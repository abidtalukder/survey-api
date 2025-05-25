import pytest
from app.models import User, Survey, Question, Response
from datetime import datetime, timedelta
from app.tests.conftest import get_token
import uuid
import jwt
from flask_jwt_extended import decode_token

# All fixtures (client, seeded_client, get_token) are now provided by conftest.py

def test_survey_complete_flow(client):
    # Always register a unique user for survey creation
    unique_id = uuid.uuid4().hex[:8]
    username = f"admin_{unique_id}"
    email = f"admin_{unique_id}@example.com"
    token = get_token(client, username, email, 'adminpass', 'admin')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create survey
    survey_data = {
        'title': 'Test Survey',
        'description': 'A comprehensive test survey',
        'questions': [
            {
                'question_id': 'q1',
                'type': 'multiple_choice',
                'text': 'Pick one',
                'order': 1,
                'choices': ['A', 'B', 'C'],
                'required': True
            },
            {
                'question_id': 'q2',
                'type': 'checkbox',
                'text': 'Pick many',
                'order': 2,
                'choices': ['X', 'Y', 'Z'],
                'required': False
            }
        ]
    }
    
    resp = client.post('/surveys/', json=survey_data, headers=headers)
    assert resp.status_code == 201
    created_data = resp.get_json()
    survey_id = created_data['id']
    
    # Verify database state
    survey = Survey.objects(id=survey_id).first()
    assert survey is not None
    assert survey.title == survey_data['title']
    assert survey.description == survey_data['description']
    assert len(survey.questions) == 2
    assert survey.created_at is not None
    assert survey.updated_at is not None
    
    # Verify question data
    q1 = survey.questions[0]
    assert q1.question_id == 'q1'
    assert q1.type == 'multiple_choice'
    assert len(q1.choices) == 3
    
    # Update survey
    update_data = {
        'title': 'Updated Survey',
        'questions': [
            {
                'question_id': 'q1',
                'type': 'multiple_choice',
                'text': 'Updated question',
                'order': 1,
                'choices': ['A', 'B', 'C', 'D'],
                'required': True
            }
        ]
    }
    resp = client.put(f'/surveys/{survey_id}', json=update_data, headers=headers)
    assert resp.status_code == 200
    
    # Verify update in database
    updated_survey = Survey.objects(id=survey_id).first()
    assert updated_survey.title == update_data['title']
    assert len(updated_survey.questions) == 1
    assert len(updated_survey.questions[0].choices) == 4
    assert updated_survey.updated_at > updated_survey.created_at

def test_question_types_validation(client):
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    username = f"admin2_{unique_id}"
    email = f"admin2_{unique_id}@example.com"
    token = get_token(client, username, email, 'adminpass', 'admin')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create base survey
    resp = client.post('/surveys/', json={
        'title': 'Question Types Survey',
        'description': 'Testing all question types'
    }, headers=headers)
    survey_id = resp.get_json()['id']
    
    test_cases = [
        # Multiple choice
        {
            'valid': {
                'question_id': 'mc1',
                'type': 'multiple_choice',
                'text': 'Valid MC',
                'order': 1,
                'choices': ['A', 'B', 'C'],
                'required': True
            },
            'invalid': [
                # No choices
                {
                    'question_id': 'mc2',
                    'type': 'multiple_choice',
                    'text': 'Invalid MC',
                    'order': 2,
                    'choices': [],
                    'required': True
                },
                # Duplicate choices
                {
                    'question_id': 'mc3',
                    'type': 'multiple_choice',
                    'text': 'Invalid MC',
                    'order': 3,
                    'choices': ['A', 'A', 'B'],
                    'required': True
                }
            ]
        },
        # Rating
        {
            'valid': {
                'question_id': 'r1',
                'type': 'rating',
                'text': 'Valid Rating',
                'order': 4,
                'min': 1,
                'max': 5,
                'required': True
            },
            'invalid': [
                # Invalid range
                {
                    'question_id': 'r2',
                    'type': 'rating',
                    'text': 'Invalid Rating',
                    'order': 5,
                    'min': 5,
                    'max': 1,
                    'required': True
                }
            ]
        },
        # Text
        {
            'valid': {
                'question_id': 't1',
                'type': 'text',
                'text': 'Valid Text',
                'order': 6,
                'required': False
            },
            'invalid': [
                # Missing text
                {
                    'question_id': 't2',
                    'type': 'text',
                    'order': 7,
                    'required': True
                }
            ]
        }
    ]
    
    # Test valid questions
    for case in test_cases:
        resp = client.post(
            f'/surveys/{survey_id}/questions',
            json=case['valid'],
            headers=headers
        )
        assert resp.status_code == 201
        
        # Verify in database
        survey = Survey.objects(id=survey_id).first()
        question = next(q for q in survey.questions if q.question_id == case['valid']['question_id'])
        assert question is not None
        assert question.type == case['valid']['type']
        
        # Test invalid cases
        for invalid in case['invalid']:
            resp = client.post(
                f'/surveys/{survey_id}/questions',
                json=invalid,
                headers=headers
            )
            assert resp.status_code == 400

