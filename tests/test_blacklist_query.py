# 1st Party Imports
from app.extensions import db
from app.models import Blacklist

# 3rd Party Imports
import pytest
import uuid
from flask import Flask
from flask.testing import FlaskClient

# Helper to add a blacklist entry directly


def add_blacklisted_email(app: Flask, email: str, reason: str | None) -> None:
    """
    Introduction:
        - Helper that inserts a blacklisted email using the test database
    Returns:
        - None
    """

    with app.app_context():
        entry = Blacklist(
            email=email,
            app_uuid=uuid.UUID("6f9619ff-8b86-d011-b42d-00cf4fc964ff"),
            blocked_reason=reason,
            request_ip="127.0.0.1",
        )
        db.session.add(entry)
        db.session.commit()


# A blacklisted email returns 200 with the reason
def test_query_blacklisted_email_returns_200(
    client: FlaskClient, auth_headers: dict, app: Flask
) -> None:
    """
    Introduction:
        - This test checks the success response for a blacklisted email
    Returns:
        - None
    """

    add_blacklisted_email(app, "blocked@example.com", "Compliance request")

    response = client.get("/blacklists/blocked@example.com", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == {
        "email": "blocked@example.com",
        "is_blacklisted": True,
        "blocked_reason": "Compliance request",
    }


# A non-blacklisted email returns 200 with false
def test_query_non_blacklisted_email_returns_200(
    client: FlaskClient, auth_headers: dict
) -> None:
    """
    Introduction:
        - This test checks the response for an email that is not blacklisted
    Returns:
        - None
    """

    response = client.get("/blacklists/free@example.com", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == {
        "email": "free@example.com",
        "is_blacklisted": False,
        "blocked_reason": None,
    }


# The email is normalized to lowercase before querying
def test_query_normalizes_email(
    client: FlaskClient, auth_headers: dict, app: Flask
) -> None:
    """
    Introduction:
        - This test checks that the query normalizes the email case
    Returns:
        - None
    """

    add_blacklisted_email(app, "mixed@example.com", None)

    response = client.get("/blacklists/Mixed@Example.com", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json()["is_blacklisted"] is True


# An empty email returns 400
def test_query_missing_email_returns_400(
    client: FlaskClient, auth_headers: dict
) -> None:
    """
    Introduction:
        - This test checks that an empty email parameter returns 400
    Returns:
        - None
    """

    response = client.get("/blacklists/", headers=auth_headers)

    assert response.status_code == 400
    assert "email" in response.get_json()["errors"]


# An invalid email format returns 400
def test_query_invalid_email_returns_400(
    client: FlaskClient, auth_headers: dict
) -> None:
    """
    Introduction:
        - This test checks that an invalid email format returns 400
    Returns:
        - None
    """

    response = client.get("/blacklists/not-an-email", headers=auth_headers)

    assert response.status_code == 400
    assert "email" in response.get_json()["errors"]


# Missing and invalid tokens both return 401
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer abc.def.ghi"}])
def test_query_without_valid_token_returns_401(
    client: FlaskClient, headers: dict
) -> None:
    """
    Introduction:
        - This test checks the unified 401 response from the JWT callbacks
    Returns:
        - None
    """

    response = client.get("/blacklists/test@example.com", headers=headers)

    assert response.status_code == 401
    assert response.get_json() == {"msg": "Missing or invalid token"}
