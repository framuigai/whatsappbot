# app.py

from flask import Flask
import logging # <--- Add this line

# Initialize the Flask application
app = Flask(__name__)

# Configure logging (Add these lines)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler() # Logs to console
                        # logging.FileHandler('app.log') # Optional: uncomment for file logging
                    ])

# Define a simple route for the root URL
@app.route('/')
def hello_world():
    """
    This function handles requests to the root URL ("/").
    It simply returns a "Hello, World!" message.
    This helps verify that the Flask application is running correctly.
    """
    app.logger.info("Hello World route accessed.") # <--- Example of using the logger
    return 'Hello, World! This is your WhatsApp Bot MVP.'

# This block ensures the Flask app runs only when the script is executed directly
if __name__ == '__main__':
    app.logger.info("Flask application starting...") # <--- Example of using the logger
    app.run(debug=True, port=5000)