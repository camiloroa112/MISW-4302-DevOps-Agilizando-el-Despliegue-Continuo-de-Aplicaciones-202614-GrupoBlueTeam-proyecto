# 1st Party Imports
import os

# 3rd Party Imports
from dotenv import load_dotenv
from sqlalchemy.engine import URL

# Load variables from a local .env file if present (no .env exists on Beanstalk)
load_dotenv()

# Environment variables the application cannot run without
REQUIRED_VARIABLES = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD", "JWT_SECRET_KEY")

# Return the names of required variables that are missing or empty
def get_missing_variables() -> list[str]:
    """
    Introduction:
        - This function checks the required environment variables for the application
    Returns:
        - list[str]: A list of missing variables
    """
    
    # Check each required variable against the current environment
    return [name for name in REQUIRED_VARIABLES if not os.environ.get(name)]

# Base configuration built from environment variables
class Config:

    # Build the PostgreSQL URL from separate parts so special characters in the password are escaped safely
    SQLALCHEMY_DATABASE_URI = URL.create(drivername = "postgresql+psycopg2", username = os.environ.get("DB_USER"), password = os.environ.get("DB_PASSWORD"), host = os.environ.get("DB_HOST"), port = int(os.environ.get("DB_PORT", "5432")), database = os.environ.get("DB_NAME"),)

    # Disable SQLAlchemy event tracking, which Flask-SQLAlchemy does not need
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Secret key used by Flask-JWT-Extended to sign and validate tokens
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")

    # The static token never expires
    JWT_ACCESS_TOKEN_EXPIRES = False

    # Let Flask-JWT-Extended errors reach their callbacks instead of becoming 500s in Flask-RESTful
    PROPAGATE_EXCEPTIONS = True