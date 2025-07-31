# app/routes/phq.py
from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.decorators.auth import admin_required
from app.services.phq import PHQ, PHQException

phq_bp = Blueprint('phq', __name__)

@phq_bp.route('/available-categories', methods=['GET'])
@login_required
@admin_required
def get_available_categories():
    """Get all PHQ-9 categories for frontend dropdown"""
    try:
        categories = PHQ.get_available_categories()
        return jsonify({
            'success': True,
            'categories': categories
        })
    except PHQException as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@phq_bp.route('/categories', methods=['POST'])
@login_required
@admin_required
def create_category():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        category_number = data.get('category_number')
        if not category_number:
            return jsonify({'success': False, 'error': 'Category number required'}), 400
            
        PHQ.create_category(
            category_number=category_number,
            category_name=data.get('category_name'),
            description=data.get('description'),
            add_default_question=data.get('add_default_question', True)
        )
        
        return jsonify({'success': True, 'message': 'Category created successfully'})
        
    except PHQException as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@phq_bp.route('/categories/create-all', methods=['POST'])
@login_required
@admin_required
def create_all_categories():
    """Create all standard PHQ-9 categories"""
    try:
        created_count = PHQ.create_all_standard_categories()
        return jsonify({
            'success': True,
            'message': f'Created {created_count} new categories'
        })
    except PHQException as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@phq_bp.route('/category/<int:category_number>/questions', methods=['POST'])
@login_required
@admin_required
def add_question(category_number):
    try:
        question_text = request.json.get('question_text')
        if not question_text:
            return jsonify({'success': False, 'error': 'Question text required'}), 400

        PHQ.add_question_to_category(category_number, question_text)
        return jsonify({'success': True, 'message': 'Question added successfully'})

    except PHQException as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@phq_bp.route('/question/<int:question_id>', methods=['PUT'])
@login_required
@admin_required
def update_question(question_id):
    try:
        data = request.json
        PHQ.update_question(question_id, data)
        return jsonify({'success': True, 'message': 'Question updated successfully'})

    except PHQException as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@phq_bp.route('/question/<int:question_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_question(question_id):
    try:
        PHQ.delete_question(question_id)
        return jsonify({'success': True, 'message': 'Question deleted successfully'})

    except PHQException as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@phq_bp.route('/category/<int:category_number>', methods=['DELETE'])
@login_required
@admin_required
def delete_category(category_number):
    try:
        PHQ.delete_category(category_number)
        return jsonify({'success': True, 'message': 'Category deleted successfully'})

    except PHQException as e:
        return jsonify({'success': False, 'error': str(e)}), 400
