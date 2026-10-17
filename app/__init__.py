# 1st Party Imports
from app.models import Blacklist
from app.extensions import db, jwt, ma
from app.auth import register_jwt_callbacks
from app.resources.health import HealthResource
from app.config import Config, get_missing_variables
from app.resources.blacklist_create import BlacklistCreateResource
from app.resources.blacklist_query import BlacklistQueryResource

# 3rd Party Imports
from flask import Flask
from flask_restful import Api
from werkzeug.middleware.proxy_fix import ProxyFix


# Application factory that builds and configures the Flask app
def create_app(config_class=Config) -> Flask:
    """
    Introduction:
        - This function creates and configures the Flask app
    Returns:
        - Flask app
    """

    # Create the Flask app
    app = Flask(__name__)

    # Load the configuration from the config class
    app.config.from_object(config_class)

    # Fail fast with a clear error if required variables are missing (skipped in tests)
    if not app.config.get("TESTING"):
        missing = get_missing_variables()

        # Raise an error if any required variables are missing
        if missing:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    # Trust exactly one proxy (the load balancer) to report the real client IP
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

    # Register the Flask-SQLAlchemy extension
    db.init_app(app)

    # Register the Flask-Marshmallow extension (must come after SQLAlchemy)
    ma.init_app(app)

    # Register the Flask-JWT-Extended extension
    jwt.init_app(app)

    # Make every authentication failure return a unified 401 response
    register_jwt_callbacks()

    # Create the database tables if they do not exist yet
    with app.app_context():
        db.create_all()

    # Create the REST API wrapper
    api = Api(app)

    # Register the health check endpoint
    api.add_resource(HealthResource, "/health")

    # Register the endpoint that adds emails to the blacklist
    api.add_resource(BlacklistCreateResource, "/blacklists")

    # Register the endpoint that queries emails in the blacklist
    api.add_resource(
        BlacklistQueryResource, "/blacklists/<string:email>", "/blacklists/"
    )

    # Return the configured app
    return app
