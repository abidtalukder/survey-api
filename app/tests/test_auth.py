import pytest
from app import bcrypt
from app.models import User, Survey, Response, Question, Answer
from flask_jwt_extended import decode_token, create_access_token
from datetime import datetime, timedelta
import uuid # For generating unique usernames/emails
from app.tests.conftest import get_token

# All fixtures (client, get_token) are now provided by conftest.py

@pytest.fixture(scope='function')
def unique_user_credentials():
    """Provides unique username and email for testing user registration."""
    unique_id = uuid.uuid4().hex[:8] # Short unique ID
    return {
        "username": f"testuser_{unique_id}",
        "email": f"testuser_{unique_id}@example.com",
        "password": "password123",
        "role": "respondent"
    }

def test_register_complete_flow(client):
    # Register
    test_user = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
        'role': 'respondent'
    }
    resp = client.post('/auth/register', json=test_user)
    assert resp.status_code == 201
    
    # Verify database state
    user = User.objects(username=test_user['username']).first()
    assert user is not None
    assert user.email == test_user['email']
    assert user.role == test_user['role']
    assert bcrypt.check_password_hash(user.password, test_user['password'])
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)

    # Verify response data
    data = resp.get_json()
    assert data['username'] == test_user['username']
    assert 'password' not in data  # Password should not be in response
    assert data['role'] == test_user['role']

def test_login_token_contents(client):
    # Register user
    user_data = {
        'username': 'tokenuser',
        'email': 'token@example.com',
        'password': 'password123',
        'role': 'admin'
    }
    client.post('/auth/register', json=user_data)
    
    # Login
    resp = client.post('/auth/login', json={
        'username': user_data['username'],
        'password': user_data['password']
    })
    assert resp.status_code == 200
    data = resp.get_json()
    
    # Verify token contents
    access_token = data['access_token']
    refresh_token = data['refresh_token']
    with client.application.app_context():
        decoded_access = decode_token(access_token)
        decoded_refresh = decode_token(refresh_token)
        
        # Check access token claims
        assert decoded_access['sub'] == str(User.objects(username=user_data['username']).first().id)
        assert decoded_access['role'] == 'admin'
        assert decoded_access['type'] == 'access'
        
        # Check refresh token
        assert decoded_refresh['type'] == 'refresh'
        assert 'role' not in decoded_refresh

def test_password_hash_security(client):
    # Register multiple users with same password
    password = 'samepassword123'
    hashes = []
    for i in range(3):
        resp = client.post('/auth/register', json={
            'username': f'user{i}',
            'email': f'user{i}@example.com',
            'password': password,
            'role': 'respondent'
        })
        user = User.objects(username=f'user{i}').first()
        hashes.append(user.password)
    
    # Verify each hash is different (salt working)
    assert len(set(hashes)) == 3
    # Verify all hashes work with original password
    for h in hashes:
        assert bcrypt.check_password_hash(h, password)

def test_logout_token_blacklist(client):
    # Register and login
    client.post('/auth/register', json={
        'username': 'logoutuser',
        'email': 'logout@example.com',
        'password': 'password123',
        'role': 'respondent'
    })
    resp = client.post('/auth/login', json={
        'username': 'logoutuser',
        'password': 'password123'
    })
    token = resp.get_json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Use token successfully
    resp = client.get('/auth/profile', headers=headers)
    assert resp.status_code == 200
    
    # Logout
    resp = client.post('/auth/logout', headers=headers)
    assert resp.status_code == 200
    
    # Verify token is blacklisted
    resp = client.get('/auth/profile', headers=headers)
    assert resp.status_code in (401, 422)
    
    # Try to use token for other endpoints
    resp = client.get('/surveys/', headers=headers)
    assert resp.status_code in (401, 422)

def test_concurrent_sessions(client):
    # Register user
    client.post('/auth/register', json={
        'username': 'multiuser',
        'email': 'multi@example.com',
        'password': 'password123',
        'role': 'respondent'
    })
    
    # Login multiple times
    tokens = []
    for _ in range(3):
        resp = client.post('/auth/login', json={
            'username': 'multiuser',
            'password': 'password123'
        })
        tokens.append(resp.get_json()['access_token'])
    
    # All tokens should work
    for token in tokens:
        headers = {'Authorization': f'Bearer {token}'}
        resp = client.get('/auth/profile', headers=headers)
        assert resp.status_code == 200
    
    # Logout with one token
    headers = {'Authorization': f'Bearer {tokens[0]}'}
    client.post('/auth/logout', headers=headers)
    
    # Verify only that token is blacklisted
    resp = client.get('/auth/profile', headers=headers)
    assert resp.status_code in (401, 422)
    
    # Other tokens should still work
    for token in tokens[1:]:
        headers = {'Authorization': f'Bearer {token}'}
        resp = client.get('/auth/profile', headers=headers)
        assert resp.status_code == 200

