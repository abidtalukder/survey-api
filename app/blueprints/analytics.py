from flask import Blueprint, Response as FlaskResponse, request, current_app, jsonify
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app.models import Survey, Response as SurveyResponse
from app.schemas import ResponseSchema
import pandas as pd
import io
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps
import openpyxl
from app import cache

analytics_bp = Blueprint('analytics', __name__)
analytics_api = Api(analytics_bp)

# Cache decorator
def cache_response(timeout=300):  # 5 minutes default
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = f"{request.path}:{request.args}"
            
            # Use the imported cache object
            cached_data_tuple = cache.get(cache_key)
            if cached_data_tuple:
                # Data is stored as (data_json_string, status_code)
                response_data_str, status_code = cached_data_tuple
                response = FlaskResponse(response_data_str, status=status_code, mimetype='application/json')
                response.headers['X-Cache'] = 'HIT'
                return response
            
            # Get fresh response (which should be jsonify-able dict or a FlaskResponse)
            func_response = f(*args, **kwargs)

            # Ensure what we cache is a JSON string and status code
            if isinstance(func_response, FlaskResponse):
                # If it's already a FlaskResponse, assume it's correctly formatted
                # We need to be careful if it's not application/json
                if func_response.mimetype == 'application/json':
                    data_to_cache = func_response.get_data(as_text=True)
                    status_to_cache = func_response.status_code
                    response_to_return = func_response # Return the original FlaskResponse
                else:
                    # Non-JSON FlaskResponse, don't cache as is, or handle differently
                    # For now, just return it without caching to avoid issues.
                    return func_response 
            elif isinstance(func_response, tuple) and len(func_response) == 2:
                # Expected (dict_data, status_code)
                dict_data, status_to_cache = func_response
                data_to_cache = jsonify(dict_data).get_data(as_text=True) # Convert dict to JSON string
                response_to_return = FlaskResponse(data_to_cache, status=status_to_cache, mimetype='application/json')
            else: # Assuming it's a dict that needs to be jsonify-ed with status 200
                dict_data = func_response
                status_to_cache = 200
                data_to_cache = jsonify(dict_data).get_data(as_text=True)
                response_to_return = FlaskResponse(data_to_cache, status=status_to_cache, mimetype='application/json')

            cache.set(cache_key, (data_to_cache, status_to_cache), timeout=timeout)
            response_to_return.headers['X-Cache'] = 'MISS'
            return response_to_return
        return decorated_function
    return decorator

# Helper: Admin or owner required
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

