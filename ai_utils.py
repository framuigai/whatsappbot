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
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- START MODIFICATION FOR DB REFACTORING ---
# Using the new, client-centric DB modules.
from db.faqs_crud import get_all_faqs, add_faq, get_faq_by_id, update_faq, soft_delete_faq_by_id
from db.conversations_crud import get_conversation_history_by_whatsapp_id
from db.clients_crud import get_client_config_by_whatsapp_id
# --- END MODIFICATION FOR DB REFACTORING ---

# --- Logging Configuration ---
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- Environment Variables ---
GEMINI_MODEL_NAME = os.getenv('GEMINI_MODEL_NAME', 'gemini-pro')
GEMINI_EMBEDDING_MODEL = os.getenv('GEMINI_EMBEDDING_MODEL', 'embedding-001')

try:
    FAQ_SIMILARITY_THRESHOLD = float(os.getenv('FAQ_SIMILARITY_THRESHOLD', 0.75))
except ValueError:
    logger.warning("Invalid FAQ_SIMILARITY_THRESHOLD in .env. Defaulting to 0.75.")
    FAQ_SIMILARITY_THRESHOLD = 0.75
logger.info(f"FAQ Similarity Threshold set to: {FAQ_SIMILARITY_THRESHOLD}")

text_model = None
embedding_model = None
try:
    if GEMINI_MODEL_NAME:
        text_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        logger.info(f"Successfully loaded Gemini text model: {GEMINI_MODEL_NAME}")
    else:
        logger.error("GEMINI_MODEL_NAME is not set. Generative AI text model will not be initialized.")

    if GEMINI_EMBEDDING_MODEL:
        logger.info(f"Using Gemini embedding model: {GEMINI_EMBEDDING_MODEL}")
    else:
        logger.error("GEMINI_EMBEDDING_MODEL is not set. Generative AI embedding model will not be initialized.")
except Exception as e:
    logger.critical(f"Failed to initialize Gemini models: {e}", exc_info=True)
    text_model = None

def generate_embedding(text):
    if not GEMINI_EMBEDDING_MODEL:
        logger.error("Embedding model not configured. Cannot generate embedding.")
        return None
    try:
        response = genai.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            content=text,
            task_type="RETRIEVAL_QUERY"
        )
        return response['embedding']
    except Exception as e:
        logger.error(f"Error generating embedding for text: '{text[:50]}...'. Error: {e}", exc_info=True)
        return None

def find_relevant_faq(user_query, client_id):
    """
    Finds most relevant FAQ for client using cosine similarity.
    Includes fallback to global FAQs if client-specific FAQs are empty.
    """
    if not GEMINI_EMBEDDING_MODEL:
        logger.warning("Embedding model not initialized. Cannot find relevant FAQs.")
        return None, 0.0

    user_query_embedding = generate_embedding(user_query)
    if user_query_embedding is None:
        logger.error("Failed to generate embedding for user query.")
        return None, 0.0

    # Step 1: Fetch client-specific FAQs
    faqs = get_all_faqs(client_id)
    if not faqs:
        logger.warning(f"No FAQs found for client '{client_id}'. Trying global FAQs (client_id=None).")
        faqs = get_all_faqs(None)

    if not faqs:
        logger.info("No FAQs available at all.")
        return None, 0.0

    max_similarity = -1
    relevant_faq = None
    user_query_embedding_np = np.array(user_query_embedding)

    for faq in faqs:
        faq_embedding = faq.get('embedding')
        if faq_embedding:
            try:
                faq_embedding_np = np.array(faq_embedding)
                dot_product = np.dot(user_query_embedding_np, faq_embedding_np)
                norm_user = np.linalg.norm(user_query_embedding_np)
                norm_faq = np.linalg.norm(faq_embedding_np)
                similarity = dot_product / (norm_user * norm_faq) if norm_user and norm_faq else 0
                if similarity > max_similarity:
                    max_similarity = similarity
                    relevant_faq = faq
            except Exception as e:
                logger.error(f"Error calculating similarity for FAQ ID {faq.get('id')}: {e}", exc_info=True)

    if relevant_faq and max_similarity >= FAQ_SIMILARITY_THRESHOLD:
        logger.info(f"Found relevant FAQ (Q='{relevant_faq['question'][:50]}...') with similarity {max_similarity:.2f} for client '{client_id}'.")
        return relevant_faq, max_similarity
    else:
        logger.info(f"No relevant FAQs above threshold ({FAQ_SIMILARITY_THRESHOLD}) for query '{user_query[:50]}...'. Max similarity: {max_similarity:.2f}.")
        return None, max_similarity

