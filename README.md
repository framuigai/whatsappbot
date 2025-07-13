# WhatsApp Gemini AI Chatbot MVP

A basic, yet robust, WhatsApp chatbot powered by Google's Gemini 1.5 Flash model, built with Flask and SQLite. It handles conversation context, manages token limits, and includes resilience features for common edge cases.

## Features

* **WhatsApp Integration:** Receives and sends messages via WhatsApp Cloud API.
* **Gemini AI Powered:** Uses Google's Gemini 1.5 Flash model for intelligent replies.
* **Conversation Context:** Stores and retrieves message history in a SQLite database to maintain multi-turn conversations.
* **Token Management:** Intelligently truncates conversation history to stay within Gemini's context window limits.
* **RAG (Retrieval Augmented Generation):** Integrates an internal FAQ knowledge base to provide precise answers when relevant, leveraging semantic search with Gemini embeddings.
* **Resilience & Edge Case Handling:**
    * Graceful handling of empty or whitespace-only messages.
    * Basic rate-limiting to prevent spam from a single user.
    * Detects and provides fallback for Gemini AI safety policy violations.
    * Implements exponential backoff with retries for Gemini API quota limits (HTTP 429).
* **Clear Logging:** Detailed logging for all operations and error cases.

## Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.8+**
* **pip** (Python package installer)
* A **WhatsApp Business Account** with a configured phone number and API access.
* A **Google Cloud Project** with the Gemini API enabled and an API key generated.
* `ngrok` (or a similar tunneling service) to expose your local Flask server to the internet for WhatsApp webhooks.

## Setup Guide

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
    cd YOUR_REPO_NAME
    ```
    (Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub details.)

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install Flask python-dotenv requests google-generativeai numpy # Added numpy for cosine similarity
    ```

4.  **Environment Variables:**
    Create a `.env` file in the root of your project directory and add the following:
    ```dotenv
    VERIFY_TOKEN="YOUR_WHATSAPP_WEBHOOK_VERIFY_TOKEN"
    WHATSAPP_PHONE_NUMBER_ID="YOUR_WHATSAPP_PHONE_NUMBER_ID"
    GEMINI_API_KEY="YOUR_GOOGLE_GEMINI_API_KEY"
    DATABASE_NAME="conversations.db" # Default name for your SQLite database
    RATE_LIMIT_SECONDS=5 # Seconds a user must wait before sending another message
    FAQ_SIMILARITY_THRESHOLD=0.75 # Threshold for FAQ relevance (0.0 to 1.0)
    LOGGING_LEVEL=INFO # Set to DEBUG for more verbose logs, INFO for production
    FLASK_DEBUG=True # Set to True for development, False for production
    GEMINI_MODEL_NAME=gemini-1.5-flash # The Gemini model used for text generation
    GEMINI_EMBEDDING_MODEL=embedding-001 # The Gemini model used for embedding generation
    ```
    * Replace placeholder values with your actual tokens and IDs.

5.  **Initialize Database and Load FAQs (Manual Method):**
    * Run the `app.py` file **once** with the "Initial FAQ Loading" block (in `app.py`) uncommented. This will create your database tables and populate the FAQs.
    * After the FAQs are loaded successfully (check your logs), **re-comment** the "Initial FAQ Loading" block in `app.py` to prevent re-adding FAQs on subsequent runs.
    ```bash
    # Ensure your virtual environment is activated
    python app.py
    # Wait for logs to confirm FAQ loading, then CTRL+C to stop
    # Now, re-comment the FAQ loading block in app.py
    ```

## Running the Bot

1.  **Start the Flask Application:**
    ```bash
    # Ensure your virtual environment is activated
    python app.py
    ```
    Your Flask app will start on `http://127.0.0.1:5000`.

2.  **Expose Your Local Server with ngrok:**
    Open a new terminal window (keep the Flask server running in the first one) and run `ngrok`:
    ```bash
    ngrok http 5000
    ```
    `ngrok` will provide you with a public HTTPS URL (e.g., `https://abcdef12345.ngrok-free.app`). Copy this URL.

3.  **Configure WhatsApp Webhook:**
    * Go to your Facebook Developer App dashboard for your WhatsApp Business Account.
    * Navigate to "WhatsApp" -> "API Setup".
    * In the "Webhook" section, click "Configure Webhook".
    * **Webhook URL:** Paste the `ngrok` HTTPS URL you copied.
    * **Verify Token:** Enter the same `VERIFY_TOKEN` you set in your `.env` file.
    * Click "Verify and Save".
    * Under the Webhook configuration, click "Manage" next to the Webhook URL and **subscribe to the `messages` field**.

## Usage

Once the Flask server and ngrok are running, and your WhatsApp webhook is configured, simply send a message to your WhatsApp Business Account number! The bot will respond.

## Troubleshooting

* **"WEBHOOK_VERIFIED failed"**: Double-check your `VERIFY_TOKEN` in `.env` and in the WhatsApp webhook configuration.
* **No replies from bot**: Check your Flask console and `whatsapp_bot.log` for any `ERROR` messages. Ensure `ngrok` is running and its URL is correct in the WhatsApp webhook. Check your WhatsApp Cloud API dashboard for any error messages related to outgoing messages.
* **Bot not remembering context**: Check your database (`conversations.db`) to ensure messages are being saved.
* **"Sorry, I couldn't process your request right now."**: This is a general fallback. Check your Flask logs for more specific errors (e.g., Gemini API errors, embedding generation failures).
* **"Please wait X seconds..." (Rate Limit)**: This indicates you're sending messages too quickly. Adjust `RATE_LIMIT_SECONDS` in `.env` if needed for testing.

## Future Enhancements (Optional)

* **Batch FAQ Loading Script:** Create a separate `import_faqs.py` script to easily load FAQs from JSON/CSV files, replacing the manual loading process.
* **Persistent Rate Limiting:** Implement rate limiting that persists across server restarts (e.g., using Redis or SQLite for timestamp storage). (Already implemented using SQLite).
* **Advanced Error Reporting:** Integrate with an error tracking service (e.g., Sentry, Bugsnag).
* **Unit Tests:** Write automated tests for individual functions.
* **Deployment:** Deploy to a cloud platform like Heroku, Google Cloud Run, AWS Elastic Beanstalk, etc., for production use.
* **Rich Media Support:** Extend the bot to handle images, audio, or other media types from WhatsApp.
* **Command Handling:** Add specific commands (e.g., `/reset` to clear conversation history).
* **FAISS Integration:** For very large knowledge bases (thousands+ FAQs), integrate FAISS for faster and more efficient similarity search.