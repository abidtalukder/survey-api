import pytest
from app import create_app, mongo
from app.config import TestConfig
from seed import seed_test_data
from app.models import User, Survey, Response # Import models for db cleanup
# from mongoengine import disconnect, connect # No longer doing manual connect/disconnect here
import uuid

@pytest.fixture(scope='session')
def app():
    """Session-wide test `Flask` application."""
    _app = create_app(TestConfig) # This will call mongo.init_app(_app)
    # _app.config['TESTING'] is already set by TestConfig
    
    ctx = _app.app_context()
    ctx.push()
    
    yield _app
    
    ctx.pop()
    # mongo.cx.close() # Potentially close client connection if issues persist, but init_app should handle

@pytest.fixture(scope='session')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def clean_db(app):
    """Clean the database before each test function."""
    with app.app_context():
        Response.objects.delete()
        Survey.objects.delete()
        User.objects.delete()
    yield

@pytest.fixture(scope='session')
def seeded_client(client, app):
    """A test client with pre-seeded data for the whole test session."""
    with app.app_context():
        seed_test_data()
    return client

@pytest.fixture(scope='function')
def clean_and_seed(app):
    """Clean and reseed the test database before each test function."""
    from app.models import User, Survey, Response
    with app.app_context():
        Response.objects.delete()
        Survey.objects.delete()
        User.objects.delete()
        seed_test_data()
    yield

# Make get_token a regular function, not a fixture

def get_token(client, username, email, password, role):
    _app = client.application
    with _app.app_context():
        # For seeded users, always try to login (never register)
        if username in ["admin", "respondent"]:
            login_resp = client.post('/auth/login', json={
                'username': username,
                'password': password
            })
            if login_resp.status_code == 200:
                login_data = login_resp.get_json()
                if 'access_token' in login_data:
                    return login_data['access_token']
                else:
                    raise KeyError(f"'access_token' not in login response for {username}. Response: {login_data}")
            else:
                raise ValueError(
                    f"Login failed for seeded user {username}. Status: {login_resp.status_code}, Response: {login_resp.get_data(as_text=True)}"
                )
        # For all other users, try login, then register if needed
        login_resp = client.post('/auth/login', json={
            'username': username,
            'password': password
        })
        if login_resp.status_code == 200:
            login_data = login_resp.get_json()
            if 'access_token' in login_data:
                return login_data['access_token']
        # Register if login fails
        reg_resp = client.post('/auth/register', json={
            'username': username,
            'email': email,
            'password': password,
            'role': role
        })
        assert reg_resp.status_code == 201, f"Registration failed for {username}: {reg_resp.get_data(as_text=True)}"
        login_resp = client.post('/auth/login', json={
            'username': username,
            'password': password
        })
        assert login_resp.status_code == 200, f"Login failed for {username} after registration: {login_resp.get_data(as_text=True)}"
        login_data = login_resp.get_json()
        assert 'access_token' in login_data, f"No access_token in login response for {username}: {login_data}"
        return login_data['access_token'] 