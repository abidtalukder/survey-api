from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
)
from mongoengine.errors import NotUniqueError
from app.models import User
from app.schemas import UserRegistrationSchema, UserLoginSchema, UserSchema
from app import bcrypt, redis_client, jwt
from datetime import timedelta
from flask_jwt_extended import current_user
from marshmallow import ValidationError
import uuid
from flasgger import swag_from

# Blueprint and API setup
auth_bp = Blueprint('auth', __name__)
auth_api = Api(auth_bp)

# Redis blacklist key prefix
JWT_REDIS_BLACKLIST_PREFIX = 'jwt_blacklist:'

# Helper: Add JWT to Redis blacklist
def add_token_to_blacklist(jti, expires):
    redis_client.setex(f"{JWT_REDIS_BLACKLIST_PREFIX}{jti}", int(expires), 'true')

# Helper: Check if JWT is blacklisted
def is_token_blacklisted(jti):
    return redis_client.exists(f"{JWT_REDIS_BLACKLIST_PREFIX}{jti}")

# Registration Resource
class RegisterResource(Resource):
    @swag_from({
        'tags': ['Authentication'],
        'summary': 'Register a new user',
        'description': 'Creates a new user account. Only "admin" and "respondent" roles are allowed. Returns the created user object.',
        'requestBody': {
            'required': True,
            'content': {
                'application/json': {
                    'schema': {'$ref': '#/components/schemas/UserRegistrationInput'},
                    'example': {
                        'username': 'newuser',
                        'email': 'newuser@example.com',
                        'password': 'password123',
                        'role': 'respondent'
                    }
                }
            }
        },
        'responses': {
            '201': {
                'description': 'User created successfully.',
                'content': {
                    'application/json': {
                        'schema': {'$ref': '#/components/schemas/User'},
                        'example': {
                            'id': '64b7c2f1e4b0f2a1b2c3d4e5',
                            'username': 'newuser',
                            'email': 'newuser@example.com',
                            'role': 'respondent',
                            'created_at': '2024-07-01T12:00:00Z',
                            'updated_at': '2024-07-01T12:00:00Z'
                        }
                    }
                }
            },
            '400': {
                'description': 'Validation error.',
                'content': {
                    'application/json': {
                        'example': {'message': 'Validation error', 'errors': {'email': ['Not a valid email address.']}}
                    }
                }
            },
            '409': {
                'description': 'Username or email already exists.',
                'content': {
                    'application/json': {
                        'example': {'message': 'Username already exists.'}
                    }
                }
            }
        }
    })
    def post(self):
        data = request.get_json()
        try:
            validated = UserRegistrationSchema().load(data)
        except ValidationError as err:
            return {'message': 'Validation error', 'errors': err.messages}, 400
            
        # Check for existing user
        if User.objects(username=validated['username']).first():
            return {'message': 'Username already exists.'}, 409
        if User.objects(email=validated['email']).first():
            return {'message': 'Email already exists.'}, 409
            
        hashed_pw = bcrypt.generate_password_hash(validated['password']).decode('utf-8')
        user = User(
            username=validated['username'],
            email=validated['email'],
            password=hashed_pw,
            role=validated['role']
        )
        user.save()
        return UserSchema().dump(user), 201