def test_profile_data_accuracy(client):
    # Register with specific data
    test_data = {
        'username': 'profileuser',
        'email': 'profile@example.com',
        'password': 'password123',
        'role': 'admin'
    }
    client.post('/auth/register', json=test_data)
    
    # Login and get profile
    resp = client.post('/auth/login', json={
        'username': test_data['username'],
        'password': test_data['password']
    })
    token = resp.get_json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    resp = client.get('/auth/profile', headers=headers)
    assert resp.status_code == 200
    profile = resp.get_json()
    
    # Verify all fields
    assert profile['username'] == test_data['username']
    assert profile['email'] == test_data['email']
    assert profile['role'] == test_data['role']
    assert 'password' not in profile
    assert 'created_at' in profile
    assert 'updated_at' in profile

def test_registration_validation(client):
    test_cases = [
        # Username validations
        {
            'data': {'username': 'a', 'email': 'valid@example.com', 'password': 'password123', 'role': 'respondent'},
            'expected_status': 400,
            'error_field': 'username'
        },
        {
            'data': {'username': 'a' * 51, 'email': 'valid@example.com', 'password': 'password123', 'role': 'respondent'},
            'expected_status': 400,
            'error_field': 'username'
        },
        # Email validations
        {
            'data': {'username': 'validuser', 'email': 'notanemail', 'password': 'password123', 'role': 'respondent'},
            'expected_status': 400,
            'error_field': 'email'
        },
        # Password validations
        {
            'data': {'username': 'validuser', 'email': 'valid@example.com', 'password': '12345', 'role': 'respondent'},
            'expected_status': 400,
            'error_field': 'password'
        },
        # Role validations
        {
            'data': {'username': 'validuser', 'email': 'valid@example.com', 'password': 'password123', 'role': 'invalid'},
            'expected_status': 400,
            'error_field': 'role'
        }
    ]
    
    for case in test_cases:
        resp = client.post('/auth/register', json=case['data'])
        assert resp.status_code == case['expected_status']
        error_data = resp.get_json()
        assert 'errors' in error_data
        assert case['error_field'] in str(error_data['errors']).lower()
        
        # Verify no user was created in database
        user = User.objects(username=case['data']['username']).first()
        assert user is None

def test_register_and_login(client, unique_user_credentials):
    # Register with unique credentials
    reg_payload = unique_user_credentials
    resp = client.post('/auth/register', json=reg_payload)
    assert resp.status_code == 201, f"Registration failed. Response: {resp.get_data(as_text=True)}"
    user_data = resp.get_json()
    assert user_data['username'] == reg_payload['username']

    # Login
    login_payload = {
        "username": reg_payload['username'],
        "password": reg_payload['password']
    }
    resp = client.post('/auth/login', json=login_payload)
    assert resp.status_code == 200, f"Login failed. Response: {resp.get_data(as_text=True)}"
    token_data = resp.get_json()
    assert 'access_token' in token_data
    assert 'refresh_token' in token_data

    # Profile
    headers = {'Authorization': f"Bearer {token_data['access_token']}"}
    resp = client.get('/auth/profile', headers=headers)
    assert resp.status_code == 200
    profile = resp.get_json()
    assert profile['username'] == reg_payload['username']

def test_register_duplicate_user(client):
    client.post('/auth/register', json={
        'username': 'dupuser',
        'email': 'dup@example.com',
        'password': 'password123',
        'role': 'respondent'
    })
    resp = client.post('/auth/register', json={
        'username': 'dupuser',
        'email': 'dup@example.com',
        'password': 'password123',
        'role': 'respondent'
    })
    assert resp.status_code == 409

def test_register_invalid_data(client):
    # Missing fields
    resp = client.post('/auth/register', json={
        'username': 'short',
        'role': 'respondent'
    })
    assert resp.status_code == 400
    # Invalid email
    resp = client.post('/auth/register', json={
        'username': 'user2',
        'email': 'notanemail',
        'password': 'password123',
        'role': 'respondent'
    })
    assert resp.status_code == 400
    # Short password
    resp = client.post('/auth/register', json={
        'username': 'user3',
        'email': 'user3@example.com',
        'password': '123',
        'role': 'respondent'
    })
    assert resp.status_code == 400

def test_login_wrong_password(client):
    client.post('/auth/register', json={
        'username': 'user4',
        'email': 'user4@example.com',
        'password': 'password123',
        'role': 'respondent'
    })
    resp = client.post('/auth/login', json={
        'username': 'user4',
        'password': 'wrongpass'
    })
    assert resp.status_code == 401

def test_login_nonexistent_user(client):
    resp = client.post('/auth/login', json={
        'username': 'nouser',
        'password': 'password123'
    })
    assert resp.status_code == 401

def test_profile_requires_auth(client):
    resp = client.get('/auth/profile')
    assert resp.status_code == 401 