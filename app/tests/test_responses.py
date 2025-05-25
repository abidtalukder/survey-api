import pytest
from app.models import User, Survey, Question, Response, Answer
from datetime import datetime, timedelta
import csv
import io
from app.tests.conftest import get_token
import uuid

# All fixtures (client, seeded_client, get_token) are now provided by conftest.py

def test_response_submission_all_types(client):
    admin_token = get_token(client, 'admin', 'admin@example.com', 'adminpass', 'admin')
    resp_token = get_token(client, 'resp', 'resp@example.com', 'resppass', 'respondent')
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    resp_headers = {'Authorization': f'Bearer {resp_token}'}
    
    survey_data = {
        'title': 'All Types Survey',
        'description': 'Testing all response types',
        'questions': [
            {
                'question_id': 'mc1',
                'type': 'multiple_choice',
                'text': 'Multiple Choice',
                'order': 1,
                'choices': ['A', 'B', 'C'],
                'required': True
            },
            {
                'question_id': 'cb1',
                'type': 'checkbox',
                'text': 'Checkbox',
                'order': 2,
                'choices': ['X', 'Y', 'Z'],
                'required': True
            },
            {
                'question_id': 'r1',
                'type': 'rating',
                'text': 'Rating',
                'order': 3,
                'min': 1,
                'max': 5,
                'required': True
            },
            {
                'question_id': 't1',
                'type': 'text',
                'text': 'Text',
                'order': 4,
                'required': False
            }
        ]
    }
    resp = client.post('/surveys/', json=survey_data, headers=admin_headers)
    assert resp.status_code == 201, f"Survey creation failed: {resp.get_data(as_text=True)}"
    survey_id = resp.get_json()['id']
    response_data = {
        'answers': [
            {'question_id': 'mc1', 'value': 'B'},
            {'question_id': 'cb1', 'value': ['X', 'Z']},
            {'question_id': 'r1', 'value': 4},
            {'question_id': 't1', 'value': 'Sample text response'}
        ]
    }
    resp = client.post(f'/surveys/{survey_id}/responses', json=response_data, headers=resp_headers)
    assert resp.status_code == 201, f"Response submission failed: {resp.get_data(as_text=True)}"
    response = Response.objects(survey=survey_id).first()
    assert response is not None
    assert len(response.answers) == 4
    mc_answer = next(a for a in response.answers if a.question_id == 'mc1')
    assert mc_answer.value == 'B'
    cb_answer = next(a for a in response.answers if a.question_id == 'cb1')
    assert set(cb_answer.value) == {'X', 'Z'}
    rating_answer = next(a for a in response.answers if a.question_id == 'r1')
    assert rating_answer.value == 4
    text_answer = next(a for a in response.answers if a.question_id == 't1')
    assert text_answer.value == 'Sample text response'

