from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.models import Response, Survey, User, Answer
from app.schemas import ResponseSchema
from marshmallow import ValidationError
from datetime import datetime
from flasgger import swag_from
import os

SWAGGER_YAML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs')

responses_bp = Blueprint('responses', __name__)
responses_api = Api(responses_bp)

# Helper: Admin or owner required for listing

def admin_or_owner_required(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        user_id = get_jwt_identity()
        survey_id = kwargs.get('survey_id')
        survey = Survey.objects(id=survey_id).first()
        if not survey:
            return {'message': 'Survey not found.'}, 404
        if claims.get('role') == 'admin' or str(survey.owner.id) == user_id:
            return fn(*args, **kwargs)
        return {'message': 'Admins or survey owners only.'}, 403
    wrapper.__name__ = fn.__name__
    return wrapper

class ResponseListResource(Resource):
    @swag_from(os.path.join(SWAGGER_YAML_DIR, 'response_post.yml'))
    @jwt_required()
    def post(self, survey_id):
        user_id = get_jwt_identity()
        survey = Survey.objects(id=survey_id).first()
        if not survey:
            return {'message': 'Survey not found.'}, 404
            
        data = request.get_json()
        answers = data.get('answers', [])
        
        # Validate required questions
        question_map = {q.question_id: q for q in survey.questions}
        answered_questions = {a.get('question_id') for a in answers}
        
        for question in survey.questions:
            if question.required and question.question_id not in answered_questions:
                return {'message': f"Required question not answered: {question.question_id}"}, 400
                
        # Validate answers
        for ans in answers:
            qid = ans.get('question_id')
            if qid not in question_map:
                return {'message': f"Invalid question_id: {qid}"}, 400
                
            question = question_map[qid]
            value = ans.get('value')
            
            # Type-specific validation
            if question.type == 'multiple_choice':
                if value not in question.choices:
                    return {'message': f"Invalid choice for question {qid}: {value}"}, 400
            elif question.type == 'checkbox':
                if not isinstance(value, list):
                    return {'message': f"Checkbox answer must be a list for question {qid}"}, 400
                if not all(choice in question.choices for choice in value):
                    return {'message': f"Invalid choices for question {qid}: {value}"}, 400
            elif question.type == 'rating':
                try:
                    rating = int(value)
                    if not (question.min <= rating <= question.max):
                        return {'message': f"Rating must be between {question.min} and {question.max} for question {qid}"}, 400
                except (ValueError, TypeError):
                    return {'message': f"Invalid rating value for question {qid}: {value}"}, 400
                    
        respondent = User.objects(id=user_id).first()
        response = Response(
            survey=survey,
            respondent=respondent,
            submitted_at=datetime.utcnow(),
            answers=[Answer(**a) for a in answers]
        )
        response.save()
        result = {'id': str(response.id), **ResponseSchema().dump(response)}
        return jsonify(result), 201

    @swag_from(os.path.join(SWAGGER_YAML_DIR, 'response_list.yml'))
    @admin_or_owner_required
    def get(self, survey_id):
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        offset = (page - 1) * per_page
        
        responses = Response.objects(survey=survey_id).skip(offset).limit(per_page)
        total = Response.objects(survey=survey_id).count()
        
        result = {
            'items': [{'id': str(r.id), **ResponseSchema().dump(r)} for r in responses],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
        return jsonify(result)

class ResponseResource(Resource):
    @swag_from(os.path.join(SWAGGER_YAML_DIR, 'response_get.yml'))
    @admin_or_owner_required
    def get(self, survey_id, response_id):
        response = Response.objects(id=response_id, survey=survey_id).first()
        if not response:
            return {'message': 'Response not found.'}, 404
        result = {'id': str(response.id), **ResponseSchema().dump(response)}
        return jsonify(result)

responses_api.add_resource(ResponseListResource, '/<string:survey_id>/responses')
responses_api.add_resource(ResponseResource, '/<string:survey_id>/responses/<string:response_id>') 