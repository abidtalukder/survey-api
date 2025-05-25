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