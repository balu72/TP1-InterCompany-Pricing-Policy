"""API routes for company management."""
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from models import db, Company
from schemas.input_schema import CompanyInput

companies_bp = Blueprint('companies', __name__, url_prefix='/api/companies')

@companies_bp.route('', methods=['GET'])
def get_companies():
    """Get all companies."""
    companies = Company.query.all()
    return jsonify({
        'companies': [company.to_dict() for company in companies]
    }), 200

@companies_bp.route('/<int:company_id>', methods=['GET'])
def get_company(company_id):
    """Get a specific company."""
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    return jsonify(company.to_dict()), 200

@companies_bp.route('', methods=['POST'])
def create_company():
    """Create a new company."""
    try:
        # Validate input
        company_input = CompanyInput(**request.json)
        
        # Create company
        company = Company(
            name=company_input.name,
            jurisdiction=company_input.jurisdiction.value,
            tax_id=company_input.tax_id,
            entity_type=company_input.entity_type.value,
            address=company_input.address,
            industry=company_input.industry,
            fiscal_year_end=company_input.fiscal_year_end
        )
        
        db.session.add(company)
        db.session.commit()
        
        return jsonify({
            'message': 'Company created successfully',
            'company': company.to_dict()
        }), 201
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@companies_bp.route('/<int:company_id>', methods=['PUT'])
def update_company(company_id):
    """Update an existing company."""
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    try:
        # Validate input
        company_input = CompanyInput(**request.json)
        
        # Update fields
        company.name = company_input.name
        company.jurisdiction = company_input.jurisdiction.value
        company.tax_id = company_input.tax_id
        company.entity_type = company_input.entity_type.value
        company.address = company_input.address
        company.industry = company_input.industry
        company.fiscal_year_end = company_input.fiscal_year_end
        
        db.session.commit()
        
        return jsonify({
            'message': 'Company updated successfully',
            'company': company.to_dict()
        }), 200
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@companies_bp.route('/<int:company_id>', methods=['DELETE'])
def delete_company(company_id):
    """Delete a company."""
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    try:
        db.session.delete(company)
        db.session.commit()
        
        return jsonify({'message': 'Company deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
