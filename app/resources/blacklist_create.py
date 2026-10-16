# 1st Party Imports
from app.extensions import db
from app.models import Blacklist
from app.schemas import blacklist_create_schema

# 3rd Party Imports
from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import jwt_required

# POST /blacklists: add an email to the global blacklist
class BlacklistCreateResource(Resource):

    # Require a valid JWT before running the handler
    @jwt_required()
    def post(self) -> tuple[dict, int]:
        """
        Introduction:
            - This endpoint validates the request body and stores the email with the client IP and timestamp
        Returns:
            - dict: A status payload
        """

        # Parse the body without raising if it is not valid JSON
        payload = request.get_json(silent = True)

        # Reject bodies that are missing, not JSON, or not a JSON object
        if not isinstance(payload, dict):
            return {"msg": "Request body must be a JSON object"}, 400

        # Validate and normalize the payload with the schema
        try:
            data = blacklist_create_schema.load(payload)

        # Return every validation error grouped by field
        except ValidationError as error:
            return {"msg": "Invalid request", "errors": error.messages}, 400

        # Build the entry; IP and timestamp are set on the server, never by the client
        entry = Blacklist(email = data["email"], app_uuid = data["app_uuid"], blocked_reason = data["blocked_reason"], request_ip = request.remote_addr)

        # Stage the new entry in the session
        db.session.add(entry)

        # Persist the entry in PostgreSQL
        try:
            db.session.commit()

        # The unique constraint on email rejects duplicates
        except IntegrityError:

            # Undo the failed transaction so the session stays usable
            db.session.rollback()

            # Inform the client that the email already exists
            return {"msg": "Email already blacklisted"}, 409

        # Confirm the creation
        return {"msg": "Email added to the global blacklist"}, 201