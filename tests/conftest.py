# 1st Party Imports
from app import create_app
from app.config import Config
from app.extensions import db
from collections.abc import Iterator

# 3rd Party Imports
import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_jwt_extended import create_access_token

# Test configuration: in-memory SQLite and a fixed secret, so no .env is required
class TestConfig(Config):

    # Enable testing mode (also skips the required-variables check in create_app)
    TESTING = True

    # In-memory SQLite database that disappears when the test ends
    SQLALCHEMY_DATABASE_URI = "sqlite://"

    # Fixed secret key used only to sign test tokens (32+ bytes, as recommended for HS256)
    JWT_SECRET_KEY = "test-secret-key-for-pytest-only-0123456789"

# Fresh application with empty tables for every test
@pytest.fixture
def app() -> Iterator[Flask]:
    """
    Introduction:
        - This fixture builds the app with the test configuration and drops the tables afterwards
    Returns:
        - Flask: The application
    """

    # Build the app with the test configuration (tables are created on startup)
    application = create_app(TestConfig)

    # Hand the app to the test
    yield application

    # Clean up the database once the test finishes
    with application.app_context():

        # Close the current database session
        db.session.remove()

        # Drop every table
        db.drop_all()

# HTTP client to call the endpoints without starting a server
@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """
    Introduction:
        - This fixture provides Flask's test client
    Returns:
        - FlaskClient: The test client
    """

    # Return the test client bound to the app
    return app.test_client()

# Authorization header with a token signed by the test secret
@pytest.fixture
def auth_headers(app: Flask) -> dict[str, str]:
    """
    Introduction:
        - This fixture generates a valid JWT for the test app
    Returns:
        - dict: The Authorization header with the token
    """

    # Tokens can only be created inside an application context
    with app.app_context():

        # Sign a token with the test secret key
        token = create_access_token(identity = "test-client")

    # Return the Authorization header
    return {"Authorization": f"Bearer {token}"}

# Valid request body reused across tests
@pytest.fixture
def valid_payload() -> dict[str, str]:
    """
    Introduction:
        - This fixture provides a request body that passes every validation
    Returns:
        - dict: A valid request body
    """

    # Return a payload with mixed-case email to also exercise normalization
    return {"email": "Juan@Mail.com", "app_uuid": "6f9619ff-8b86-d011-b42d-00cf4fc964ff", "blocked_reason": "Compliance request"}