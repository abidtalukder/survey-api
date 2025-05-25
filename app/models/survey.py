from mongoengine import Document, StringField, ReferenceField, DateTimeField, EmbeddedDocumentListField
from datetime import datetime
from .user import User
from .question import Question

class Survey(Document):
    """
    Survey model containing embedded questions.
    """
    owner = ReferenceField(User, required=True, reverse_delete_rule=2)  # CASCADE
    title = StringField(required=True, max_length=200)
    description = StringField()
    questions = EmbeddedDocumentListField(Question)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'surveys',
        'indexes': [
            'owner',
            'title'
        ],
        'ordering': ['-created_at']
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs) 