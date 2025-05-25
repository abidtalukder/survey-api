# Survey API

A full-featured REST API for survey collection and analytics, built with Flask, MongoDB, and Redis.

## Features
- User registration, login, and role-based access (admin/respondent)
- Survey creation, management, and analytics
- Multiple question types (multiple choice, checkbox, rating, free text)
- JWT authentication with Redis-backed token revocation
- Password hashing with Flask-Bcrypt
- Rate limiting, CORS, and OpenAPI docs
- CSV export of responses

## Setup
1. Clone the repo and navigate to the project directory.
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env` and update secrets and URIs as needed.
4. Run MongoDB and Redis locally or update URIs for remote services.
5. Start the app:
   ```bash
   flask run
   ```
6. For production, use Gunicorn or Docker.

## Testing
Run tests with:
```bash
pytest
```