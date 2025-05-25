from marshmallow import Schema, fields
from .question import QuestionSchema

class SurveySchema(Schema):
    id = fields.String(attribute="id")
    owner = fields.String(attribute="owner.id")
    title = fields.String(required=True)
    description = fields.String()
    questions = fields.List(fields.Nested(QuestionSchema))
    created_at = fields.DateTime()
    updated_at = fields.DateTime() 