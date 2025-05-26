"""
Swagger/OpenAPI configuration for the Survey API
"""

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,  # all in
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "openapi": "3.0.2",
    "uiversion": 3
}

swagger_template = {
    "openapi": "3.0.2",
    "info": {
        "title": "Survey API",
        "description": "Comprehensive API documentation for the Survey platform. This API allows for user management, survey creation, question management, response collection, analytics, and more.",
        "version": "1.0.0",
        "contact": {
            "email": "your-email@example.com"
        }
    },
    "servers": [
        {
            "url": "/",
            "description": "Local development server"
        }
    ],
    "components": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT Authorization header using the Bearer scheme. Example: 'Authorization: Bearer {token}'"
            }
        },
        "schemas": {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "example": "64b7c2f1e4b0f2a1b2c3d4e5"},
                    "username": {"type": "string", "example": "admin"},
                    "email": {"type": "string", "example": "admin@example.com"},
                    "role": {"type": "string", "enum": ["admin", "respondent"], "example": "admin"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"}
                }
            },
            "UserLoginInput": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "example": "admin"},
                    "password": {"type": "string", "example": "adminpass"}
                },
                "required": ["username", "password"]
            },
            "UserRegistrationInput": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "example": "newuser"},
                    "email": {"type": "string", "example": "newuser@example.com"},
                    "password": {"type": "string", "example": "password123"},
                    "role": {"type": "string", "enum": ["admin", "respondent"], "example": "respondent"}
                },
                "required": ["username", "email", "password", "role"]
            },
            "Survey": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "example": "64b7c2f1e4b0f2a1b2c3d4e6"},
                    "title": {"type": "string", "example": "Customer Satisfaction Survey"},
                    "description": {"type": "string", "example": "A survey to measure customer satisfaction."},
                    "owner": {"$ref": "#/components/schemas/User"},
                    "questions": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Question"}
                    },
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"}
                }
            },
            "SurveyInput": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "example": "Customer Satisfaction Survey"},
                    "description": {"type": "string", "example": "A survey to measure customer satisfaction."},
                    "questions": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/QuestionInput"}
                    }
                },
                "required": ["title"]
            },
            "Question": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string", "example": "q1"},
                    "text": {"type": "string", "example": "How satisfied are you with our service?"},
                    "type": {"type": "string", "enum": ["multiple_choice", "checkbox", "rating", "text"], "example": "multiple_choice"},
                    "choices": {"type": "array", "items": {"type": "string"}, "example": ["Very Satisfied", "Satisfied", "Neutral", "Dissatisfied"]},
                    "min": {"type": "integer", "example": 1},
                    "max": {"type": "integer", "example": 5},
                    "required": {"type": "boolean", "example": True},
                    "order": {"type": "integer", "example": 1}
                }
            },
            "QuestionInput": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "example": "How satisfied are you with our service?"},
                    "type": {"type": "string", "enum": ["multiple_choice", "checkbox", "rating", "text"], "example": "multiple_choice"},
                    "choices": {"type": "array", "items": {"type": "string"}, "example": ["Very Satisfied", "Satisfied", "Neutral", "Dissatisfied"]},
                    "min": {"type": "integer", "example": 1},
                    "max": {"type": "integer", "example": 5},
                    "required": {"type": "boolean", "example": True},
                    "order": {"type": "integer", "example": 1}
                },
                "required": ["text", "type"]
            },
            "Response": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "example": "64b7c2f1e4b0f2a1b2c3d4e7"},
                    "survey": {"$ref": "#/components/schemas/Survey"},
                    "respondent": {"$ref": "#/components/schemas/User"},
                    "submitted_at": {"type": "string", "format": "date-time"},
                    "answers": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Answer"}
                    }
                }
            },
            "ResponseInput": {
                "type": "object",
                "properties": {
                    "answers": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/AnswerInput"},
                        "example": [
                            {"question_id": "q1", "value": "Very Satisfied"},
                            {"question_id": "q2", "value": 5}
                        ]
                    }
                },
                "required": ["answers"]
            },
            "Answer": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string", "example": "q1"},
                    "value": {"type": "object", "example": "Very Satisfied"}
                }
            },
            "AnswerInput": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string", "example": "q1"},
                    "value": {"type": "object", "example": "Very Satisfied"}
                },
                "required": ["question_id", "value"]
            }
        }
    }
} 