from flask import Blueprint, request
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt
from app.models import User
from app.schemas import UserSchema, UserRegistrationSchema
from app import bcrypt
from marshmallow import ValidationError
from flasgger import swag_from

users_bp = Blueprint('users', __name__)
users_api = Api(users_bp)

# Helper: Admin role required
def admin_required(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return {'message': 'Admins only.'}, 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

class UserListResource(Resource):
    method_decorators = [admin_required]
    @swag_from({
        'tags': ['Users'],
        'summary': 'List all users',
        'description': 'Returns a list of all users. Admin only.',
        'security': [{'BearerAuth': []}],
        'responses': {
            '200': {
                'description': 'A list of users.',
                'content': {
                    'application/json': {
                        'schema': {'type': 'array', 'items': {'$ref': '#/components/schemas/User'}},
                        'example': [
                            {
                                'id': '64b7c2f1e4b0f2a1b2c3d4e5',
                                'username': 'admin',
                                'email': 'admin@example.com',
                                'role': 'admin',
                                'created_at': '2024-07-01T12:00:00Z',
                                'updated_at': '2024-07-01T12:00:00Z'
                            }
                        ]
                    }
                }
            },
            '403': {
                'description': 'Admins only.',
                'content': {'application/json': {'example': {'message': 'Admins only.'}}}
            }
        }
    })
    def get(self):
        users = User.objects()
        return UserSchema(many=True).dump(users), 200

    @swag_from({
        'tags': ['Users'],
        'summary': 'Create a new user',
        'description': 'Creates a new user. Admin only.',
        'security': [{'BearerAuth': []}],
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
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/User'}}}
            },
            '400': {
                'description': 'Validation error.',
                'content': {'application/json': {'example': {'message': 'Validation error'}}}
            },
            '403': {
                'description': 'Admins only.',
                'content': {'application/json': {'example': {'message': 'Admins only.'}}}
            }
        }
    })
    def post(self):
        data = request.get_json()
        try:
            validated = UserRegistrationSchema().load(data)
        except ValidationError as err:
            return {'message': 'Validation error', 'errors': err.messages}, 400
        hashed_pw = bcrypt.generate_password_hash(validated['password']).decode('utf-8')
        user = User(
            username=validated['username'],
            email=validated['email'],
            password=hashed_pw,
            role=validated['role']
        )
        user.save()
        return UserSchema().dump(user), 201

class UserResource(Resource):
    method_decorators = [admin_required]
    @swag_from({
        'tags': ['Users'],
        'summary': 'Get a user by ID',
        'description': 'Returns a user by their ID. Admin only.',
        'security': [{'BearerAuth': []}],
        'parameters': [
            {'name': 'user_id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}, 'description': 'User ID'}
        ],
        'responses': {
            '200': {
                'description': 'User found.',
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/User'}}}
            },
            '403': {
                'description': 'Admins only.',
                'content': {'application/json': {'example': {'message': 'Admins only.'}}}
            },
            '404': {
                'description': 'User not found.',
                'content': {'application/json': {'example': {'message': 'User not found.'}}}
            }
        }
    })
    def get(self, user_id):
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found.'}, 404
        return UserSchema().dump(user), 200

    @swag_from({
        'tags': ['Users'],
        'summary': 'Update a user by ID',
        'description': 'Updates a user by their ID. Admin only.',
        'security': [{'BearerAuth': []}],
        'parameters': [
            {'name': 'user_id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}, 'description': 'User ID'}
        ],
        'requestBody': {
            'required': True,
            'content': {
                'application/json': {
                    'schema': {'$ref': '#/components/schemas/UserRegistrationInput'},
                    'example': {
                        'username': 'updateduser',
                        'email': 'updated@example.com',
                        'password': 'newpassword',
                        'role': 'respondent'
                    }
                }
            }
        },
        'responses': {
            '200': {
                'description': 'User updated successfully.',
                'content': {'application/json': {'schema': {'$ref': '#/components/schemas/User'}}}
            },
            '403': {
                'description': 'Admins only.',
                'content': {'application/json': {'example': {'message': 'Admins only.'}}}
            },
            '404': {
                'description': 'User not found.',
                'content': {'application/json': {'example': {'message': 'User not found.'}}}
            }
        }
    })
    def put(self, user_id):
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found.'}, 404
        data = request.get_json()
        if 'password' in data:
            data['password'] = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        user.modify(**data)
        user.reload()
        return UserSchema().dump(user), 200

    @swag_from({
        'tags': ['Users'],
        'summary': 'Delete a user by ID',
        'description': 'Deletes a user by their ID. Admin only.',
        'security': [{'BearerAuth': []}],
        'parameters': [
            {'name': 'user_id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}, 'description': 'User ID'}
        ],
        'responses': {
            '200': {
                'description': 'User deleted.',
                'content': {'application/json': {'example': {'message': 'User deleted.'}}}
            },
            '403': {
                'description': 'Admins only.',
                'content': {'application/json': {'example': {'message': 'Admins only.'}}}
            },
            '404': {
                'description': 'User not found.',
                'content': {'application/json': {'example': {'message': 'User not found.'}}}
            }
        }
    })
    def delete(self, user_id):
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found.'}, 404
        user.delete()
        return {'message': 'User deleted.'}, 200

users_api.add_resource(UserListResource, '/')
users_api.add_resource(UserResource, '/<string:user_id>') 