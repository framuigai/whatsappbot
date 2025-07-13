import google.generativeai as genai
import os
import json
import logging
import numpy as np
import db_utils
import sys

# --- Logging Configuration ---
# Configure logging for this module. This allows specific logging levels for ai_utils.
# The actual level will be set in app.py's __main__ block for consistency.
logger = logging.getLogger(__name__)

# --- Environment Variables ---
GEMINI_MODEL_NAME = os.getenv('GEMINI_MODEL_NAME', 'gemini-pro')
GEMINI_EMBEDDING_MODEL = os.getenv('GEMINI_EMBEDDING_MODEL', 'embedding-001')

# New: Environment variable for FAQ similarity threshold
try:
    FAQ_SIMILARITY_THRESHOLD = float(os.getenv('FAQ_SIMILARITY_THRESHOLD', 0.75))
except ValueError:
    logger.warning("Invalid FAQ_SIMILARITY_THRESHOLD in .env. Defaulting to 0.75.")
    FAQ_SIMILARITY_THRESHOLD = 0.75
logger.info(f"FAQ Similarity Threshold set to: {FAQ_SIMILARITY_THRESHOLD}")

# Initialize the Gemini models once
text_model = None
try:
    if GEMINI_MODEL_NAME:
        text_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        logger.info(f"Successfully loaded Gemini text model: {GEMINI_MODEL_NAME}")
    else:
        logger.error("GEMINI_MODEL_NAME not set. Gemini text model not loaded.")
except Exception as e:
    logger.error(f"Error loading Gemini text model {GEMINI_MODEL_NAME}: {e}")

def generate_ai_reply(user_message, wa_id):
    """
    Generates an AI response using the Gemini model, incorporating relevant FAQ context.
    """
    if text_model is None:
        logger.error("Gemini text model is not initialized. Cannot generate AI reply.")
        return "I'm sorry, my AI brain is currently offline. Please try again later."

    logger.info(f"AI processing message from {wa_id}: '{user_message}'")

    context_string = ""
    # Call find_relevant_faqs to get context
    relevant_faqs_with_scores = find_relevant_faqs(user_message, top_n=5) # Fetch a few more to filter effectively

    # Apply Threshold & Log Injected Content
    filtered_faqs = []
    if relevant_faqs_with_scores:
        for score, faq_item in relevant_faqs_with_scores:
            if score >= FAQ_SIMILARITY_THRESHOLD:
                filtered_faqs.append(faq_item)
            else:
                logger.debug(f"FAQ '{faq_item['question'][:50]}...' skipped due to low similarity score ({score:.4f} < {FAQ_SIMILARITY_THRESHOLD}).")

        if filtered_faqs:
            logger.info(f"Found {len(filtered_faqs)} relevant FAQs above threshold ({FAQ_SIMILARITY_THRESHOLD}).")
            context_string = "Here is some relevant information from our FAQs that might help:\n\n"
            for i, faq in enumerate(filtered_faqs):
                context_string += f"Q{i+1}: {faq['question']}\nA{i+1}: {faq['answer']}\n\n"
                logger.debug(f"    Injected FAQ content Q{i+1}: '{faq['question'][:50]}...' (Score: {relevant_faqs_with_scores[i][0]:.4f})")
        else:
            logger.info("No relevant FAQs found above the similarity threshold. Skipping FAQ injection.")
    else:
        logger.info("No FAQs found by search for the query or no FAQs in DB. Skipping FAQ injection.")

    # Construct the prompt with context
    system_instruction = (
        "You are a helpful and friendly WhatsApp assistant for our company. "
        "Use the provided context to answer the user's questions truthfully and concisely. "
        "If the answer is not in the provided context, state that you don't have enough information "
        "and suggest contacting support at support@example.com or calling 1-800-555-0199."
        "Do not invent information. Prioritize factual answers over conversational filler."
        "Keep your responses polite and professional."
    )

    full_prompt = f"{system_instruction}\n\n"
    if context_string:
        full_prompt += f"Context:\n{context_string}\n" # Add "Context:" label
    full_prompt += f"User Query: {user_message}"

    logger.debug(f"Sending prompt to Gemini for {wa_id}:\n{full_prompt[:700]}...") # Log more of the prompt for debug

    try:
        response = text_model.generate_content(full_prompt)
        response_text = response.text
        logger.info(f"AI generated response for {wa_id}: {response_text[:200]}...") # Log first 200 chars
        return response_text
    except Exception as e:
        logger.error(f"Error generating AI reply for {wa_id}: {e}", exc_info=True) # exc_info for full traceback
        return "I'm sorry, I encountered an error trying to generate a response. Please try again later."


def generate_embedding(text):
    """
    Generates an embedding vector for the given text using the Gemini embedding model.
    """
    if not text or not text.strip():
        logger.warning("Attempted to generate embedding for empty or whitespace text. Returning None.")
        return None
    try:
        result = genai.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_query" # Use retrieval_query for search
        )
        embedding = result['embedding']
        logger.debug(f"Generated embedding for text (first 50 chars): '{text[:50]}'")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding for text: '{text[:50]}...' - {e}", exc_info=True)
        return None

def cosine_similarity(vec1, vec2):
    """
    Calculates the cosine similarity between two vectors.
    """
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)

    norm_vec1 = np.linalg.norm(vec1_np)
    norm_vec2 = np.linalg.norm(vec2_np)

    if norm_vec1 == 0 or norm_vec2 == 0:
        logger.warning("One or both vectors have zero norm in cosine_similarity. Returning 0.0.")
        return 0.0

    return np.dot(vec1_np, vec2_np) / (norm_vec1 * norm_vec2)

def find_relevant_faqs(user_query, top_n=3):
    """
    Finds the top_n most relevant FAQs to the user's query using cosine similarity.
    Returns a list of (similarity_score, faq_item) tuples.
    """
    query_embedding = generate_embedding(user_query)
    if query_embedding is None:
        logger.warning("Could not generate embedding for user query. Returning empty list.")
        return []

    all_faqs = db_utils.get_all_faqs()

    if not all_faqs:
        logger.info("No FAQs found in the database to compare against.")
        return []

    scored_faqs = []
    for faq in all_faqs:
        faq_embedding = faq.get('embedding')
        if faq_embedding and isinstance(faq_embedding, list):
            try:
                similarity = cosine_similarity(query_embedding, faq_embedding)
                scored_faqs.append((similarity, faq))
            except Exception as e:
                logger.error(f"Error calculating similarity for FAQ ID {faq.get('id')}: {e}. Skipping this FAQ.", exc_info=True)
        else:
            logger.warning(f"FAQ ID {faq.get('id')} has missing or invalid embedding (type: {type(faq_embedding)}). Skipping for relevance search.")

    scored_faqs.sort(key=lambda x: x[0], reverse=True)

    logger.debug(f"Initial relevance search results for query: '{user_query}'")
    if scored_faqs:
        for i, (score, faq) in enumerate(scored_faqs[:top_n]):
            logger.debug(f"  Match {i+1} (Raw Score): {score:.4f}, Q='{faq['question'][:50]}...'")
    else:
        logger.debug("  No FAQs with valid embeddings found for comparison.")

    return scored_faqs[:top_n]