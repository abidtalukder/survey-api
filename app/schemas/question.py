from marshmallow import Schema, fields, validate

class QuestionSchema(Schema):
    question_id = fields.String(required=True)
    type = fields.String(required=True, validate=validate.OneOf(["multiple_choice", "checkbox", "rating", "text"]))
    text = fields.String(required=True)
    order = fields.Integer(required=True)
    choices = fields.List(fields.String(), load_default=list)
    required = fields.Boolean(load_default=False)
    min = fields.Integer(load_default=1)
    max = fields.Integer(load_default=5) 