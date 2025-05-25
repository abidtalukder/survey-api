import json
from flask import Response as FlaskResponse, current_app

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, FlaskResponse):
            # This is a Flask Response object. Flask-RESTful expects the data part.
            # If the response is not application/json, get_json will raise an error.
            # We should let Flask-RESTful handle its own response objects if they are
            # returned directly from resource methods. This encoder is more for
            # custom objects that might be part of the data payload that Flask/Flask-RESTful
            # tries to serialize.
            # However, if a FlaskResponse *is* passed to json.dumps directly (which is
            # what seems to be happening via Flask-RESTful sometimes), we need to handle it.
            if obj.mimetype == 'application/json':
                return obj.get_json() # This should be the already serialized JSON data
            else:
                # If it's not a JSON response, what should we do?
                # Returning the response text might be an option, or a representation.
                # For now, let default error handling occur for non-JSON FlaskResponse objects.
                current_app.logger.warning(f"CustomJSONEncoder encountered a non-JSON FlaskResponse: {obj}")
                return super().default(obj) # Will likely raise TypeError
        
        # Add handling for other non-standard types here if needed (e.g. datetime, ObjectId)
        # Example:
        # if isinstance(obj, datetime):
        #     return obj.isoformat()
        # if isinstance(obj, ObjectId):
        #     return str(obj)
        
        return super().default(obj) 