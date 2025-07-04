# test_gemini.py (Cleaned up after successful connection)
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env file. Please set it.")
    exit()

# Configure with the standard Generative Language API endpoint
genai.configure(
    api_key=GEMINI_API_KEY,
    client_options={"api_endpoint": "generativelanguage.googleapis.com"}
)

print("--- Sending test prompt to Gemini-1.5-Flash ---")

try:
    # Initialize the model with 'gemini-1.5-flash'
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Send a simple text prompt
    response = model.generate_content("What is the capital of France?")

    # Print the response
    if response.text:
        print("\nGemini's Response:")
        print(response.text)
    else:
        print("\nGemini returned an empty response or no text.")
        # Handle potential content safety blocks or empty responses
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            print(f"Response blocked due to: {response.prompt_feedback.block_reason}")
            if response.prompt_feedback.safety_ratings:
                for rating in response.prompt_feedback.safety_ratings:
                    print(f"  {rating.category.name}: {rating.probability.name}")

except Exception as e:
    print(f"An error occurred when trying to use gemini-1.5-flash: {e}")
    print("Please ensure your API key is correct and the 'Generative Language API' is enabled.")