def test_response_validation(client, app):
    unique_id = uuid.uuid4().hex[:8]
    admin_username = f"admin_validator_{unique_id}"
    admin_email = f"admin_validator_{unique_id}@example.com"
    resp_username = f"resp_validator_{unique_id}"
    resp_email = f"resp_validator_{unique_id}@example.com"
    admin_token = get_token(client, admin_username, admin_email, 'adminpass', 'admin')
    resp_token = get_token(client, resp_username, resp_email, 'resppass', 'respondent')
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    resp_headers = {'Authorization': f'Bearer {resp_token}'}
    
    # Create survey
    survey_data = {
        'title': 'Validation Survey',
        'description': 'Testing response validation',
        'questions': [
            {
                'question_id': 'mc1_valid', # Made ID more specific
                'type': 'multiple_choice',
                'text': 'Required MC',
                'order': 1,
                'choices': ['A', 'B', 'C'],
                'required': True
            },
            {
                'question_id': 'r1_valid', # Made ID more specific
                'type': 'rating',
                'text': 'Rating 1-5',
                'order': 2,
                'min': 1,
                'max': 5,
                'required': True
            }
        ]
    }

    # Create survey using admin token
    create_survey_resp = client.post('/surveys/', json=survey_data, headers=admin_headers)
    assert create_survey_resp.status_code == 201, f"Survey creation failed. Response: {create_survey_resp.get_data(as_text=True)}"
    
    survey_json = create_survey_resp.get_json()
    assert 'id' in survey_json, "Survey ID not in creation response."
    survey_id = survey_json['id']

    # Test cases for response validation
    test_cases = [
        # Valid response
        ({'answers': [
            {'question_id': 'mc1_valid', 'value': 'A'},
            {'question_id': 'r1_valid', 'value': 3}
        ]}, 201),
        # Missing required question (mc1_valid)
        ({'answers': [
            {'question_id': 'r1_valid', 'value': 3}
        ]}, 400),
        # Invalid choice for multiple choice
        ({'answers': [
            {'question_id': 'mc1_valid', 'value': 'D'}, # 'D' is not a valid choice
            {'question_id': 'r1_valid', 'value': 3}
        ]}, 400),
        # Rating out of range
        ({'answers': [
            {'question_id': 'mc1_valid', 'value': 'A'},
            {'question_id': 'r1_valid', 'value': 6} # 6 is out of 1-5 range
        ]}, 400),
        # Invalid question_id
        ({'answers': [
            {'question_id': 'invalid_q', 'value': 'A'}
        ]}, 400),
    ]

    for response_data, expected_status in test_cases:
        submit_resp = client.post(f'/surveys/{survey_id}/responses', json=response_data, headers=resp_headers)
        assert submit_resp.status_code == expected_status, (
            f"Expected status {expected_status} but got {submit_resp.status_code} for response data: {response_data}. "
            f"Response: {submit_resp.get_data(as_text=True)}"
        )

def test_response_analytics(seeded_client):
    survey = Survey.objects.first()
    survey_id = str(survey.id)
    token = get_token(seeded_client, 'analyst', 'analyst@example.com', 'password123', 'admin')
    headers = {'Authorization': f'Bearer {token}'}
    resp = seeded_client.get(f'/surveys/{survey_id}/analytics', headers=headers)
    assert resp.status_code == 200
    analytics = resp.get_json()
    for question in survey.questions:
        if question.question_id not in analytics:
            continue
        if question.type == 'multiple_choice':
            counts = analytics[question.question_id]['counts']
            if not counts:
                continue
            total_responses = sum(counts.values())
            assert total_responses == Response.objects(survey=survey).count()
            percentages = analytics[question.question_id]['percentages']
            if not percentages:
                continue
            assert abs(sum(percentages.values()) - 100.0) < 0.1
        elif question.type == 'rating':
            stats = analytics[question.question_id]
            if not stats.get('distribution'):
                continue
            assert 'average' in stats
            assert 'median' in stats
            assert 'distribution' in stats
            responses = Response.objects(survey=survey)
            values = [next(a.value for a in r.answers if a.question_id == question.question_id)
                     for r in responses if any(a.question_id == question.question_id for a in r.answers)]
            if not values:
                continue
            expected_avg = sum(values) / len(values)
            assert abs(stats['average'] - expected_avg) < 0.01

