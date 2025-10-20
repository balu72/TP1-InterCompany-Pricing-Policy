"""API routes for policy management."""
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from datetime import datetime
from models import db, Policy, Company, Transaction
from schemas.input_schema import PolicyGenerationRequest, PolicyReviewRequest, SectionUpdateRequest
from utils.logger import get_logger

logger = get_logger(__name__)
policies_bp = Blueprint('policies', __name__, url_prefix='/api/policies')

@policies_bp.route('', methods=['GET'])
def get_policies():
    """Get all policies or filter by company."""
    company_id = request.args.get('company_id', type=int)
    
    if company_id:
        policies = Policy.query.filter_by(company_id=company_id).all()
    else:
        policies = Policy.query.all()
    
    return jsonify({
        'policies': [policy.to_dict(include_sections=False) for policy in policies]
    }), 200

@policies_bp.route('/<int:policy_id>', methods=['GET'])
def get_policy(policy_id):
    """Get a specific policy with full details."""
    policy = Policy.query.get(policy_id)
    if not policy:
        return jsonify({'error': 'Policy not found'}), 404
    
    return jsonify(policy.to_dict(include_sections=True)), 200

@policies_bp.route('/generate', methods=['POST'])
def generate_policy():
    """Trigger policy generation using LangGraph workflow."""
    try:
        logger.info("=" * 60)
        logger.info("POLICY GENERATION REQUEST INITIATED")
        logger.info("=" * 60)
        
        # Validate input
        gen_request = PolicyGenerationRequest(**request.json)
        logger.info(f"Request validated: company_id={gen_request.company_id}, "
                   f"transactions={gen_request.transaction_ids}, fiscal_year={gen_request.fiscal_year}")
        
        # Check if company exists
        company = Company.query.get(gen_request.company_id)
        if not company:
            logger.error(f"Company not found: {gen_request.company_id}")
            return jsonify({'error': 'Company not found'}), 404
        
        logger.info(f"Company found: {company.name} ({company.jurisdiction})")
        
        # Validate transactions exist
        transactions = Transaction.query.filter(
            Transaction.id.in_(gen_request.transaction_ids),
            Transaction.company_id == gen_request.company_id
        ).all()
        
        if len(transactions) != len(gen_request.transaction_ids):
            logger.error(f"Transaction validation failed. Requested: {gen_request.transaction_ids}, Found: {len(transactions)}")
            return jsonify({'error': 'Some transactions not found or do not belong to the company'}), 404
        
        logger.info(f"Validated {len(transactions)} transactions for policy generation")
        
        # Create policy record
        policy = Policy(
            company_id=gen_request.company_id,
            fiscal_year=gen_request.fiscal_year,
            status='generating',
            generation_progress=0,
            sections={},
            generation_log=[]
        )
        
        db.session.add(policy)
        db.session.commit()
        logger.info(f"Policy record created with ID: {policy.id}")
        
        # Prepare data for workflow
        from generation.state import CompanyData, TransactionData
        from generation.pricing_policy_workflow import create_workflow
        from flask import current_app
        
        company_data = CompanyData(
            id=company.id,
            name=company.name,
            jurisdiction=company.jurisdiction,
            tax_id=company.tax_id,
            entity_type=company.entity_type,
            industry=company.industry,
            fiscal_year_end=company.fiscal_year_end
        )
        
        transaction_data = [
            TransactionData(
                id=txn.id,
                transaction_type=txn.transaction_type,
                description=txn.description,
                related_party_name=txn.related_party_name,
                related_party_jurisdiction=txn.related_party_jurisdiction,
                amount=float(txn.amount) if txn.amount else None,
                currency=txn.currency,
                functions=txn.functions,
                assets=txn.assets,
                risks=txn.risks,
                risk_level=txn.risk_level
            )
            for txn in transactions
        ]
        
        # Execute workflow
        workflow = create_workflow(current_app.config)
        final_state = workflow.generate_policy(
            policy_id=policy.id,
            company=company_data,
            transactions=transaction_data,
            fiscal_year=gen_request.fiscal_year
        )
        
        # Update policy with generated sections
        policy.sections = final_state['sections']
        policy.generation_log = final_state['generation_log']
        policy.generation_progress = int((len(final_state['completed_sections']) / 7) * 100)
        
        if final_state['failed_sections']:
            policy.status = 'partial'
        else:
            policy.status = 'review'  # Ready for review
        
        db.session.commit()
        
        logger.info(f"Policy {policy.id} generation completed successfully")
        logger.info("=" * 60)
        
        # Serialize policy before closing session
        policy_data = policy.to_dict(include_sections=True)
        
        # Log complete policy
        logger.info("\n" + "=" * 80)
        logger.info("COMPLETE GENERATED POLICY DOCUMENT")
        logger.info("=" * 80)
        logger.info(f"Policy ID: {policy_data['id']}")
        logger.info(f"Company: {policy_data['company_id']}")
        logger.info(f"Fiscal Year: {policy_data['fiscal_year']}")
        logger.info(f"Status: {policy_data['status']}")
        logger.info(f"Progress: {policy_data['generation_progress']}%")
        logger.info("=" * 80)
        
        for section_name, section_data in policy_data['sections'].items():
            logger.info(f"\n{'=' * 80}")
            logger.info(f"SECTION: {section_name.upper().replace('_', ' ')}")
            logger.info(f"{'=' * 80}")
            logger.info(f"Status: {section_data['status']}")
            logger.info(f"Citations: {', '.join(section_data.get('citations', []))}")
            logger.info(f"\n{section_data['content']}\n")
            logger.info("=" * 80)
        
        logger.info("\n" + "=" * 80)
        logger.info("END OF POLICY DOCUMENT")
        logger.info("=" * 80 + "\n")
        
        db.session.close()  # Close session after serialization
        
        # Return complete policy with all sections
        return jsonify({
            'message': 'Policy generation completed',
            'policy': policy_data
        }), 200
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@policies_bp.route('/<int:policy_id>/sections/<section_name>', methods=['GET'])
def get_policy_section(policy_id, section_name):
    """Get a specific section of a policy."""
    policy = Policy.query.get(policy_id)
    if not policy:
        return jsonify({'error': 'Policy not found'}), 404
    
    section = policy.get_section(section_name)
    if not section:
        return jsonify({'error': 'Section not found'}), 404
    
    return jsonify({
        'section_name': section_name,
        'section': section
    }), 200

