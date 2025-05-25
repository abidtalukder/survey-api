from flask import Flask, Response as FlaskResponse
from flask_mongoengine import MongoEngine
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger
import redis
from .config import Config, TestConfig
from flask_caching import Cache
from .encoder import CustomJSONEncoder
from mongoengine import disconnect

# Initialize extensions
mongo = MongoEngine()
jwt = JWTManager()
bcrypt = Bcrypt()
limiter = Limiter(key_func=get_remote_address, default_limits=None)
swagger = Swagger()
redis_client = None
cache = Cache()

def create_app(config_class=Config):
    """
    Application factory for the Survey API.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Explicitly set the app's JSON encoder. 
    # For Flask 2.2.x, this influences jsonify and potentially extensions.
    # The RESTFUL_JSON config should ideally handle Flask-RESTful, but this is a belt-and-suspenders approach.
    app.json_encoder = CustomJSONEncoder 

    # Ensure no previous default connection exists before initializing
    try:
        disconnect(alias='default')
    except Exception:
        pass # Safely ignore if no connection was present

    # Initialize extensions
    mongo.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))
    limiter.init_app(app)
    swagger.init_app(app)
    cache.init_app(app)

    # Initialize Redis if configured
    global redis_client
    if app.config.get('REDIS_URL'):
        redis_client = redis.from_url(app.config['REDIS_URL'])
    else:
        redis_client = redis.Redis(host='localhost', port=6379, db=0)

    # Register blueprints
    from .blueprints import auth_bp, users_bp, surveys_bp, responses_bp, analytics_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(surveys_bp, url_prefix='/surveys')
    app.register_blueprint(responses_bp, url_prefix='/surveys')
    app.register_blueprint(analytics_bp, url_prefix='/surveys')

    return app
