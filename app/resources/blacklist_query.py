# 1st Party Imports
from app.extensions import db
from app.models import Blacklist
from app.schemas import blacklist_query_schema

# 3rd Party Imports
from flask_restful import Resource
from marshmallow import ValidationError
from flask_jwt_extended import jwt_required
from sqlalchemy import select


# GET /blacklists/<string:email>: check if an email is in the global blacklist
class BlacklistQueryResource(Resource):
    """
    Introduction:
        - This resource handles the GET /blacklists/<email> endpoint.
    """
    
    # Require a valid JWT before running the handler
    @jwt_required()

    def get(self, email: str = "") -> tuple[dict, int]:
        """
        Introduction:
            - This endpoint returns whether the requested email is blacklisted and the reason
        Returns:
            - dict: The blacklist status payload
        """

        # Validate and normalize the email from the URL
        try:
            data = blacklist_query_schema.load({"email": email})

        # Return every validation error grouped by field
        except ValidationError as error:
            return {"msg": "Invalid request", "errors": error.messages}, 400

        # Look up the normalized email in the database
        normalized_email = data["email"]

        # Check if the email is blacklisted
        entry = db.session.scalar(select(Blacklist).filter_by(email=normalized_email))

        # Build the response following the documented contract
        if entry is not None:
            return {"email": normalized_email, "is_blacklisted": True, "blocked_reason": entry.blocked_reason,}, 200

        # The email is not blacklisted
        return {"email": normalized_email, "is_blacklisted": False, "blocked_reason": None,}, 200