@policies_bp.route('/<int:policy_id>/sections/<section_name>', methods=['PATCH'])
def update_policy_section(policy_id, section_name):
    """Update a specific section (manual edit)."""
    policy = Policy.query.get(policy_id)
    if not policy:
        return jsonify({'error': 'Policy not found'}), 404
    
    if policy.status == 'approved':
        return jsonify({'error': 'Cannot edit approved policy'}), 403
    
    try:
        # Validate input
        update_request = SectionUpdateRequest(**request.json)
        
        # Update section
        policy.update_section(section_name, update_request.content, status='edited')
        
        return jsonify({
            'message': 'Section updated successfully',
            'section_name': section_name
        }), 200
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@policies_bp.route('/<int:policy_id>/sections/<section_name>/regenerate', methods=['POST'])
def regenerate_section(policy_id, section_name):
    """Regenerate a specific section."""
    policy = Policy.query.get(policy_id)
    if not policy:
        return jsonify({'error': 'Policy not found'}), 404
    
    if policy.status == 'approved':
        return jsonify({'error': 'Cannot regenerate sections of approved policy'}), 403
    
    try:
        # TODO: Trigger regeneration for specific section using LangGraph
        
        return jsonify({
            'message': 'Section regeneration initiated',
            'section_name': section_name,
            'note': 'Regeneration workflow will be implemented with LangGraph'
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@policies_bp.route('/<int:policy_id>/review', methods=['POST'])
def submit_review(policy_id):
    """Submit review for a policy."""
    policy = Policy.query.get(policy_id)
    if not policy:
        return jsonify({'error': 'Policy not found'}), 404
    
    try:
        # Validate input
        review_request = PolicyReviewRequest(**request.json)
        
        # Update policy
        policy.reviewed_by = review_request.reviewed_by
        policy.reviewed_at = datetime.utcnow()
        policy.review_comments = review_request.review_comments
        
        if review_request.approved:
            policy.status = 'approved'
            policy.approved_by = review_request.reviewed_by
            policy.approved_at = datetime.utcnow()
        else:
            policy.status = 'review'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Review submitted successfully',
            'policy': policy.to_dict(include_sections=False)
        }), 200
        
    except ValidationError as e:
        return jsonify({'error': 'Validation error', 'details': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@policies_bp.route('/<int:policy_id>', methods=['DELETE'])
def delete_policy(policy_id):
    """Delete a policy."""
    policy = Policy.query.get(policy_id)
    if not policy:
        return jsonify({'error': 'Policy not found'}), 404
    
    if policy.status == 'approved':
        return jsonify({'error': 'Cannot delete approved policy'}), 403
    
    try:
        db.session.delete(policy)
        db.session.commit()
        
        return jsonify({'message': 'Policy deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@policies_bp.route('/<int:policy_id>/export', methods=['GET'])
def export_policy(policy_id):
    """Export policy as DOCX."""
    policy = Policy.query.get(policy_id)
    if not policy:
        return jsonify({'error': 'Policy not found'}), 404
    
    # TODO: Implement document export
    return jsonify({
        'message': 'Export functionality will be implemented',
        'policy_id': policy_id
    }), 501