# Login Resource
class LoginResource(Resource):
    @swag_from({
        'tags': ['Authentication'],
        'summary': 'Authenticate user and obtain JWT tokens',
        'description': 'Authenticates a user and returns access and refresh JWT tokens along with user info.',
        'requestBody': {
            'required': True,
            'content': {
                'application/json': {
                    'schema': {'$ref': '#/components/schemas/UserLoginInput'},
                    'example': {
                        'username': 'admin',
                        'password': 'adminpass'
                    }
                }
            }
        },
        'responses': {
            '200': {
                'description': 'Login successful. Returns JWT tokens and user info.',
                'content': {
                    'application/json': {
                        'example': {
                            'access_token': '<JWT access token>',
                            'refresh_token': '<JWT refresh token>',
                            'user': {
                                'id': '64b7c2f1e4b0f2a1b2c3d4e5',
                                'username': 'admin',
                                'email': 'admin@example.com',
                                'role': 'admin',
                                'created_at': '2024-07-01T12:00:00Z',
                                'updated_at': '2024-07-01T12:00:00Z'
                            }
                        }
                    }
                }
            },
            '400': {
                'description': 'Validation error.',
                'content': {
                    'application/json': {
                        'example': {'message': 'Validation error', 'errors': {'username': ['Missing data for required field.']}}
                    }
                }
            },
            '401': {
                'description': 'Invalid username or password.',
                'content': {
                    'application/json': {
                        'example': {'message': 'Invalid username or password.'}
                    }
                }
            }
        }
    })
    def post(self):
        data = request.get_json()
        try:
            validated = UserLoginSchema().load(data)
        except ValidationError as err:
            return {'message': 'Validation error', 'errors': err.messages}, 400
        user = User.objects(username=validated['username']).first()
        if not user or not bcrypt.check_password_hash(user.password, validated['password']):
            return {'message': 'Invalid username or password.'}, 401
        access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
        refresh_token = create_refresh_token(identity=str(user.id))
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': UserSchema().dump(user)
        }, 200

# Logout Resource (JWT Blacklist)
class LogoutResource(Resource):
    @swag_from({
        'tags': ['Authentication'],
        'summary': 'Logout user (JWT Blacklist)',
        'description': 'Logs out the current user by blacklisting the JWT. Requires a valid JWT access token.',
        'security': [{'BearerAuth': []}],
        'responses': {
            '200': {
                'description': 'Successfully logged out.',
                'content': {
                    'application/json': {
                        'example': {'message': 'Successfully logged out.'}
                    }
                }
            },
            '401': {
                'description': 'Missing or invalid JWT.',
                'content': {
                    'application/json': {
                        'example': {'msg': 'Missing Authorization Header'}
                    }
                }
            }
        }
    })
    @jwt_required()
    def post(self):
        jwt_data = get_jwt()
        jti = jwt_data['jti']
        exp = jwt_data['exp']
        now = jwt_data['iat']
        expires = exp - now
        add_token_to_blacklist(jti, expires)
        return {'message': 'Successfully logged out.'}, 200

# Profile Resource
class ProfileResource(Resource):
    @swag_from({
        'tags': ['Authentication'],
        'summary': 'Get current user profile',
        'description': 'Returns the profile of the currently authenticated user. Requires a valid JWT access token.',
        'security': [{'BearerAuth': []}],
        'responses': {
            '200': {
                'description': 'User profile returned.',
                'content': {
                    'application/json': {
                        'schema': {'$ref': '#/components/schemas/User'},
                        'example': {
                            'id': '64b7c2f1e4b0f2a1b2c3d4e5',
                            'username': 'admin',
                            'email': 'admin@example.com',
                            'role': 'admin',
                            'created_at': '2024-07-01T12:00:00Z',
                            'updated_at': '2024-07-01T12:00:00Z'
                        }
                    }
                }
            },
            '401': {
                'description': 'Token has been revoked or is missing.',
                'content': {
                    'application/json': {
                        'example': {'message': 'Token has been revoked.'}
                    }
                }
            },
            '404': {
                'description': 'User not found.',
                'content': {
                    'application/json': {
                        'example': {'message': 'User not found.'}
                    }
                }
            }
        }
    })
    @jwt_required()
    def get(self):
        jwt_data = get_jwt()
        if is_token_blacklisted(jwt_data['jti']):
            return {'message': 'Token has been revoked.'}, 401
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found.'}, 404
        return UserSchema().dump(user), 200

# JWT callback to check blacklist
@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return is_token_blacklisted(jti)

auth_api.add_resource(RegisterResource, '/register')
auth_api.add_resource(LoginResource, '/login')
auth_api.add_resource(LogoutResource, '/logout')
auth_api.add_resource(ProfileResource, '/profile') 