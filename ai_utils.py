# ai_utils.py
# This file contains utility functions for integrating with Google Gemini AI models,
# handling FAQ responses, and managing AI-driven replies based on conversation history.

import google.generativeai as genai
import os
import json
import logging
import numpy as np
import sys

# Import specific types for Gemini safety settings directly at the top for clarity.
# HarmCategory is used to define categories for content safety.
# HarmBlockThreshold is used to specify how aggressively content in a category should be blocked.
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- START MODIFICATION FOR DB REFACTORING ---
# Importing specific CRUD (Create, Read, Update, Delete) operations
# from the new database modules. This promotes modularity and maintainability.
from db.faqs_crud import get_all_faqs, add_faq, get_faq_by_id, update_faq, delete_faq_by_id
from db.conversations_crud import get_conversation_history_by_whatsapp_id # For fetching user conversation history
from db.tenants_crud import get_tenant_config_by_whatsapp_id # For fetching tenant-specific AI instructions
# --- END MODIFICATION FOR DB REFACTORING ---

# --- Logging Configuration ---
# Set up a logger for this module to record events and errors.
logger = logging.getLogger(__name__)
# The logging level is typically set via a configuration file or environment variable (e.g., in config.py).
# For demonstration, assume LOGGING_LEVEL and log_level_map are imported from 'config'.
# Example: logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
# (Assuming these are defined elsewhere and imported, as seen in other files like app.py)
# For now, setting a default level if config is not strictly provided in this snippet.
if not logger.handlers: # Prevent adding multiple handlers if already configured
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO) # Default to INFO if not set by an external config


# --- Environment Variables ---
# Load configuration from environment variables, providing default values.
# These variables control which Gemini models are used and similarity thresholds for FAQs.
GEMINI_MODEL_NAME = os.getenv('GEMINI_MODEL_NAME', 'gemini-pro')
GEMINI_EMBEDDING_MODEL = os.getenv('GEMINI_EMBEDDING_MODEL', 'embedding-001')

try:
    FAQ_SIMILARITY_THRESHOLD = float(os.getenv('FAQ_SIMILARITY_THRESHOLD', 0.75))
except ValueError:
    logger.warning("Invalid FAQ_SIMILARITY_THRESHOLD in .env. Defaulting to 0.75.")
    FAQ_SIMILARITY_THRESHOLD = 0.75
logger.info(f"FAQ Similarity Threshold set to: {FAQ_SIMILARITY_THRESHOLD}")

# Initialize the Gemini models once to avoid repeated initialization.
# text_model is for generative AI responses.
# embedding_model is conceptually for embeddings, but in Gemini, `genai.embed_content`
# is typically used directly with the model name. The `embedding_model` variable here
# might be a placeholder or for other specific uses.
text_model = None
embedding_model = None # This variable is kept, but `genai.embed_content` is typically called directly.
try:
    if GEMINI_MODEL_NAME:
        text_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        logger.info(f"Successfully loaded Gemini text model: {GEMINI_MODEL_NAME}")
    else:
        logger.error("GEMINI_MODEL_NAME is not set. Generative AI text model will not be initialized.")

    if GEMINI_EMBEDDING_MODEL:
        # Note: 'embedding-001' is not a GenerativeModel; it's used with `genai.embed_content`.
        # The line below is conceptually incorrect for direct model loading for embeddings,
        # but the actual embedding generation uses `genai.embed_content` correctly.
        # This variable might be kept for logging purposes.
        # Correct way to get an embedding model if it were a separate model object:
        # embedding_model = genai.get_model(GEMINI_EMBEDDING_MODEL)
        logger.info(f"Using Gemini embedding model: {GEMINI_EMBEDDING_MODEL}")
    else:
        logger.error("GEMINI_EMBEDDING_MODEL is not set. Generative AI embedding model will not be initialized.")

except Exception as e:
    logger.critical(f"Failed to initialize Gemini models: {e}", exc_info=True)
    text_model = None # Ensure models are None if initialization fails

def generate_embedding(text):
    """
    Generates an embedding for the given text using the Gemini embedding model.
    These embeddings are numerical representations of text, useful for
    finding semantic similarity between different pieces of text (e.g., user queries and FAQs).
    """
    if not GEMINI_EMBEDDING_MODEL: # Check if the model name is configured
        logger.error("Embedding model not configured. Cannot generate embedding.")
        return None
    try:
        # `genai.embed_content` is the correct method to generate embeddings with Gemini's embedding model.
        # 'task_type' is important for optimizing the embedding for its intended use (e.g., retrieval).
        response = genai.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            content=text,
            task_type="RETRIEVAL_QUERY" # Or "RETRIEVAL_DOCUMENT" for documents in your FAQ database
        )
        # The actual embedding vector is typically found in the 'embedding' field of the response.
        return response['embedding']
    except Exception as e:
        logger.error(f"Error generating embedding for text: '{text[:50]}...'. Error: {e}", exc_info=True)
        return None

