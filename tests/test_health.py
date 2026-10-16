# 3rd Party Imports
from flask.testing import FlaskClient

# The health check responds 200 without a token
def test_health_returns_ok(client: FlaskClient) -> None:
    """
    Introduction:
        - This test checks that /health works without authentication
    Returns:
        - None
    """

    # Call the health endpoint without headers
    response = client.get("/health")

    # The endpoint must respond 200
    assert response.status_code == 200

    # The payload must report an ok status
    assert response.get_json() == {"status": "ok"}