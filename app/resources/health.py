# 3rd Party Imports
from flask_restful import Resource

# Lightweight endpoint used by the Beanstalk load balancer health check
class HealthResource(Resource):

    # Respond 200 without authentication or database access
    def get(self) -> tuple[dict, int]:
        """
        Introduction:
            - This endpoint is used by the Beanstalk load balancer health check
        Returns:
            - A minimal status payload
        """
        
        # Return a minimal status payload
        return {"status": "ok"}, 200