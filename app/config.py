import os
from dotenv import load_dotenv
from datetime import timedelta
from app.encoder import CustomJSONEncoder

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
    MONGODB_SETTINGS = {
        'host': os.getenv('MONGODB_URI', 'mongodb://localhost:27017/survey_api'),
        'uuidRepresentation': 'standard'
    }
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    BCRYPT_LOG_ROUNDS = 12
    SWAGGER = {
        'title': 'Survey API',
        'uiversion': 3
    }
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_STORAGE_URL = REDIS_URL
    CORS_ORIGINS = ['*']
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    CACHE_KEY_PREFIX = "survey_api:"
    TESTING = False
    DEBUG = False
    RESTFUL_JSON = {'cls': CustomJSONEncoder}

class TestConfig(Config):
    TESTING = True
    MONGODB_SETTINGS = {
        'host': 'mongodb://localhost:27017/survey_api_test',
        'uuidRepresentation': 'standard'
    }
    CACHE_TYPE = "simple"
    CACHE_DEFAULT_TIMEOUT = 60  # 1 minute for testing
    CACHE_KEY_PREFIX = "test:"
    RESTFUL_JSON = {'cls': CustomJSONEncoder}
