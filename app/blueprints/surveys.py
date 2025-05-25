from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.models import Survey, User, Question
from app.schemas import SurveySchema, QuestionSchema
from marshmallow import ValidationError
from mongoengine.errors import ValidationError as MongoValidationError

surveys_bp = Blueprint('surveys', __name__)
surveys_api = Api(surveys_bp)

# Helper: Admin role required
def admin_required(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return {'message': 'Admins only.'}, 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

class SurveyListResource(Resource):
    @jwt_required()
    def get(self):
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        offset = (page - 1) * per_page
        
        surveys = Survey.objects().skip(offset).limit(per_page)
        total = Survey.objects().count()
        
        result = {
            'items': [{'id': str(s.id), **SurveySchema().dump(s)} for s in surveys],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
        return jsonify(result)

    @admin_required
    def post(self):
        data = request.get_json()
        try:
            validated = SurveySchema().load(data)
        except ValidationError as err:
            return {'message': 'Validation error', 'errors': err.messages}, 400
            
        owner = User.objects(id=get_jwt_identity()).first()
        if not owner:
            return {'message': 'Owner not found.'}, 404
            
        # Create survey with questions if provided
        survey = Survey(
            owner=owner,
            title=validated['title'],
            description=validated.get('description', ''),
            questions=[]
        )
        
        # Add questions if provided
        if 'questions' in data:
            try:
                questions_data = data['questions']
                for q_data in questions_data:
                    q_validated = QuestionSchema().load(q_data)
                    question = Question(**q_validated)
                    survey.questions.append(question)
            except ValidationError as err:
                return {'message': 'Question validation error', 'errors': err.messages}, 400
                
        survey.save()
        result = {'id': str(survey.id), **SurveySchema().dump(survey)}
        return jsonify(result), 201

class SurveyResource(Resource):
    @jwt_required()
    def get(self, survey_id):
        survey = Survey.objects(id=survey_id).first()
        if not survey:
            return {'message': 'Survey not found.'}, 404
        result = {'id': str(survey.id), **SurveySchema().dump(survey)}
        return jsonify(result)

    @admin_required
    def put(self, survey_id):
        survey = Survey.objects(id=survey_id).first()
        if not survey:
            return {'message': 'Survey not found.'}, 404
            
        data = request.get_json()
        try:
            validated = SurveySchema().load(data, partial=True)
        except ValidationError as err:
            return {'message': 'Validation error', 'errors': err.messages}, 400
            
        if 'title' in validated:
            survey.title = validated['title']
        if 'description' in validated:
            survey.description = validated.get('description', '')
            
        # Update questions if provided
        if 'questions' in data:
            try:
                questions_data = data['questions']
                survey.questions = []  # Clear existing questions
                for q_data in questions_data:
                    q_validated = QuestionSchema().load(q_data)
                    question = Question(**q_validated)
                    survey.questions.append(question)
            except ValidationError as err:
                return {'message': 'Question validation error', 'errors': err.messages}, 400
                
        survey.save()
        result = {'id': str(survey.id), **SurveySchema().dump(survey)}
        return jsonify(result)

    @admin_required
    def delete(self, survey_id):
        survey = Survey.objects(id=survey_id).first()
        if not survey:
            return {'message': 'Survey not found.'}, 404
        survey.delete()
        return {'message': 'Survey deleted.'}, 200

class QuestionListResource(Resource):
    @jwt_required()
    def get(self, survey_id):
        survey = Survey.objects(id=survey_id).first()
        if not survey:
            return {'message': 'Survey not found.'}, 404
        return jsonify(QuestionSchema(many=True).dump(survey.questions))

    @admin_required
    def post(self, survey_id):
        survey = Survey.objects(id=survey_id).first()
        if not survey:
            return {'message': 'Survey not found.'}, 404
            
        data = request.get_json()
        try:
            validated = QuestionSchema().load(data)
        except ValidationError as err:
            return {'message': 'Validation error', 'errors': err.messages}, 400
            
        # Validate question type specific requirements
        if validated['type'] == 'multiple_choice' or validated['type'] == 'checkbox':
            if not validated.get('choices'):
                return {'message': 'Choices are required for multiple choice and checkbox questions.'}, 400
            if len(validated['choices']) < 2:
                return {'message': 'At least two choices are required.'}, 400
            if len(validated['choices']) != len(set(validated['choices'])):
                return {'message': 'Duplicate choices are not allowed.'}, 400
                
        elif validated['type'] == 'rating':
            if 'min' not in validated or 'max' not in validated:
                validated['min'] = 1
                validated['max'] = 5
            elif validated['min'] >= validated['max']:
                return {'message': 'Min rating must be less than max rating.'}, 400
                
        # Create and add question
        question = Question(**validated)
        survey.questions.append(question)
        try:
            survey.save()
        except MongoValidationError as err:
            return {'message': 'Invalid question data.', 'errors': str(err)}, 400
            
        return jsonify(QuestionSchema().dump(question)), 201

class QuestionResource(Resource):
    @admin_required
    def put(self, survey_id, question_id):
        survey = Survey.objects(id=survey_id).first()
        if not survey:
            return {'message': 'Survey not found.'}, 404
        question = next((q for q in survey.questions if q.question_id == question_id), None)
        if not question:
            return {'message': 'Question not found.'}, 404
            
        data = request.get_json()
        try:
            validated = QuestionSchema().load(data, partial=True)
        except ValidationError as err:
            return {'message': 'Validation error', 'errors': err.messages}, 400
            
        # Update question
        for key, value in validated.items():
            setattr(question, key, value)
            
        try:
            survey.save()
        except MongoValidationError as err:
            return {'message': 'Invalid question data.', 'errors': str(err)}, 400
            
        return jsonify(QuestionSchema().dump(question))

    @admin_required
    def delete(self, survey_id, question_id):
        survey = Survey.objects(id=survey_id).first()
        if not survey:
            return {'message': 'Survey not found.'}, 404
        question = next((q for q in survey.questions if q.question_id == question_id), None)
        if not question:
            return {'message': 'Question not found.'}, 404
        survey.questions = [q for q in survey.questions if q.question_id != question_id]
        survey.save()
        return {'message': 'Question deleted.'}, 200

surveys_api.add_resource(SurveyListResource, '/')
surveys_api.add_resource(SurveyResource, '/<string:survey_id>')
surveys_api.add_resource(QuestionListResource, '/<string:survey_id>/questions')
surveys_api.add_resource(QuestionResource, '/<string:survey_id>/questions/<string:question_id>') 