def generate_ai_reply(user_query, wa_id, client_id):
    """
    Generates an AI reply based on the user's query and conversation history.
    Prioritizes answers from the FAQ database if a relevant FAQ is found.
    If no relevant FAQ, it uses the Generative AI model to produce a response.
    Includes fallback for global FAQs if client-specific FAQs are missing.
    """
    response_text = "I'm sorry, I couldn't process your request at the moment. Please try again later."
    faq_matched = False
    faq_question = None
    faq_answer = None
    ai_model_used = GEMINI_MODEL_NAME

    try:
        # Fetch client-specific configuration from the database using the WhatsApp ID.
        client_config = get_client_config_by_whatsapp_id(wa_id)
        if client_config:
            logger.info(f"Processing message for client: `{client_config.get('client_id')}` (WA ID: {wa_id})")
            client_id = client_config.get('client_id', client_id)

        # 1. Attempt to find a relevant FAQ in the database (with fallback to global FAQs).
        relevant_faq, similarity = find_relevant_faq(user_query, client_id)

        if relevant_faq:
            faq_matched = True
            faq_question = relevant_faq['question']
            faq_answer = relevant_faq['answer']
            response_text = faq_answer
            logger.info(
                f"Responded with FAQ for client '{client_id}'. Q: '{faq_question[:50]}...', A: '{faq_answer[:50]}...'")
        else:
            logger.info(
                f"No relevant FAQ found for user query for client '{client_id}'. Proceeding with generative AI.")

            # 2. If no relevant FAQ is found, use the Generative AI model.
            if text_model:
                # Fetch recent conversation history for context.
                conversation_history = get_conversation_history_by_whatsapp_id(wa_id, limit=5, client_id=client_id)

                history_string = ""
                for msg in conversation_history:
                    history_string += f"{msg['sender'].capitalize()}: {msg['message_text']}\n"

                # Define system instruction (persona/guidelines for the AI)
                system_instruction = (
                    "You are a helpful and friendly AI assistant for a business. "
                    "Answer questions based on the provided conversation history. "
                    "If you don't have enough information, politely state that you cannot answer and suggest contacting support. "
                    "Maintain a professional and polite tone. Do not invent information."
                )

                # Optional: customize system instruction for specific clients
                if client_config and client_config.get('client_name') == "my_initial_client_id":
                    system_instruction = (
                        "You are a helpful and friendly AI assistant for 'My Initial Client Inc.'. "
                        "Answer questions based on conversation history and common business knowledge. "
                        "If you don't have enough information, say so politely and suggest contacting support. "
                        "Maintain professionalism and avoid inventing details."
                    )

                prompt = (
                    f"Conversation History:\n{history_string}\n\n"
                    f"User: {user_query}\n\n"
                    "AI:"
                )
                logger.debug(f"Sending prompt to Gemini:\n{prompt}")

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
                logger.info(f"Generative AI response for client '{client_id}': {response_text[:50]}...")
            else:
                logger.error("Generative AI model not initialized. Cannot generate AI reply.")
                response_text = "I'm sorry, my AI capabilities are not active right now."

    except Exception as e:
        logger.error(f"Error in generate_ai_reply: {e}", exc_info=True)
        response_text = "I encountered an error while trying to respond. Please try again."

    return {
        "response": response_text,
        "faq_matched": faq_matched,
        "faq_question": faq_question,
        "faq_answer": faq_answer,
        "ai_model_used": ai_model_used
    }

