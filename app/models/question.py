from mongoengine import EmbeddedDocument, StringField, IntField, ListField, BooleanField

class Question(EmbeddedDocument):
    """
    Embedded document for survey questions.
    """
    question_id = StringField(required=True)
    type = StringField(required=True, choices=("multiple_choice", "checkbox", "rating", "text"))
    text = StringField(required=True)
    order = IntField(required=True)
    choices = ListField(StringField(), default=list)  # For multiple choice/checkbox
    required = BooleanField(default=False)
    min = IntField(default=1)  # For rating questions
    max = IntField(default=5)  # For rating questions 