.PHONY: help install clean seed test

help:
	@echo "Available commands:"
	@echo "  install   Install Python dependencies"
	@echo "  clean     Drop all MongoDB data (local)"
	@echo "  seed      Seed the database with test data"
	@echo "  test      Run all tests with pytest"

install:
	pip install -r requirements.txt

clean:
	python3.11 -c "from app import create_app; from mongoengine.connection import get_db; app = create_app(); ctx = app.app_context(); ctx.push(); db = get_db(); db.client.drop_database(db.name); print('Database cleaned.'); ctx.pop()"

seed:
	python3.11 seed.py

test:
	python3.11 -m pytest 