# 1st Party Imports
from app.extensions import db
from datetime import datetime, timezone

# Email entry stored in the global blacklist
class Blacklist(db.Model):

    # Explicit table name in the database
    __tablename__ = "blacklist"

    # Internal numeric identifier
    id = db.Column(db.Integer, primary_key = True)

    # Normalized email; unique because an email is either blacklisted or not (409 on duplicates)
    email = db.Column(db.String(254), unique = True, nullable = False)

    # Client application that requested the block
    app_uuid = db.Column(db.Uuid, nullable = False)

    # Optional reason for the block, up to 255 characters
    blocked_reason = db.Column(db.String(255), nullable = True)

    # Client IP address; 45 characters fits the longest IPv6 representation
    request_ip = db.Column(db.String(45), nullable = False)

    # Server-side timestamp in UTC, never sent by the client
    created_at = db.Column(db.DateTime(timezone = True), nullable = False, default = lambda: datetime.now(timezone.utc))