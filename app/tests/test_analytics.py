import pytest
from app.models import User, Survey, Question, Response, Answer
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import seed
import json
from collections import Counter
from io import StringIO
from app.tests.conftest import get_token

# All fixtures (client, seeded_client, get_token) are now provided by conftest.py

def test_analytics_calculations(seeded_client):
    # Get a survey with multiple responses from seed data
    survey = Survey.objects.first()
    survey_id = str(survey.id)
    
    # Get admin token
    token = get_token(seeded_client, 'analyst', 'analyst@example.com', 'password123', 'admin')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get analytics
    resp = seeded_client.get(f'/surveys/{survey_id}/analytics', headers=headers)
    assert resp.status_code == 200
    analytics = resp.get_json()
    
    # Get all responses for verification
    responses = Response.objects(survey=survey)
    
    for question in survey.questions:
        qid = question.question_id
        assert qid in analytics
        
        # Get all answers for this question
        answers = [next(a for a in r.answers if a.question_id == qid) for r in responses if any(a.question_id == qid for a in r.answers)]
        
        if question.type == 'multiple_choice':
            if not answers:
                continue
            # Verify counts
            actual_counts = Counter(a.value for a in answers)
            api_counts = analytics[qid]['counts']
            assert actual_counts == Counter(api_counts)
            
            # Verify percentages
            total = len(answers)
            for choice, count in api_counts.items():
                expected_pct = (count / total) * 100
                assert abs(analytics[qid]['percentages'][choice] - expected_pct) < 0.1
            
        elif question.type == 'checkbox':
            if not answers:
                continue
            # Flatten all selected choices
            all_selections = [choice for a in answers for choice in a.value]
            actual_counts = Counter(all_selections)
            api_counts = analytics[qid]['counts']
            assert actual_counts == Counter(api_counts)
            
            # Verify selection rates
            total_responses = len(answers)
            for choice in question.choices:
                choice_responses = sum(1 for a in answers if choice in a.value)
                expected_rate = (choice_responses / total_responses) * 100
                assert abs(analytics[qid]['selection_rates'][choice] - expected_rate) < 0.1
            
        elif question.type == 'rating':
            if not answers:
                continue
            values = [a.value for a in answers]
            
            # Verify average
            expected_avg = sum(values) / len(values)
            assert abs(analytics[qid]['average'] - expected_avg) < 0.01
            
            # Verify median
            expected_median = sorted(values)[len(values)//2]
            assert analytics[qid]['median'] == expected_median
            
            # Verify distribution
            dist = analytics[qid]['distribution']
            for rating in range(question.min, question.max + 1):
                expected_count = sum(1 for v in values if v == rating)
                assert dist[str(rating)] == expected_count
            
        elif question.type == 'text':
            if not answers:
                continue
            # Verify response count
            assert analytics[qid]['response_count'] == len(answers)
            
            # Verify average length
            lengths = [len(str(a.value)) for a in answers]
            expected_avg_length = sum(lengths) / len(lengths) if lengths else 0
            assert abs(analytics[qid]['average_length'] - expected_avg_length) < 0.1

def test_analytics_time_series(seeded_client):
    # Get a survey from seed data
    survey = Survey.objects.first()
    survey_id = str(survey.id)
    
    # Get admin token
    token = get_token(seeded_client, 'timeanalyst', 'time@example.com', 'password123', 'admin')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get time series analytics
    resp = seeded_client.get(
        f'/surveys/{survey_id}/analytics?time_series=true&interval=daily',
        headers=headers
    )
    assert resp.status_code == 200
    analytics = resp.get_json()
    
    # Verify time series data
    assert 'time_series' in analytics
    time_data = analytics['time_series']
    
    # Get responses sorted by date
    responses = Response.objects(survey=survey).order_by('submitted_at')
    
    # Group responses by day
    response_dates = [r.submitted_at.date() for r in responses]
    daily_counts = Counter(response_dates)
    
    # Verify each day's count
    for entry in time_data:
        date = datetime.fromisoformat(entry['date']).date()
        assert entry['count'] == daily_counts[date]
        
    # Verify cumulative counts
    cumulative = 0
    for entry in time_data:
        cumulative += entry['count']
        assert entry['cumulative'] == cumulative

def test_analytics_export_formats(seeded_client):
    # Get a survey from seed data
    survey = Survey.objects(title='Test Survey 1').first()
    survey_id = str(survey.id)
    
    # Get admin token
    token = get_token(seeded_client, 'exporter', 'export@example.com', 'password123', 'admin')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test CSV export
    resp = seeded_client.get(f'/surveys/{survey_id}/export?format=csv', headers=headers)
    if resp.status_code == 404:
        pytest.skip('No responses to export for this survey')
    assert resp.status_code == 200
    assert resp.mimetype == 'text/csv'
    
    # Test Excel export
    resp = seeded_client.get(f'/surveys/{survey_id}/export?format=excel', headers=headers)
    assert resp.status_code == 200
    assert resp.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    # Test JSON export
    resp = seeded_client.get(f'/surveys/{survey_id}/export?format=json', headers=headers)
    assert resp.status_code == 200
    assert resp.mimetype == 'application/json'
    
    # Verify data consistency across formats
    responses = Response.objects(survey=survey)
    
    # Get JSON data
    json_data = resp.get_json()
    
    # Get CSV data
    resp = seeded_client.get(f'/surveys/{survey_id}/export?format=csv', headers=headers)
    csv_data = pd.read_csv(StringIO(resp.data.decode()))
    
    # Verify row counts match
    assert len(json_data) == len(csv_data) == responses.count()
    
    # Verify question columns exist in both formats
    for question in survey.questions:
        assert question.question_id in csv_data.columns
        assert all(question.question_id in r for r in json_data)

@pytest.mark.usefixtures('clean_and_seed')
def test_analytics_permissions(seeded_client):
    survey = Survey.objects(title='Test Survey 1').first()
    survey_id = str(survey.id)
    admin_token = get_token(seeded_client, 'admin', 'admin@example.com', 'adminpass', 'admin')
    resp_token = get_token(seeded_client, 'respondent', 'respondent@example.com', 'password123', 'respondent')
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    resp_headers = {'Authorization': f'Bearer {resp_token}'}
    endpoints = [
        f'/surveys/{survey_id}/analytics',
        f'/surveys/{survey_id}/export',
        f'/surveys/{survey_id}/analytics?time_series=true',
        f'/surveys/{survey_id}/analytics?cross_tab=q1,q2'
    ]
    for endpoint in endpoints:
        resp = seeded_client.get(endpoint, headers=admin_headers)
        assert resp.status_code == 200
        resp = seeded_client.get(endpoint, headers=resp_headers)
        assert resp.status_code == 403
        resp = seeded_client.get(endpoint)
        assert resp.status_code == 401

@pytest.mark.usefixtures('clean_and_seed')
def test_analytics_caching(seeded_client):
    survey = Survey.objects.first()
    survey_id = str(survey.id)
    token = get_token(seeded_client, 'admin', 'admin@example.com', 'adminpass', 'admin')
    headers = {'Authorization': f'Bearer {token}'}
    resp = seeded_client.get(f'/surveys/{survey_id}/analytics', headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get('X-Cache') in ('MISS', 'HIT')
    resp = seeded_client.get(f'/surveys/{survey_id}/analytics', headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get('X-Cache') == 'HIT'
    resp_token = get_token(seeded_client, 'resp', 'resp@example.com', 'resppass', 'respondent')
    resp_headers = {'Authorization': f'Bearer {resp_token}'}
    seeded_client.post(f'/surveys/{survey_id}/responses', json={
        'answers': [{'question_id': survey.questions[0].question_id, 'value': 'A'}]
    }, headers=resp_headers)
    resp = seeded_client.get(f'/surveys/{survey_id}/analytics', headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get('X-Cache') in ('MISS', 'HIT')

def test_analytics_and_csv(client):
    token = get_token(client, 'admin', 'admin@example.com', 'adminpass', 'admin')
    headers = {'Authorization': f'Bearer {token}'}
    # Create survey
    resp = client.post('/surveys/', json={
        'title': 'Test Survey',
        'description': 'A test survey.'
    }, headers=headers)
    survey_id = resp.get_json()['id']
    # Add questions
    client.post(f'/surveys/{survey_id}/questions', json={
        'question_id': 'q1',
        'type': 'multiple_choice',
        'text': 'Pick one',
        'order': 1,
        'choices': ['A', 'B'],
        'required': True
    }, headers=headers)
    client.post(f'/surveys/{survey_id}/questions', json={
        'question_id': 'q2',
        'type': 'rating',
        'text': 'Rate 1-5',
        'order': 2,
        'required': True
    }, headers=headers)
    # Submit responses
    for val in ['A', 'B', 'A']:
        client.post(f'/surveys/{survey_id}/responses', json={
            'answers': [
                {'question_id': 'q1', 'value': val},
                {'question_id': 'q2', 'value': 5}
            ]
        }, headers=headers)
    # Analytics
    resp = client.get(f'/surveys/{survey_id}/analytics', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'q1' in data and 'counts' in data['q1']
    assert data['q1']['counts']['A'] == 2
    # CSV Export
    resp = client.get(f'/surveys/{survey_id}/export', headers=headers)
    assert resp.status_code == 200
    assert resp.mimetype == 'text/csv'
    df = pd.read_csv(StringIO(resp.data.decode()))
    assert 'q1' in df.columns and 'q2' in df.columns

def test_analytics_unauthorized(client):
    resp = client.get('/surveys/someid/analytics')
    assert resp.status_code == 401

def test_analytics_forbidden(client):
    admin_token = get_token(client, 'admin2', 'admin2@example.com', 'adminpass', 'admin')
    resp_token = get_token(client, 'resp', 'resp@example.com', 'resppass', 'respondent')
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    resp_headers = {'Authorization': f'Bearer {resp_token}'}
    # Create survey
    resp = client.post('/surveys/', json={'title': 'Private Survey', 'description': ''}, headers=admin_headers)
    survey_id = resp.get_json()['id']
    # Respondent tries to get analytics
    resp = client.get(f'/surveys/{survey_id}/analytics', headers=resp_headers)
    assert resp.status_code == 403

def test_csv_no_responses(client):
    token = get_token(client, 'admin3', 'admin3@example.com', 'adminpass', 'admin')
    headers = {'Authorization': f'Bearer {token}'}
    # Create survey
    resp = client.post('/surveys/', json={'title': 'NoResp Survey', 'description': ''}, headers=headers)
    survey_id = resp.get_json()['id']
    # Add question
    client.post(f'/surveys/{survey_id}/questions', json={
        'question_id': 'q1',
        'type': 'text',
        'text': 'Text?',
        'order': 1,
        'required': True
    }, headers=headers)
    # Try to export CSV (no responses)
    resp = client.get(f'/surveys/{survey_id}/export', headers=headers)
    assert resp.status_code == 404 