def find_relevant_faq(user_query, tenant_id):
    """
    Finds the most relevant FAQ based on the user's query for a specific tenant
    using embedding similarity (cosine similarity).
    Returns the FAQ object if a relevant one is found above a certain threshold, otherwise None.
    """
    # Ensure embedding model is available before proceeding.
    if not GEMINI_EMBEDDING_MODEL:
        logger.warning("Embedding model not initialized. Cannot find relevant FAQs.")
        return None, 0.0

    user_query_embedding = generate_embedding(user_query)
    if user_query_embedding is None:
        logger.error("Failed to generate embedding for user query. Cannot find relevant FAQ.")
        return None, 0.0

    # Retrieve all FAQs for the given tenant from the database.
    all_faqs = get_all_faqs(tenant_id)
    if not all_faqs:
        logger.info(f"No FAQs found for tenant '{tenant_id}'.")
        return None, 0.0

    max_similarity = -1 # Initialize with a low value to find the maximum similarity
    relevant_faq = None

    for faq in all_faqs:
        faq_embedding = faq.get('embedding')
        if faq_embedding:
            try:
                # Convert list embeddings from JSON (stored in DB) to NumPy arrays for calculation.
                faq_embedding_np = np.array(faq_embedding)
                user_query_embedding_np = np.array(user_query_embedding)

                # Calculate cosine similarity: (A . B) / (||A|| * ||B||)
                dot_product = np.dot(user_query_embedding_np, faq_embedding_np)
                norm_user = np.linalg.norm(user_query_embedding_np)
                norm_faq = np.linalg.norm(faq_embedding_np)

                if norm_user == 0 or norm_faq == 0:
                    similarity = 0 # Avoid division by zero if an embedding is all zeros
                else:
                    similarity = dot_product / (norm_user * norm_faq)

                # Keep track of the FAQ with the highest similarity.
                if similarity > max_similarity:
                    max_similarity = similarity
                    relevant_faq = faq
            except Exception as e:
                logger.error(f"Error calculating similarity for FAQ ID {faq.get('id')}: {e}", exc_info=True)

    # Return the relevant FAQ only if its similarity is above the predefined threshold.
    if relevant_faq and max_similarity >= FAQ_SIMILARITY_THRESHOLD:
        logger.info(f"Found relevant FAQ (Q='{relevant_faq['question'][:50]}...') with similarity {max_similarity:.2f} for tenant '{tenant_id}'.")
        return relevant_faq, max_similarity
    else:
        logger.info(f"No relevant FAQs found above threshold ({FAQ_SIMILARITY_THRESHOLD}) for query '{user_query[:50]}...' for tenant '{tenant_id}'. Max similarity: {max_similarity:.2f}.")
        return None, max_similarity


