import google.generativeai as genai
import os
import json
import logging

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment variables (retrieved here as this module will use them)
# Note: genai.configure is now called in app.py once at startup,
# so these os.getenv calls are mainly for readability and direct access if needed,
# but the genai client is already configured.
GEMINI_MODEL_NAME = os.getenv('GEMINI_MODEL_NAME')
GEMINI_EMBEDDING_MODEL = os.getenv('GEMINI_EMBEDDING_MODEL')

# Initialize the Gemini models once
try:
    text_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    logging.info(f"Successfully loaded Gemini text model: {GEMINI_MODEL_NAME}")
except Exception as e:
    logging.error(f"Error loading Gemini text model {GEMINI_MODEL_NAME}: {e}")
    text_model = None  # Set to None if loading fails


def generate_ai_reply(user_message, wa_id):
    """
    Generates an AI response using the Gemini model.
    For now, it's a simple echo with an upgrade message.
    In future steps, this will involve conversation history and RAG.
    """
    if text_model is None:
        logging.error("Gemini text model not loaded. Cannot generate AI reply.")
        return "I'm sorry, my AI brain is currently offline. Please try again later."

    logging.info(f"Received message from {wa_id} for AI processing: '{user_message}'")
    try:
        # Day 2: Still a placeholder response, but now coming from the ai_utils structure
        # The actual AI logic (RAG, conversation history) will be built here in future days.
        response_text = "Thank you for your message! My AI brain is currently being upgraded for Week 3. Please check back soon!"

        # Example of how you would *actually* call the model later:
        # response = text_model.generate_content(user_message)
        # response_text = response.text

        logging.info(f"AI generated response for {wa_id}: {response_text[:100]}...")
        return response_text
    except Exception as e:
        logging.error(f"Error generating AI reply for {wa_id}: {e}")
        return "I'm sorry, I encountered an error trying to generate a response."


def generate_embedding(text):
    """
    Generates an embedding vector for the given text using the Gemini embedding model.
    """
    if not text:
        logging.warning("Attempted to generate embedding for empty text.")
        return None
    try:
        # The embedding model is called directly here.
        result = genai.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_query"  # Appropriate task type for FAQ questions
        )
        # The embedding is usually a list of floats
        embedding = result['embedding']
        logging.debug(f"Generated embedding for text (first 5 chars): '{text[:50]}'")
        return embedding
    except Exception as e:
        logging.error(f"Error generating embedding for text: '{text[:50]}...' - {e}")
        return None