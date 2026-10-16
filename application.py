# 1st Party Imports
from app import create_app

# WSGI entry point; Beanstalk looks for an object named "application" in application.py
application = create_app()