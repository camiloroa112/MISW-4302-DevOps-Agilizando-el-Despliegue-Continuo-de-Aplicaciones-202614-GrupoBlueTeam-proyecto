# 1st Party Imports
from app.config import Config

# 3rd Party Imports
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

# Generate the static access token signed with the configured secret key
def generate_token() -> str:
    """
    Introduction:
        - This function builds a minimal Flask app with only the JWT settings (no database needed) and signs a non-expiring token
    Returns:
        - The encoded JWT as a string
    """

    # Create a minimal app that does not touch the database
    app = Flask(__name__)

    # Use the same secret key the API uses to validate tokens
    app.config["JWT_SECRET_KEY"] = Config.JWT_SECRET_KEY

    # Bind Flask-JWT-Extended to the minimal app
    JWTManager(app)

    # Create the token inside the application context
    with app.app_context():
        return create_access_token(identity = "blacklist-client", expires_delta = False)

# Print the token when the script is executed directly
if __name__ == "__main__":
    print(generate_token())