from mongoengine import Document, ReferenceField, DateTimeField, EmbeddedDocumentListField
from datetime import datetime
from .survey import Survey
from .user import User
from .answer import Answer

class Response(Document):
    """
    Response model for storing survey answers.
    """
    survey = ReferenceField(Survey, required=True, reverse_delete_rule=2)  # CASCADE
    respondent = ReferenceField(User, required=False, reverse_delete_rule=3)  # NULLIFY
    submitted_at = DateTimeField(default=datetime.utcnow)
    answers = EmbeddedDocumentListField(Answer)

    meta = {
        'collection': 'responses',
        'indexes': [
            'survey',
            'respondent'
        ],
        'ordering': ['-submitted_at']
    } 