def add_faq_entry(question, answer, client_id):
    """
    Adds a new FAQ entry to the database, generating an embedding for the question.
    The embedding is stored to allow for similarity-based retrieval later.
    """
    embedding = generate_embedding(question)
    if embedding is None:
        logger.error(f"Failed to generate embedding for FAQ question: '{question[:50]}...' (Client: {client_id})")
        return False
    try:
        add_faq(question, answer, embedding, client_id)
        logger.info(f"Successfully added new FAQ: '{question[:50]}...' for client '{client_id}'.")
        return True
    except Exception as e:
        logger.error(f"Error adding FAQ entry: {e}", exc_info=True)
        return False

def update_faq_entry(faq_id, question, answer, client_id):
    """
    Updates an existing FAQ entry in the database.
    If the question changes, a new embedding is generated for it.
    """
    existing_faq = get_faq_by_id(faq_id, client_id)
    if not existing_faq:
        logger.warning(f"FAQ with ID {faq_id} not found for client '{client_id}'. Cannot update.")
        return False

    embedding = existing_faq.get('embedding')
    if question != existing_faq.get('question'):
        embedding = generate_embedding(question)
        if embedding is None:
            logger.error(f"Failed to generate new embedding for updated FAQ question: '{question[:50]}...' (Client: {client_id})\n"
                         "FAQ update will proceed with old embedding if available, or fail if new embedding is critical.")

    try:
        update_faq(faq_id, question, answer, embedding, client_id)
        logger.info(f"Successfully updated FAQ ID {faq_id}: Q='{question[:50]}...' for client '{client_id}'")
        return True
    except Exception as e:
        logger.error(f"Error updating FAQ entry: {e}", exc_info=True)
        return False

def delete_faq_entry(faq_id, client_id):
    """
    Deletes an FAQ entry from the database for a specific client.
    """
    try:
        soft_delete_faq_by_id(faq_id, client_id)
        logger.info(f"Successfully deleted FAQ ID {faq_id} for client '{client_id}'.")
        return True
    except Exception as e:
        logger.error(f"Error deleting FAQ entry: {e}", exc_info=True)
        return False

def get_faqs_for_client(client_id):
    """
    Retrieves all FAQs for a specific client from the database.
    """
    return get_all_faqs(client_id)

def get_most_relevant_faq(user_query: str, client_id: str):
    """
    Fetch FAQs dynamically from the DB for the given client, compute similarity using embeddings,
    and return the most relevant FAQ if above the similarity threshold.
    """
    try:
        user_embedding = generate_embedding(user_query)
        if user_embedding is None:
            logger.warning("Failed to generate embedding for user query.")
            return None

        faqs = get_all_faqs(client_id)
        if not faqs:
            logger.info(f"No FAQs found for client {client_id}.")
            return None

        best_match = None
        max_similarity = 0.0

        for faq in faqs:
            try:
                faq_embedding = np.array(faq.get('embedding', []), dtype=float)
                similarity = cosine_similarity(user_embedding, faq_embedding)
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_match = faq
            except Exception as e:
                logger.error(f"Error processing FAQ embedding: {e}", exc_info=True)

        if best_match and max_similarity >= FAQ_SIMILARITY_THRESHOLD:
            logger.info(f"Found relevant FAQ (Q='{best_match['question'][:30]}...') with similarity {max_similarity:.2f} for client '{client_id}'.")
            return best_match
        else:
            logger.info(f"No relevant FAQs found above threshold ({FAQ_SIMILARITY_THRESHOLD}) for query '{user_query[:20]}...'. Max similarity: {max_similarity:.2f}.")
            return None

    except Exception as e:
        logger.error(f"Error in get_most_relevant_faq: {e}", exc_info=True)
        return None

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2)