def generate_ai_reply(user_query, wa_id, tenant_id):
    """
    Generates an AI reply based on the user's query and conversation history.
    Prioritizes answers from the FAQ database if a relevant FAQ is found.
    If no relevant FAQ, it uses the Generative AI model to produce a response.
    """
    response_text = "I'm sorry, I couldn't process your request at the moment. Please try again later."
    faq_matched = False
    faq_question = None
    faq_answer = None
    ai_model_used = GEMINI_MODEL_NAME

    try:
        # Fetch tenant-specific configuration from the database using the WhatsApp ID.
        tenant_config = get_tenant_config_by_whatsapp_id(wa_id)
        if tenant_config:
            logger.info(f"Processing message for tenant: `{tenant_config.get('tenant_id')}` (WA ID: {wa_id})")
            # Ensure consistency by updating tenant_id if it's found in the config.
            tenant_id = tenant_config.get('tenant_id', tenant_id)

        # 1. Attempt to find a relevant FAQ in the database.
        relevant_faq, similarity = find_relevant_faq(user_query, tenant_id)

        if relevant_faq:
            faq_matched = True
            faq_question = relevant_faq['question']
            faq_answer = relevant_faq['answer']
            response_text = faq_answer # If FAQ matches, use its answer directly.
            logger.info(f"Responded with FAQ for tenant '{tenant_id}'. Q: '{faq_question[:50]}...', A: '{faq_answer[:50]}...'")
        else:
            logger.info(f"No relevant FAQ found for user query for tenant '{tenant_id}'. Proceeding with generative AI.")
            # 2. If no relevant FAQ is found, use the Generative AI model.
            if text_model:
                # Fetch recent conversation history for context.
                conversation_history = get_conversation_history_by_whatsapp_id(wa_id, limit=5, tenant_id=tenant_id)

                history_string = ""
                for msg in conversation_history:
                    history_string += f"{msg['sender'].capitalize()}: {msg['message_text']}\n"

                # Define a system instruction (persona/guidelines for the AI)
                # This can be customized per tenant for specific business needs.
                system_instruction = ""
                if tenant_config and tenant_config.get('tenant_name') == "my_initial_client_id": # Example tenant customization
                    system_instruction = (
                        "You are a helpful and friendly AI assistant for 'My Initial Client Inc.'. "
                        "Answer questions based on the provided conversation history and common business knowledge. "
                        "If you don't have enough information, politely state that you cannot answer and suggest visiting their website or contacting their dedicated support. "
                        "Maintain a professional and polite tone. Do not invent information."
                    )
                else:
                    system_instruction = (
                        "You are a helpful and friendly AI assistant for a business. "
                        "Answer questions based on the provided conversation history. "
                        "If you don't have enough information from the conversation history to answer a question, you must state that you cannot answer the question and suggest contacting support. "
                        "Maintain a professional and polite tone. Do not invent information."
                    )

                # Construct the prompt for the Generative AI model, including history and user query.
                prompt = (
                    f"Conversation History:\n{history_string}\n\n"
                    f"User: {user_query}\n\n"
                    f"{'':<0}" # This line can be used for additional FAQ context if integrated differently
                    "AI:"
                )
                logger.debug(f"Sending prompt to Gemini:\n{prompt}")

                # Make the generative content request to the Gemini text model.
                # Crucially, safety_settings are applied here to control content generation.
                # The corrected HarmCategory members are used: HARM_CATEGORY_HARASSMENT, etc.
                response = text_model.generate_content(
                    contents=[{"role": "user", "parts": [{"text": system_instruction}, {"text": prompt}]}],
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
                    }
                )
                response_text = response.text
                logger.info(f"Generative AI response for tenant '{tenant_id}': {response_text[:50]}...")
            else:
                logger.error("Generative AI model not initialized. Cannot generate AI reply.")
                response_text = "I'm sorry, my AI capabilities are not active right now."

    except Exception as e:
        logger.error(f"Error in generate_ai_reply: {e}", exc_info=True)
        response_text = "I encountered an error while trying to respond. Please try again."

    # Return a dictionary containing the AI's response and metadata about the reply.
    return {
        "response": response_text,
        "faq_matched": faq_matched,
        "faq_question": faq_question,
        "faq_answer": faq_answer,
        "ai_model_used": ai_model_used
    }


def add_faq_entry(question, answer, tenant_id):
    """
    Adds a new FAQ entry to the database, generating an embedding for the question.
    The embedding is stored to allow for similarity-based retrieval later.
    """
    embedding = generate_embedding(question)
    if embedding is None:
        logger.error(f"Failed to generate embedding for FAQ question: '{question[:50]}...' (Tenant: {tenant_id})")
        return False
    try:
        # Call the CRUD function to add the FAQ to the database.
        add_faq(question, answer, embedding, tenant_id)
        logger.info(f"Successfully added new FAQ: '{question[:50]}...' for tenant '{tenant_id}'.")
        return True
    except Exception as e:
        logger.error(f"Error adding FAQ entry: {e}", exc_info=True)
        return False

def update_faq_entry(faq_id, question, answer, tenant_id):
    """
    Updates an existing FAQ entry in the database.
    If the question changes, a new embedding is generated for it.
    """
    existing_faq = get_faq_by_id(faq_id, tenant_id)
    if not existing_faq:
        logger.warning(f"FAQ with ID {faq_id} not found for tenant '{tenant_id}'. Cannot update.")
        return False

    embedding = existing_faq.get('embedding') # Keep existing embedding by default
    if question != existing_faq.get('question'):
        # If the question has changed, regenerate its embedding.
        embedding = generate_embedding(question)
        if embedding is None:
            logger.error(f"Failed to generate new embedding for updated FAQ question: '{question[:50]}...' (Tenant: {tenant_id})\n"
                         "FAQ update will proceed with old embedding if available, or fail if new embedding is critical.")
            # Depending on desired behavior, you might want to return False here
            # For now, it will proceed with the old embedding if regeneration fails

    try:
        # Call the CRUD function to update the FAQ in the database.
        update_faq(faq_id, question, answer, embedding, tenant_id)
        logger.info(f"Successfully updated FAQ ID {faq_id}: Q='{question[:50]}...' for tenant '{tenant_id}'")
        return True
    except Exception as e:
        logger.error(f"Error updating FAQ entry: {e}", exc_info=True)
        return False

def delete_faq_entry(faq_id, tenant_id):
    """
    Deletes an FAQ entry from the database for a specific tenant.
    """
    try:
        # Call the CRUD function to delete the FAQ from the database.
        delete_faq_by_id(faq_id, tenant_id)
        logger.info(f"Successfully deleted FAQ ID {faq_id} for tenant '{tenant_id}'.")
        return True
    except Exception as e:
        logger.error(f"Error deleting FAQ entry: {e}", exc_info=True)
        return False

def get_faqs_for_tenant(tenant_id):
    """
    Retrieves all FAQs for a specific tenant from the database.
    """
    return get_all_faqs(tenant_id)