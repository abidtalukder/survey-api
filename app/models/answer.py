from mongoengine import EmbeddedDocument, StringField, DynamicField

class Answer(EmbeddedDocument):
    """
    Embedded document for answers to survey questions.
    """
    question_id = StringField(required=True)
    value = DynamicField(required=True)  # Can be str, int, list, etc. 