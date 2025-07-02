from flask import Flask, session as flask_session
from utils import htmx_render

app = Flask(__name__)

# Secret key for session management. Replace with a strong, random key.
# In a real application, this should come from environment variables or a config file.
# TODO: Replace with a proper secret key management strategy (e.g., environment variable)
app.secret_key = 'dev_secret_key_should_be_changed'


@app.route('/')
def home():
    """Serves the home page."""
    # TODO: This is a placeholder for the model_builder_main route for url_for in home.html
    # Will need to be updated once the model_builder blueprint is established.
    # For now, to prevent url_for from breaking if home is rendered directly,
    # we can pass a dummy value or ensure templates handle missing URLs gracefully.
    # The current home.html template uses a placeholder name directly in url_for,
    # which will error if that route isn't defined.
    # A better approach for now is to make the button non-functional or point to '#'.
    # For this step, we'll rely on the placeholder in home.html and define a dummy route for it.
    return htmx_render("home.html")

# Dummy route for placeholder in home.html to prevent startup error
# TODO: Remove this once model_builder.model_builder_main is implemented
@app.route('/model_builder_placeholder')
def model_builder_main_placeholder():
    return "Placeholder for Model Builder"


if __name__ == '__main__':
    # TODO: Add configuration for host, port, and debug mode from environment variables
    app.run(debug=True, port=8080)
