"""API routes for transaction management."""
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from models import db, Transaction, Company
from schemas.input_schema import TransactionInput

transactions_bp = Blueprint('transactions', __name__, url_prefix='/api/transactions')

@transactions_bp.route('', methods=['GET'])
def get_transactions():
    """Get all transactions or filter by company."""
    company_id = request.args.get('company_id', type=int)
    
    if company_id:
        transactions = Transaction.query.filter_by(company_id=company_id).all()
    else:
        transactions = Transaction.query.all()
    
    return jsonify({
        'transactions': [transaction.to_dict() for transaction in transactions]
    }), 200

@transactions_bp.route('/<int:transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """Get a specific transaction."""
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    return jsonify(transaction.to_dict()), 200

@transactions_bp.route('', methods=['POST'])
def create_transaction():
    """Create a new transaction."""
    try:
        # Validate input
        transaction_input = TransactionInput(**request.json)
        
        # Check if company exists
        company = Company.query.get(transaction_input.company_id)
        if not company:
            return jsonify({'error': 'Company not found'}), 404
        
        # Create transaction
        transaction = Transaction(
            company_id=transaction_input.company_id,
            transaction_type=transaction_input.transaction_type.value,
            description=transaction_input.description,
            related_party_name=transaction_input.related_party_name,
            related_party_jurisdiction=transaction_input.related_party_jurisdiction.value,
            amount=transaction_input.amount,
            currency=transaction_input.currency,
            fiscal_year=transaction_input.fiscal_year,
            functions=transaction_input.functional_profile.functions,
            assets=transaction_input.functional_profile.assets,
            risks=transaction_input.functional_profile.risks,
            risk_level=transaction_input.functional_profile.risk_level.value
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'message': 'Transaction created successfully',
            'transaction': transaction.to_dict()
        }), 201
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """Update an existing transaction."""
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    try:
        # Validate input
        transaction_input = TransactionInput(**request.json)
        
        # Update fields
        transaction.transaction_type = transaction_input.transaction_type.value
        transaction.description = transaction_input.description
        transaction.related_party_name = transaction_input.related_party_name
        transaction.related_party_jurisdiction = transaction_input.related_party_jurisdiction.value
        transaction.amount = transaction_input.amount
        transaction.currency = transaction_input.currency
        transaction.fiscal_year = transaction_input.fiscal_year
        transaction.functions = transaction_input.functional_profile.functions
        transaction.assets = transaction_input.functional_profile.assets
        transaction.risks = transaction_input.functional_profile.risks
        transaction.risk_level = transaction_input.functional_profile.risk_level.value
        
        db.session.commit()
        
        return jsonify({
            'message': 'Transaction updated successfully',
            'transaction': transaction.to_dict()
        }), 200
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    """Delete a transaction."""
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    try:
        db.session.delete(transaction)
        db.session.commit()
        
        return jsonify({'message': 'Transaction deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
