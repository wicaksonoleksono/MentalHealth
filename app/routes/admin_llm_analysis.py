# app/routes/admin_llm_analysis.py
from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.decorators.auth import admin_required
from app.services.llm_analysis import LLMAnalysisService
from app.models.llm_analysis import LLMModel, LLMAnalysisResult, AnalysisConfiguration
from app import db

admin_llm_analysis_bp = Blueprint('admin_llm_analysis', __name__)
llm_service = LLMAnalysisService()

@admin_llm_analysis_bp.route('/admin/api/llm-analysis/config', methods=['POST'])
@login_required
@admin_required
def update_analysis_config():
    """Update analysis configuration"""
    try:
        data = request.get_json()
        instruction_prompt = data.get('instruction_prompt', '').strip()
        
        if not instruction_prompt:
            return jsonify({'success': False, 'error': 'Instruction prompt is required'})
        
        # Use hardcoded format from LLMAnalysisService
        config = llm_service.update_analysis_configuration(instruction_prompt, llm_service.ANALYSIS_FORMAT)
        return jsonify({'success': True, 'config_id': config.id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_llm_analysis_bp.route('/admin/api/llm-analysis/models', methods=['POST'])
@login_required
@admin_required
def add_llm_model():
    """Add a new LLM model"""
    try:
        data = request.get_json()
        model_name = data.get('model_name', '').strip()
        provider = data.get('provider', '').strip()
        
        if not model_name or not provider:
            return jsonify({'success': False, 'error': 'Model name and provider are required'})
        
        model = llm_service.add_llm_model(model_name, provider)
        return jsonify({
            'success': True, 
            'model': {
                'id': model.id,
                'name': model.name,
                'provider': model.provider,
                'api_key_configured': model.api_key_configured
            }
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to add model: {str(e)}'})

@admin_llm_analysis_bp.route('/admin/api/llm-analysis/models', methods=['DELETE'])
@login_required
@admin_required
def remove_llm_model():
    """Remove an LLM model"""
    try:
        data = request.get_json()
        model_name = data.get('model_name', '').strip()
        
        if not model_name:
            return jsonify({'success': False, 'error': 'Model name is required'})
        
        llm_service.remove_llm_model(model_name)
        return jsonify({'success': True})
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to remove model: {str(e)}'})

@admin_llm_analysis_bp.route('/admin/api/llm-analysis/models', methods=['GET'])
@login_required
@admin_required
def get_llm_models():
    """Get all LLM models"""
    try:
        models = llm_service.get_active_models()
        return jsonify({
            'success': True,
            'models': [{
                'id': model.id,
                'name': model.name,
                'provider': model.provider,
                'api_key_configured': model.api_key_configured,
                'is_active': model.is_active,
                'created_at': model.created_at.isoformat()
            } for model in models]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_llm_analysis_bp.route('/admin/api/llm-analysis/providers', methods=['GET'])
@login_required
@admin_required
def get_available_providers():
    """Get available LLM providers"""
    try:
        providers = llm_service.get_available_providers()
        return jsonify({'success': True, 'providers': providers})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_llm_analysis_bp.route('/admin/api/llm-analysis/analyze', methods=['POST'])
@login_required
@admin_required
def analyze_session():
    """Analyze a session with all active LLM models"""
    try:
        data = request.get_json()
        session_id = data.get('session_id', '').strip()
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID is required'})

        from app.models.assessment import Assessment
        assessment = Assessment.query.filter_by(session_id=session_id).first()
        if not assessment:
            return jsonify({'success': False, 'error': 'Assessment not found'})

        if assessment.llm_analysis_status == 'completed':
            return jsonify({'success': False, 'error': 'This session has already been analyzed.'})
        
        results = llm_service.analyze_session(session_id)
        
        return jsonify({
            'success': True,
            'results_count': len(results),
            'completed': len([r for r in results if r.analysis_status == 'completed']),
            'failed': len([r for r in results if r.analysis_status == 'failed'])
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Analysis failed: {str(e)}'})

@admin_llm_analysis_bp.route('/admin/api/llm-analysis/results/<session_id>', methods=['GET'])
@login_required
@admin_required
def get_analysis_results(session_id):
    """Get analysis results for a session"""
    try:
        results = llm_service.get_session_analysis_results(session_id)
        
        formatted_results = []
        for result in results:
            formatted_result = {
                'id': result.id,
                'session_id': result.session_id,
                'model_name': result.llm_model.name if result.llm_model else 'Unknown',
                'provider': result.llm_model.provider if result.llm_model else 'Unknown',
                'status': result.analysis_status,
                'error_message': result.error_message,
                'processing_time_ms': result.processing_time_ms,
                'created_at': result.created_at.isoformat(),
                'completed_at': result.completed_at.isoformat() if result.completed_at else None,
                'parsed_results': result.get_parsed_results(),
                'raw_response': result.raw_response
            }
            formatted_results.append(formatted_result)
        
        return jsonify({'success': True, 'data': formatted_results})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_llm_analysis_bp.route('/admin/api/llm-analysis/config', methods=['GET'])
@login_required
@admin_required
def get_analysis_config():
    """Get current analysis configuration"""
    try:
        config = AnalysisConfiguration.get_active_config()
        if config:
            return jsonify({
                'success': True,
                'config': {
                    'id': config.id,
                    'instruction_prompt': config.instruction_prompt,
                    'format_prompt': config.format_prompt,
                    'created_at': config.created_at.isoformat(),
                    'updated_at': config.updated_at.isoformat()
                }
            })
        else:
            return jsonify({'success': False, 'error': 'No active configuration found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_llm_analysis_bp.route('/admin/api/llm-analysis/check-pending', methods=['POST'])
@login_required
@admin_required
def check_pending_analysis():
    """Check for and process pending auto-analysis (safety net)"""
    try:
        from app.models.assessment import Assessment
        
        processed_sessions = Assessment.check_pending_auto_analysis()
        
        return jsonify({
            'success': True,
            'processed_count': len(processed_sessions),
            'processed_sessions': processed_sessions,
            'message': f'Processed {len(processed_sessions)} pending analyses'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to check pending analysis: {str(e)}'})