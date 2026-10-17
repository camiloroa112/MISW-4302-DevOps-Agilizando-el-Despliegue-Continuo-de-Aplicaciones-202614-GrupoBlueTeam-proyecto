# 1st Party Imports
from app.extensions import ma

# 3rd Party Imports
from marshmallow import fields, pre_load, validate


# Normalize an email so "Juan@Mail.com " and "juan@mail.com" are treated as the same
def normalize_email(value: str) -> str:
    """
    Introduction:
        - This function trims surrounding spaces and lowercases an email (shared by POST and GET)
    Returns:
        - str: The normalized email
    """

    # Remove surrounding spaces and lowercase the whole address
    return value.strip().lower()


# Validation rules for the POST /blacklists request body
class BlacklistCreateSchema(ma.Schema):
    # Required email with valid format, at most 254 characters
    email = fields.Email(required=True, validate=validate.Length(max=254))

    # Required client application identifier in UUID format
    app_uuid = fields.UUID(required=True)

    # Optional reason, None when omitted, at most 255 characters
    blocked_reason = fields.String(
        load_default=None, allow_none=True, validate=validate.Length(max=255)
    )

    # Normalize the email before validation runs
    @pre_load
    def normalize_email_field(self, data: dict, **kwargs) -> dict:
        """
        Introduction:
            - This hook normalizes the email before Marshmallow validates it
        Returns:
            - dict: The payload with the normalized email
        """

        # Only normalize strings; any other type will fail validation afterwards
        if isinstance(data.get("email"), str):
            # Copy the payload so the original request data is not mutated
            data = {**data, "email": normalize_email(data["email"])}

        # Return the (possibly) normalized payload
        return data


# Shared schema instance used by the POST resource
blacklist_create_schema = BlacklistCreateSchema()


# Validation rules for the GET /blacklists/<email> URL parameter
class BlacklistQuerySchema(ma.Schema):
    # Required email with valid format, at most 254 characters
    email = fields.Email(required=True, validate=validate.Length(max=254))

    # Normalize the email before validation runs
    @pre_load
    def normalize_email_field(self, data: dict, **kwargs) -> dict:
        """
        Introduction:
            - This hook normalizes the email before Marshmallow validates it
        Returns:
            - dict: The payload with the normalized email
        """

        # Only normalize strings; any other type will fail validation afterwards
        if isinstance(data.get("email"), str):
            # Copy the payload so the original request data is not mutated
            data = {**data, "email": normalize_email(data["email"])}

        # Return the (possibly) normalized payload
        return data


# Shared schema instance used by the GET resource
blacklist_query_schema = BlacklistQuerySchema()
