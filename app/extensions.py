# 3rd Party Imports
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow

# Initialize Flask extensions
db = SQLAlchemy()

# Initialize Flask-JWT-Extended extensions
ma = Marshmallow()

# Initialize Flask-JWT-Extended Manager
jwt = JWTManager()