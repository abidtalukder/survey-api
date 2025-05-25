from mongoengine import Document, StringField, EmailField, DateTimeField
from datetime import datetime

class User(Document):
    """
    User model for authentication and role management.
    """
    username = StringField(required=True, unique=True, max_length=50)
    email = EmailField(required=True, unique=True)
    password = StringField(required=True)  # Hashed password
    role = StringField(required=True, choices=("admin", "respondent"))
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'users',
        'indexes': [
            'username',
            'email',
            'role'
        ],
        'ordering': ['-created_at']
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs) 