@pytest.mark.usefixtures('clean_and_seed')
def test_survey_permissions(seeded_client):
    admin = User.objects(username='admin').first()
    respondent = User.objects(username='respondent').first()
    admin_token = get_token(seeded_client, 'admin', 'admin@example.com', 'adminpass', 'admin')
    resp_token = get_token(seeded_client, 'respondent', 'respondent@example.com', 'password123', 'respondent')
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    resp_headers = {'Authorization': f'Bearer {resp_token}'}
    # Debug: print seeded admin id and JWT identity
    admin_id = str(admin.id)
    jwt_identity = decode_token(admin_token)['sub']
    print(f"Seeded admin id: {admin_id}, JWT identity: {jwt_identity}")
    assert admin_id == jwt_identity, f"JWT identity {jwt_identity} does not match seeded admin id {admin_id}"
    survey = Survey.objects(title='Test Survey 1').first()
    survey_id = str(survey.id)
    permission_tests = [
        (f'/surveys/', 'get', 200, 200),
        (f'/surveys/', 'post', 201, 403),
        (f'/surveys/{survey_id}', 'get', 200, 200),
        (f'/surveys/{survey_id}/questions', 'post', 201, 403),
        (f'/surveys/{survey_id}', 'put', 200, 403),
        (f'/surveys/{survey_id}', 'delete', 200, 403),
    ]
    for endpoint, method, admin_expected, resp_expected in permission_tests:
        if method == 'get':
            resp = seeded_client.get(endpoint, headers=admin_headers)
        elif method == 'post':
            test_data = {'title': 'Test'} if endpoint == '/surveys/' else {'question_id': 'test', 'type': 'text', 'text': 'Test', 'order': 1}
            resp = seeded_client.post(endpoint, json=test_data, headers=admin_headers)
            if endpoint == '/surveys/':
                print(f"POST /surveys/ status={resp.status_code}, body={resp.get_data(as_text=True)}")
        elif method == 'put':
            resp = seeded_client.put(endpoint, json={'title': 'Updated'}, headers=admin_headers)
        else:
            resp = seeded_client.delete(endpoint, headers=admin_headers)
        assert resp.status_code == admin_expected
        if method == 'get':
            resp = seeded_client.get(endpoint, headers=resp_headers)
        elif method == 'post':
            test_data = {'title': 'Test'} if endpoint == '/surveys/' else {'question_id': 'test', 'type': 'text', 'text': 'Test', 'order': 1}
            resp = seeded_client.post(endpoint, json=test_data, headers=resp_headers)
        elif method == 'put':
            resp = seeded_client.put(endpoint, json={'title': 'Updated'}, headers=resp_headers)
        else:
            resp = seeded_client.delete(endpoint, headers=resp_headers)
        assert resp.status_code == resp_expected

def test_survey_listing_and_filtering(seeded_client, app):
    token = get_token(seeded_client, 'listuser', 'list@example.com', 'password123', 'admin')
    headers = {'Authorization': f'Bearer {token}'}
    # Test pagination: request per_page=2. Seed data creates at least 3 surveys.
    resp = seeded_client.get('/surveys/?page=1&per_page=2', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['items']) == 2
    assert data['total'] >= 3 # There may be more than 3 surveys due to other tests
    assert data['page'] == 1
    assert data['pages'] >= 2 # There may be more than 2 pages if more surveys exist
    # Test second page
    resp = seeded_client.get('/surveys/?page=2&per_page=2', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    # There may be 1 or more items on the second page depending on total
    assert data['page'] == 2
    assert data['pages'] >= 2

    # Test filtering (if implemented - for now, just pagination and basic listing)
    # Example: Search for a survey with a specific title
    # with app.app_context(): # Use app_context if directly querying DB
    #     first_survey_title = Survey.objects.first().title
    # resp = seeded_client.get(f'/surveys/?title={first_survey_title}', headers=headers)
    # assert resp.status_code == 200
    # data = resp.get_json()
    # assert len(data['items']) >= 1
    # assert data['items'][0]['title'] == first_survey_title

@pytest.mark.usefixtures('clean_and_seed')
def test_survey_cascade_delete(seeded_client, app):
    token = get_token(seeded_client, 'deleteuser', 'deleteuser@example.com', 'password123', 'admin')
    admin_headers = {'Authorization': f'Bearer {token}'}
    with app.app_context():
        survey_to_delete = Survey.objects(title='Test Survey 1').first()
        assert survey_to_delete is not None, "Survey 'Test Survey 1' not found after seeding."
        survey_id = str(survey_to_delete.id)
        initial_response_count = Response.objects(survey=survey_to_delete).count()
        assert initial_response_count > 0, f"Survey '{survey_to_delete.title}' should have responses after seeding, but found {initial_response_count}."
        initial_question_count = len(survey_to_delete.questions)
        assert initial_question_count > 0, "Survey should have questions."
    resp = seeded_client.delete(f'/surveys/{survey_id}', headers=admin_headers)
    assert resp.status_code == 200, f"Failed to delete survey. Response: {resp.get_data(as_text=True)}"
    with app.app_context():
        assert Survey.objects(id=survey_id).first() is None, "Survey was not deleted from DB."
        assert Response.objects(survey=survey_id).count() == 0, "Responses were not deleted after survey deletion." 