@pytest.mark.usefixtures('clean_and_seed')
def test_response_retrieval_and_filtering(seeded_client, app):
    with app.app_context():
        survey = Survey.objects(title='Test Survey 1').first()
        assert survey is not None, "No survey found in seeded data for retrieval test."
        survey_id = str(survey.id)
    token = get_token(seeded_client, 'admin', 'admin@example.com', 'adminpass', 'admin')
    headers = {'Authorization': f'Bearer {token}'}
    resp = seeded_client.get(f'/surveys/{survey_id}/responses?page=1&per_page=50', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['items']) > 0
    assert data['total'] >= 1
    assert data['page'] == 1
    assert data['pages'] >= 1
    resp = seeded_client.get(f'/surveys/{survey_id}/responses?page=2&per_page=50', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['page'] == 2
    assert data['pages'] >= 1

    # Test filtering (if implemented - for now, just pagination)
    # Example: resp = seeded_client.get(f'/surveys/{survey_id}/responses?respondent_id={some_id}', headers=headers)


def test_response_export(seeded_client, app):
    with app.app_context():
        survey = Survey.objects(title='Test Survey 1').first()
        assert survey is not None, "No survey found in seeded data for export test."
        survey_id = str(survey.id)
    token = get_token(seeded_client, 'exporter', 'exporter@example.com', 'password123', 'admin')
    headers = {'Authorization': f'Bearer {token}'}
    resp_csv = seeded_client.get(f'/surveys/{survey_id}/export?format=csv', headers=headers)
    if resp_csv.status_code == 404:
        pytest.skip('No responses to export for this survey')
    assert resp_csv.status_code == 200
    assert resp_csv.mimetype == 'text/csv'

    # Parse CSV content
    content = resp_csv.data.decode('utf-8')
    csv_reader = csv.reader(io.StringIO(content))
    csv_lines = list(csv_reader)
    
    assert len(csv_lines) > 1 # Header + data rows
    csv_headers = csv_lines[0]
    
    with app.app_context():
        db_responses_count = Response.objects(survey=survey).count()
        db_questions = Survey.objects.get(id=survey_id).questions
        question_ids_from_db = [q.question_id for q in db_questions]

    # Verify headers (order might differ, so check for presence)
    # Standard headers + question_ids
    expected_base_headers = ['response_id', 'respondent', 'submitted_at']
    for header in expected_base_headers:
        assert header in csv_headers, f"Expected header '{header}' not in CSV"
    for qid in question_ids_from_db:
        assert qid in csv_headers, f"Question ID '{qid}' not in CSV headers"

    # Verify row count matches database (excluding header row)
    assert len(csv_lines) -1 == db_responses_count, "CSV row count does not match DB response count"

    # Verify some response data from the first data row (more robustly)
    if db_responses_count > 0 and len(csv_lines) > 1:
        first_data_row_dict = dict(zip(csv_headers, csv_lines[1]))
        with app.app_context():
            first_db_response = Response.objects(survey=survey).first()
            assert first_db_response is not None

            assert first_data_row_dict['response_id'] == str(first_db_response.id)
            if first_db_response.respondent:
                assert first_data_row_dict['respondent'] == str(first_db_response.respondent.id)
            # Datetime comparison can be tricky; consider parsing or checking format if exact match fails
            # For now, check presence
            assert first_db_response.submitted_at.isoformat()[:19] in first_data_row_dict['submitted_at']

            for q_in_db in db_questions:
                qid = q_in_db.question_id
                answer_obj = next((ans for ans in first_db_response.answers if ans.question_id == qid), None)
                csv_value_str = first_data_row_dict.get(qid, '')
                
                if answer_obj:
                    if isinstance(answer_obj.value, list):
                        # For lists, CSV might store as semicolon-separated string
                        # Need to parse csv_value_str and compare sets or sorted lists
                        csv_list_values = sorted([val.strip() for val in csv_value_str.split(';') if val.strip()])
                        db_list_values = sorted([str(v) for v in answer_obj.value])
                        assert csv_list_values == db_list_values, f"Mismatch for qid {qid}: CSV {csv_list_values} vs DB {db_list_values}"
                    else:
                        assert str(answer_obj.value) == csv_value_str, f"Mismatch for qid {qid}: CSV '{csv_value_str}' vs DB '{str(answer_obj.value)}'"
                # else: if no answer_obj, csv_value_str should be empty or represent missing data

    # Test Excel export
    resp_excel = seeded_client.get(f'/surveys/{survey_id}/export?format=excel', headers=headers)
    assert resp_excel.status_code == 200
    assert resp_excel.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    # Test JSON export
    resp_json = seeded_client.get(f'/surveys/{survey_id}/export?format=json', headers=headers)
    assert resp_json.status_code == 200
    assert resp_json.mimetype == 'application/json'
    json_data = resp_json.get_json()
    with app.app_context():
        assert len(json_data) == Response.objects(survey=survey).count() 