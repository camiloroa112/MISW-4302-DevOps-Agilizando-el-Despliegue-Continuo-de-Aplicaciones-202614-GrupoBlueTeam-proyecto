# 1st Party Imports
from app.extensions import db
from app.models import Blacklist

# 3rd Party Imports
import pytest
from flask import Flask
from flask.testing import FlaskClient

# Read a stored entry directly from the database
def get_entry(app: Flask, email: str) -> Blacklist | None:
    """
    Introduction:
        - This helper fetches a blacklist entry by email
    Returns:
        - The entry, or None if it does not exist
    """

    # Queries require an application context
    with app.app_context():

        # Look up the entry by its normalized email
        return db.session.scalar(db.select(Blacklist).filter_by(email = email))

# A valid request is created
def test_create_returns_201(client: FlaskClient, auth_headers: dict, valid_payload: dict) -> None:
    """
    Introduction:
        - This test checks the success response of POST /blacklists
    Returns:
        - None
    """

    # Send a valid request
    response = client.post("/blacklists", json = valid_payload, headers = auth_headers)

    # The endpoint must respond 201
    assert response.status_code == 200

    # The confirmation message must match the contract
    assert response.get_json() == {"msg": "Email added to the global blacklist"}

# The server stores the normalized email, client IP and timestamp
def test_create_stores_server_side_fields(app: Flask, client: FlaskClient, auth_headers: dict, valid_payload: dict) -> None:
    """
    Introduction:
        - This test checks what is persisted after a successful request
    Returns:
        - None
    """

    # Send a valid request with a mixed-case email
    client.post("/blacklists", json = valid_payload, headers = auth_headers)

    # Fetch the entry using the lowercase email
    entry = get_entry(app, "juan@mail.com")

    # The entry must exist under the normalized email
    assert entry is not None

    # The UUID must be stored as sent
    assert str(entry.app_uuid) == valid_payload["app_uuid"]

    # The reason must be stored as sent
    assert entry.blocked_reason == "Compliance request"

    # The test client always calls from 127.0.0.1
    assert entry.request_ip == "127.0.0.1"

    # The timestamp must be set by the server
    assert entry.created_at is not None

# The reason is optional
def test_create_without_reason_returns_201(app: Flask, client: FlaskClient, auth_headers: dict, valid_payload: dict) -> None:
    """
    Introduction:
        - This test checks that blocked_reason can be omitted
    Returns:
        - None
    """

    # Remove the optional field from the payload
    payload = {key: value for key, value in valid_payload.items() if key != "blocked_reason"}

    # Send the request without a reason
    response = client.post("/blacklists", json = payload, headers = auth_headers)

    # The endpoint must still respond 201
    assert response.status_code == 201

    # The stored reason must be empty
    assert get_entry(app, "juan@mail.com").blocked_reason is None

# The same email in another case is a duplicate
def test_create_duplicate_email_returns_409(client: FlaskClient, auth_headers: dict, valid_payload: dict) -> None:
    """
    Introduction:
        - This test checks that emails are unique regardless of case
    Returns:
        - None
    """

    # Store the email the first time
    client.post("/blacklists", json = valid_payload, headers = auth_headers)

    # Send the same email in lowercase
    response = client.post("/blacklists", json = {**valid_payload, "email": "juan@mail.com"}, headers = auth_headers)

    # The endpoint must respond 409
    assert response.status_code == 409

    # The message must match the contract
    assert response.get_json() == {"msg": "Email already blacklisted"}

# Each required field is enforced
@pytest.mark.parametrize("missing_field", ["email", "app_uuid"])
def test_create_missing_required_field_returns_400(client: FlaskClient, auth_headers: dict, valid_payload: dict, missing_field: str) -> None:
    """
    Introduction:
        - This test checks that email and app_uuid are mandatory
    Returns:
        - None
    """

    # Remove the required field under test
    payload = {key: value for key, value in valid_payload.items() if key != missing_field}

    # Send the incomplete request
    response = client.post("/blacklists", json = payload, headers = auth_headers)

    # The endpoint must respond 400
    assert response.status_code == 400

    # The error must point to the missing field
    assert missing_field in response.get_json()["errors"]

# Invalid formats are rejected
@pytest.mark.parametrize("field, value", [("email", "not-an-email"), ("app_uuid", "123")])
def test_create_invalid_format_returns_400(client: FlaskClient, auth_headers: dict, valid_payload: dict, field: str, value: str) -> None:
    """
    Introduction:
        - This test checks the email and UUID format validations
    Returns:
        - None
    """

    # Send the payload with one invalid field
    response = client.post("/blacklists", json = {**valid_payload, field: value}, headers = auth_headers)

    # The endpoint must respond 400
    assert response.status_code == 400

    # The error must point to the invalid field
    assert field in response.get_json()["errors"]

# The reason accepts 255 characters but not 256
@pytest.mark.parametrize("length, expected_status", [(255, 201), (256, 400)])
def test_create_reason_length_limit(client: FlaskClient, auth_headers: dict, valid_payload: dict, length: int, expected_status: int) -> None:
    """
    Introduction:
        - This test checks the boundary of the 255-character limit
    Returns:
        - None
    """

    # Send a reason with the length under test
    response = client.post("/blacklists", json = {**valid_payload, "blocked_reason": "a" * length}, headers = auth_headers)

    # The status must match the expected result for that length
    assert response.status_code == expected_status

# Fields set by the server cannot be sent by the client
def test_create_unknown_field_returns_400(client: FlaskClient, auth_headers: dict, valid_payload: dict) -> None:
    """
    Introduction:
        - This test checks that unknown fields are rejected
    Returns:
        - None
    """

    # Try to send the IP in the body
    response = client.post("/blacklists", json = {**valid_payload, "request_ip": "1.1.1.1"}, headers = auth_headers)

    # The endpoint must respond 400
    assert response.status_code == 400

# A body that is not JSON is rejected
def test_create_non_json_body_returns_400(client: FlaskClient, auth_headers: dict) -> None:
    """
    Introduction:
        - This test checks the response to an invalid JSON body
    Returns:
        - None
    """

    # Send plain text declared as JSON
    response = client.post("/blacklists", data = "not json", content_type = "application/json", headers = auth_headers)

    # The endpoint must respond 400
    assert response.status_code == 400

    # The message must explain the problem
    assert response.get_json() == {"msg": "Request body must be a JSON object"}

# Missing and invalid tokens both return 401
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer abc.def.ghi"}])
def test_create_without_valid_token_returns_401(client: FlaskClient, valid_payload: dict, headers: dict) -> None:
    """
    Introduction:
        - This test checks the unified 401 response from the JWT callbacks
    Returns:
        - None
    """

    # Send the request without a valid token
    response = client.post("/blacklists", json = valid_payload, headers = headers)

    # The endpoint must respond 401, never 422 or 500
    assert response.status_code == 401

    # The message must match the contract
    assert response.get_json() == {"msg": "Missing or invalid token"}

# The IP comes from the load balancer header when present
def test_create_uses_forwarded_ip(app: Flask, client: FlaskClient, auth_headers: dict, valid_payload: dict) -> None:
    """
    Introduction:
        - This test checks that ProxyFix stores the client IP sent by the load balancer
    Returns:
        - None
    """

    # Simulate the header added by the load balancer
    client.post("/blacklists", json = valid_payload, headers = {**auth_headers, "X-Forwarded-For": "203.0.113.10"})

    # The stored IP must be the forwarded one
    assert get_entry(app, "juan@mail.com").request_ip == "203.0.113.10"