class SurveyAnalyticsResource(Resource):
    @admin_or_owner_required
    @cache_response(timeout=300)
    def get(self, survey_id):
        survey = Survey.objects(id=survey_id).first()
        if not survey:
            return {'message': 'Survey not found.'}, 404
        
        responses = SurveyResponse.objects(survey=survey_id)
        analytics_data = {}
        
        if request.args.get('time_series'):
            interval = request.args.get('interval', 'daily')
            time_data = []
            responses_by_date = defaultdict(int)
            
            for r_obj in responses.order_by('submitted_at'):
                if interval == 'daily':
                    date_key = r_obj.submitted_at.date()
                elif interval == 'weekly':
                    date_key = r_obj.submitted_at.date() - timedelta(days=r_obj.submitted_at.weekday())
                else:
                    date_key = r_obj.submitted_at.replace(day=1).date()
                responses_by_date[date_key] += 1
            
            cumulative = 0
            for date_val in sorted(responses_by_date.keys()):
                count = responses_by_date[date_val]
                cumulative += count
                time_data.append({
                    'date': date_val.isoformat(),
                    'count': count,
                    'cumulative': cumulative
                })
            analytics_data['time_series'] = time_data
        
        for question in survey.questions:
            qid = question.question_id
            qtype = question.type
            qanswers = [a for resp_obj in responses for a in resp_obj.answers if a.question_id == qid]
            
            if qtype in ('multiple_choice', 'checkbox'):
                counts = defaultdict(int)
                for ans in qanswers:
                    val = ans.value
                    if isinstance(val, list):
                        for v_item in val:
                            counts[v_item] += 1
                    else:
                        counts[val] += 1
                
                num_responses_for_question = len(qanswers)

                percentages = {k: (v / num_responses_for_question * 100) if num_responses_for_question > 0 else 0 for k, v in counts.items()}
                if qtype == 'checkbox':
                    percentages = {k: (v / num_responses_for_question * 100) if num_responses_for_question > 0 else 0 for k, v in counts.items()}
                else:
                    total_selections = sum(counts.values())
                    percentages = {k: (v / total_selections * 100) if total_selections > 0 else 0 for k, v in counts.items()}

                analytics_data[qid] = {
                    'type': qtype,
                    'counts': dict(counts),
                    'percentages': percentages,
                    'total_responses': num_responses_for_question
                }
                
            elif qtype == 'rating':
                ratings = [ans.value for ans in qanswers if isinstance(ans.value, (int, float))]
                if ratings:
                    avg = sum(ratings) / len(ratings)
                    sorted_ratings = sorted(ratings)
                    mid = len(sorted_ratings) // 2
                    if len(sorted_ratings) % 2 == 0:
                        median = (sorted_ratings[mid - 1] + sorted_ratings[mid]) / 2.0
                    else:
                        median = sorted_ratings[mid]
                    distribution = defaultdict(int)
                    for r_val in ratings:
                        distribution[str(int(r_val))] += 1
                    analytics_data[qid] = {
                        'type': qtype,
                        'average': avg,
                        'median': median,
                        'distribution': dict(distribution),
                        'total_responses': len(ratings)
                    }
                else:
                    analytics_data[qid] = {'type': qtype, 'total_responses': 0, 'average': 0, 'median': 0, 'distribution': {}}
                    
            elif qtype == 'text':
                text_vals = [str(ans.value) for ans in qanswers if ans.value is not None]
                analytics_data[qid] = {
                    'type': qtype,
                    'response_count': len(text_vals),
                    'average_length': sum(len(r_text) for r_text in text_vals) / len(text_vals) if text_vals else 0,
                    'samples': text_vals[:5]
                }
        
        return analytics_data

class SurveyCSVExportResource(Resource):
    @admin_or_owner_required
    def get(self, survey_id):
        survey = Survey.objects(id=survey_id).first()
        if not survey:
            return {'message': 'Survey not found.'}, 404

        responses_qs = SurveyResponse.objects(survey=survey)
        if not responses_qs:
            return {'message': 'No responses found for this survey.'}, 404
            
        rows = []
        question_ids_ordered = [q.question_id for q in survey.questions]

        for r_obj in responses_qs:
            row_dict = {
                'response_id': str(r_obj.id),
                'respondent': str(r_obj.respondent.id) if r_obj.respondent else None,
                'submitted_at': r_obj.submitted_at.isoformat()
            }
            answers_map = {ans.question_id: ans for ans in r_obj.answers}
            for qid in question_ids_ordered:
                answer = answers_map.get(qid)
                if answer:
                    row_dict[qid] = ';'.join(map(str, answer.value)) if isinstance(answer.value, list) else str(answer.value)
                else:
                    row_dict[qid] = ''
            rows.append(row_dict)
            
        df = pd.DataFrame(rows)
        column_order = ['response_id', 'respondent', 'submitted_at'] + question_ids_ordered
        df = df[column_order]
        
        export_format = request.args.get('format', 'csv').lower()
        
        if export_format == 'excel':
            excel_buf = io.BytesIO()
            df.to_excel(excel_buf, index=False, engine='openpyxl')
            excel_buf.seek(0)
            return FlaskResponse(
                excel_buf.getvalue(),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment;filename=survey_{survey_id}_responses.xlsx'}
            )
        elif export_format == 'json':
            return rows, 200
        else:  # Default to CSV
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            csv_buf.seek(0)
            return FlaskResponse(
                csv_buf.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment;filename=survey_{survey_id}_responses.csv'}
            )

analytics_api.add_resource(SurveyAnalyticsResource, '/<string:survey_id>/analytics')
analytics_api.add_resource(SurveyCSVExportResource, '/<string:survey_id>/export') 