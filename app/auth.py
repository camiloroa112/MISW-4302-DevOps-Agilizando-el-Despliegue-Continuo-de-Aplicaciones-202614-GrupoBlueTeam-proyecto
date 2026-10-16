# 1st Party Imports
from app.extensions import jwt

# 3rd Party Imports
from flask import Response, jsonify

# Shared message for every authentication failure
UNAUTHORIZED_MESSAGE = "Missing or invalid token"

# Build the unified 401 response used by every JWT error callback
def unauthorized_response() -> tuple[Response, int]:
    """
    Introduction:
        - This function builds the shared response for any authentication failure
    Returns:
        - A JSON error payload with a 401 status
    """

    # Return the shared error payload with a 401 status
    return jsonify({"msg": UNAUTHORIZED_MESSAGE}), 401

# Handle requests without an Authorization header (401 by default)
def handle_missing_token(reason: str) -> tuple[Response, int]:
    """
    Introduction:
        - This callback runs when the request does not include a token
    Returns:
        - A JSON error payload with a 401 status
    """

    # Delegate to the unified response
    return unauthorized_response()

# Handle malformed or wrongly signed tokens (422 by default)
def handle_invalid_token(reason: str) -> tuple[Response, int]:
    """
    Introduction:
        - This callback runs when the token is malformed or its signature is invalid
    Returns:
        - A JSON error payload with a 401 status
    """

    # Delegate to the unified response
    return unauthorized_response()

# Handle expired tokens (unlikely, since the static token never expires)
def handle_expired_token(jwt_header: dict, jwt_payload: dict) -> tuple[Response, int]:
    """
    Introduction:
        - This callback runs when the token has expired
    Returns:
        - A JSON error payload with a 401 status
    """

    # Delegate to the unified response
    return unauthorized_response()

# Attach every error callback to the shared JWTManager instance
def register_jwt_callbacks() -> None:
    """
    Introduction:
        - This function registers the JWT error callbacks so every auth failure returns 401
    Returns:
        - None
    """

    # Missing Authorization header
    jwt.unauthorized_loader(handle_missing_token)

    # Malformed token or invalid signature
    jwt.invalid_token_loader(handle_invalid_token)

    # Expired token
    jwt.expired_token_loader(handle_expired_token)