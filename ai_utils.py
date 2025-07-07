import google.generativeai as genai
import os
import json
import logging
import numpy as np
import db_utils # Make sure this is imported

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment variables
GEMINI_MODEL_NAME = os.getenv('GEMINI_MODEL_NAME')
GEMINI_EMBEDDING_MODEL = os.getenv('GEMINI_EMBEDDING_MODEL')
# New: Environment variable for FAQ similarity threshold
FAQ_SIMILARITY_THRESHOLD = float(os.getenv('FAQ_SIMILARITY_THRESHOLD', 0.75)) # Default to 0.75 if not set

# Initialize the Gemini models once
try:
    text_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    logging.info(f"Successfully loaded Gemini text model: {GEMINI_MODEL_NAME}")
except Exception as e:
    logging.error(f"Error loading Gemini text model {GEMINI_MODEL_NAME}: {e}")
    text_model = None # Set to None if loading fails

def generate_ai_reply(user_message, wa_id):
    """
    Generates an AI response using the Gemini model, incorporating relevant FAQ context.
    """
    if text_model is None:
        logging.error("Gemini text model not loaded. Cannot generate AI reply.")
        return "I'm sorry, my AI brain is currently offline. Please try again later."

    logging.info(f"Received message from {wa_id} for AI processing: '{user_message}'")

    context_string = ""
    # Day 4: Call find_relevant_faqs to get context
    # find_relevant_faqs now returns (score, faq_item) tuples
    relevant_faqs_with_scores = find_relevant_faqs(user_message, top_n=3)

    if relevant_faqs_with_scores:
        # Filter FAQs by similarity threshold to ensure quality
        filtered_faqs = []
        for score, faq_item in relevant_faqs_with_scores:
            if score >= FAQ_SIMILARITY_THRESHOLD:
                filtered_faqs.append(faq_item)
            else:
                logging.debug(f"FAQ '{faq_item['question'][:50]}...' skipped due to low similarity score ({score:.4f} < {FAQ_SIMILARITY_THRESHOLD}).")

        if filtered_faqs:
            context_string = "Here is some relevant information from our FAQs:\n\n"
            for i, faq in enumerate(filtered_faqs):
                context_string += f"Q{i+1}: {faq['question']}\nA{i+1}: {faq['answer']}\n\n"
            logging.info(f"Injected {len(filtered_faqs)} relevant FAQs into context.")
        else:
            logging.info("No relevant FAQs found above the similarity threshold after filtering.")
    else:
        logging.info("No relevant FAQs found for the query.")

    # Construct the prompt with context
    # System instruction: Guide the LLM on how to use the context
    system_instruction = (
        "You are a helpful and friendly WhatsApp assistant for our company. "
        "Use the provided context to answer the user's questions truthfully and concisely. "
        "If the answer is not in the provided context, state that you don't have enough information "
        "and suggest contacting support at support@example.com or calling 1-800-555-0199."
        "Do not invent information. Prioritize factual answers over conversational filler."
    )

    # Combine context and user message
    full_prompt = f"{system_instruction}\n\n{context_string}User: {user_message}"

    logging.info(f"Sending prompt to Gemini for {wa_id}:\n{full_prompt[:500]}...") # Log first 500 chars

    try:
        # Make the actual call to Gemini
        response = text_model.generate_content(full_prompt)
        response_text = response.text

        logging.info(f"AI generated response for {wa_id}: {response_text[:100]}...")
        return response_text
    except Exception as e:
        logging.error(f"Error generating AI reply for {wa_id}: {e}")
        # Improve error handling, perhaps fall back to a generic message
        return "I'm sorry, I encountered an error trying to generate a response. Please try again later."


def generate_embedding(text):
    """
    Generates an embedding vector for the given text using the Gemini embedding model.
    """
    if not text:
        logging.warning("Attempted to generate embedding for empty text.")
        return None
    try:
        result = genai.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_query"
        )
        embedding = result['embedding']
        logging.debug(f"Generated embedding for text (first 5 chars): '{text[:50]}'")
        return embedding
    except Exception as e:
        logging.error(f"Error generating embedding for text: '{text[:50]}...' - {e}")
        return None

def cosine_similarity(vec1, vec2):
    """
    Calculates the cosine similarity between two vectors.
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0

    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def find_relevant_faqs(user_query, top_n=3):
    """
    Finds the top_n most relevant FAQs to the user's query using cosine similarity.
    Returns a list of (similarity_score, faq_item) tuples.
    """
    query_embedding = generate_embedding(user_query)
    if query_embedding is None:
        logging.warning("Could not generate embedding for user query. Returning empty list.")
        return []

    all_faqs = db_utils.get_all_faqs() # Get all FAQs from the database

    scored_faqs = []
    for faq in all_faqs:
        # The embedding is already a list from db_utils.get_all_faqs(), no need to json.loads it again
        faq_embedding = faq.get('embedding')
        if faq_embedding and isinstance(faq_embedding, list): # Ensure it's a list (already handled by db_utils)
            try:
                similarity = cosine_similarity(query_embedding, faq_embedding)
                scored_faqs.append((similarity, faq))
            except Exception as e:
                # Catch general exceptions during similarity calculation
                logging.error(f"Error calculating similarity for FAQ ID {faq.get('id')}: {e}. Skipping this FAQ.")
        else:
            # This case ideally shouldn't happen if db_utils.get_all_faqs is working correctly,
            # but it's a good safeguard for missing or malformed embeddings.
            logging.warning(f"FAQ ID {faq.get('id')} has missing or invalid embedding type ({type(faq_embedding)}). Skipping for relevance search.")

    scored_faqs.sort(key=lambda x: x[0], reverse=True)

    logging.info(f"Relevance search for query: '{user_query}'")
    for i, (score, faq) in enumerate(scored_faqs[:top_n]):
        logging.info(f"  Match {i+1}: Score={score:.4f}, Q='{faq['question'][:50]}...'")

    # Return top_n matches as (score, faq_item) tuples
    return scored_faqs[:top_n]