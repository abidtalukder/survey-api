import random
import string
from datetime import datetime, timedelta
from flask import current_app
from app.models import User, Survey, Question, Response, Answer

# Helper functions
def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def random_email():
    return f"{random_string(6)}@example.com"

def random_role():
    return random.choice(["admin", "respondent"])

def random_question_type():
    return random.choice(["multiple_choice", "checkbox", "rating", "text"])

def random_choices():
    return [random_string(4) for _ in range(random.randint(2, 5))]

def seed_test_data():
    """
    Create test data for the application.
    Uses current_app.app_context() so it can be called from test fixtures.
    """
    # Clear existing data in correct order to respect dependencies
    Response.objects.delete() # Responses refer to Surveys and Users
    Survey.objects.delete()   # Surveys refer to Users (owner)
    User.objects.delete()     # Users can now be safely deleted

    # Create test users
    admin = User(
        username='admin',
        email='admin@example.com',
        password='$2b$12$golh3CP7dtOkBhqsMCQVteZ/ymVI1wqgv4MDfGn4N6pArSFe3Z1Ve',  # 'adminpass'
        role='admin'
    ).save()
    print(f"Seeded admin: id={admin.id}, username={admin.username}, email={admin.email}")

    respondent = User(
        username='respondent',
        email='respondent@example.com',
        password='$2b$12$Bb63oXzCZfox4oaBgGb4L.mG0mhkSOQrE7aM0ytCMOT9rHbWp4xx.',  # 'password123'
        role='respondent'
    ).save()
    print(f"Seeded respondent: id={respondent.id}, username={respondent.username}, email={respondent.email}")
    
    # Create 3 surveys for better listing tests
    surveys = []
    for i in range(3):
        survey = Survey(
            owner=admin,
            title=f'Test Survey {i+1}',
            description=f'A test survey number {i+1}',
            questions=[
                Question(
                    question_id=f'q1_s{i+1}',
                    type='multiple_choice',
                    text='Multiple Choice Question',
                    order=1,
                    choices=['A', 'B', 'C'],
                    required=True
                ),
                Question(
                    question_id=f'q2_s{i+1}',
                    type='rating',
                    text='Rating Question',
                    order=2,
                    min=1,
                    max=5,
                    required=True
                ),
                Question(
                    question_id=f'q3_s{i+1}',
                    type='checkbox',
                    text='Checkbox Question',
                    order=3,
                    choices=['X', 'Y', 'Z'],
                    required=False
                ),
                Question(
                    question_id=f'q4_s{i+1}',
                    type='text',
                    text='Text Question',
                    order=4,
                    required=False
                )
            ]
        ).save()
        surveys.append(survey)

    # Use the first survey for detailed response seeding
    target_survey = surveys[0]

    # Create test responses
    choices = ['A', 'B', 'C']
    ratings = [1, 2, 3, 4, 5]
    checkbox_choices = [['X'], ['Y'], ['Z'], ['X', 'Y'], ['Y', 'Z'], ['X', 'Z'], ['X', 'Y', 'Z']]
    text_responses = [
        'Great survey!',
        'Interesting questions.',
        'Could be better.',
        'Very thorough.',
        'Nice work!'
    ]

    # Create 51 responses over the past week for the target_survey
    for i in range(51):
        Response(
            survey=target_survey,
            respondent=respondent, # This respondent will be used for these 51 responses
            submitted_at=datetime.utcnow() - timedelta(days=random.randint(0, 7)),
            answers=[
                Answer(question_id=f'q1_s1', value=random.choice(choices)),
                Answer(question_id=f'q2_s1', value=random.choice(ratings)),
                Answer(question_id=f'q3_s1', value=random.choice(checkbox_choices)),
                Answer(question_id=f'q4_s1', value=random.choice(text_responses))
            ]
        ).save()
    
    # Create another respondent for some other surveys if needed, or use the same admin/respondent
    # For example, to test analytics from different users or survey ownership scenarios.
    # For now, the above setup should cover many test cases.

    # After creating surveys
    print(f"Seeded survey: id={surveys[0].id}, title={surveys[0].title}, owner={surveys[0].owner.id}")

if __name__ == '__main__':
    import os
    from app import create_app
    from app.config import TestConfig
    from app.models import User, Survey, Response
    use_test_db = os.getenv('USE_TEST_DB', '0') == '1'
    if use_test_db:
        print('Seeding TEST database...')
        app = create_app(TestConfig)
    else:
        print('Seeding MAIN database...')
        app = create_app()
    with app.app_context():
        # Drop all collections to ensure a clean slate
        print('Dropping all collections...')
        Response.objects.delete()
        Survey.objects.delete()
        User.objects.delete()
        seed_test_data()
        print("Test data seeded successfully.") 