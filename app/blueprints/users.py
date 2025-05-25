from flask import Blueprint, request
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt
from app.models import User
from app.schemas import UserSchema, UserRegistrationSchema
from app import bcrypt
from marshmallow import ValidationError

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
    def get(self):
        users = User.objects()
        return UserSchema(many=True).dump(users), 200

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
    def get(self, user_id):
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found.'}, 404
        return UserSchema().dump(user), 200

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

    def delete(self, user_id):
        user = User.objects(id=user_id).first()
        if not user:
            return {'message': 'User not found.'}, 404
        user.delete()
        return {'message': 'User deleted.'}, 200

users_api.add_resource(UserListResource, '/')
users_api.add_resource(UserResource, '/<string:user_id>') 