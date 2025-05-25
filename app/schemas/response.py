from marshmallow import Schema, fields
from .answer import AnswerSchema

class ResponseSchema(Schema):
    id = fields.String(attribute="id")
    survey = fields.String(attribute="survey.id")
    respondent = fields.String(attribute="respondent.id")
    submitted_at = fields.DateTime()
    answers = fields.List(fields.Nested(AnswerSchema)) 