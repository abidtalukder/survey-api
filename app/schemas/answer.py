from marshmallow import Schema, fields

class AnswerSchema(Schema):
    question_id = fields.String(required=True)
    value = fields.Raw(required=True) 