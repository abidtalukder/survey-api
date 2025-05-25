from marshmallow import Schema, fields, validate, validates, ValidationError

class UserSchema(Schema):
    id = fields.String(attribute="id")
    username = fields.String(required=True, validate=validate.Length(min=3, max=50))
    email = fields.Email(required=True)
    role = fields.String(required=True, validate=validate.OneOf(["admin", "respondent"]))
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

class UserRegistrationSchema(Schema):
    username = fields.String(required=True, validate=validate.Length(min=3, max=50))
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=6))
    role = fields.String(required=True, validate=validate.OneOf(["admin", "respondent"]))

class UserLoginSchema(Schema):
    username = fields.String(required=True)
    password = fields.String(required=True) 