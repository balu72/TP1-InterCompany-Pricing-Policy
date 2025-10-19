"""Generic section generator node for LangGraph workflow."""
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from generation.state import PolicyGenerationState, POLICY_SECTIONS
from generation.rag_integration import RAGSystem

class SectionGenerator:
    """Base class for generating policy sections."""
    
    def __init__(self, rag_system: RAGSystem, prompts_dir: Path):
        """Initialize section generator."""
        self.rag_system = rag_system
        self.prompts_dir = prompts_dir
    
    def load_template(self, section_name: str) -> str:
        """Load prompt template for a section."""
        template_file = self.prompts_dir / f"{section_name}_prompt.txt"
        with open(template_file, 'r') as f:
            return f.read()
    
    def format_transactions(self, transactions: List) -> str:
        """Format transactions for template."""
        formatted = []
        for i, txn in enumerate(transactions, 1):
            formatted.append(f"""
Transaction {i}:
- Type: {txn.transaction_type}
- Description: {txn.description}
- Related Party: {txn.related_party_name} ({txn.related_party_jurisdiction})
- Amount: {txn.currency} {txn.amount:,.2f} if txn.amount else 'Not specified'
- Functions: {', '.join(txn.functions or [])}
- Assets: {', '.join(txn.assets or [])}
- Risks: {', '.join(txn.risks or [])}
- Risk Level: {txn.risk_level}
""")
        return "\n".join(formatted)
    
    def retrieve_context(self, section_name: str, jurisdiction: str, transaction_types: List[str]) -> str:
        """Retrieve relevant regulatory context from RAG."""
        # Build query based on section
        queries = {
            'executive_summary': f"executive summary requirements for transfer pricing documentation in {jurisdiction}",
            'related_parties': f"related party definition and identification requirements in {jurisdiction}",
            'functional_analysis': f"functional analysis FAR framework and requirements for {', '.join(transaction_types)} in {jurisdiction}",
            'comparability_analysis': f"comparability analysis five factors OECD guidelines {jurisdiction}",
            'tp_method': f"transfer pricing methods selection TNMM cost plus for {', '.join(transaction_types)} {jurisdiction}",
            'benchmarking': f"arm's length range benchmarking safe harbour provisions {jurisdiction} IT services margins",
            'documentation_requirements': f"transfer pricing documentation filing deadlines master file local file CbCR {jurisdiction}"
        }
        
        query = queries.get(section_name, f"{section_name} transfer pricing requirements {jurisdiction}")
        
        # Retrieve context chunks
        context_chunks = self.rag_system.retrieve_context(query)
        
        # Format context
        formatted_context = "\n\n---\n\n".join([f"REGULATORY SOURCE {i+1}:\n{chunk}" 
                                                 for i, chunk in enumerate(context_chunks)])
        
        return formatted_context
    
    def generate_section(self, state: PolicyGenerationState, section_name: str) -> str:
        """Generate a specific section."""
        # Load template
        template = self.load_template(section_name)
        
        # Retrieve regulatory context
        transaction_types = list(set([txn.transaction_type for txn in state['transactions']]))
        regulatory_context = self.retrieve_context(section_name, state['company'].jurisdiction, transaction_types)
        
        # Format transactions
        transactions_detail = self.format_transactions(state['transactions'])
        
        # Get related jurisdictions
        related_jurisdictions = list(set([txn.related_party_jurisdiction for txn in state['transactions']]))
        
        # Prepare template variables
        template_vars = {
            'regulatory_context': regulatory_context,
            'company_name': state['company'].name,
            'jurisdiction': state['company'].jurisdiction,
            'tax_id': state['company'].tax_id,
            'entity_type': state['company'].entity_type,
            'industry': state['company'].industry or 'Not specified',
            'fiscal_year': state['fiscal_year'],
            'transactions_detail': transactions_detail,
            'transaction_summary': f"{len(state['transactions'])} transactions with entities in {', '.join(related_jurisdictions)}",
            'related_jurisdictions': ', '.join(related_jurisdictions)
        }
        
        # Add section-specific variables
        if section_name == 'functional_analysis':
            template_vars['transactions_detail'] = transactions_detail
        
        if section_name in ['comparability_analysis', 'tp_method']:
            # Would need previous sections - simplified for now
            template_vars['functional_analysis_summary'] = state['sections'].get('functional_analysis', {}).get('content', 'See functional analysis section')
            template_vars['selected_method'] = 'TNMM'  # Default, should be determined dynamically
        
        if section_name == 'benchmarking':
            template_vars['selected_method'] = 'TNMM'
            template_vars['tested_party'] = state['company'].name
            template_vars['pli'] = 'Operating Margin on Operating Costs'
        
        # Fill template
        filled_template = template.format(**template_vars)
        
        # Generate using LLM via RAG system
        generated_content = self.rag_system.generate_with_context(
            prompt=filled_template,
            context_query=None  # Context already included in prompt
        )
        
        return generated_content

def create_section_node(section_name: str, rag_system: RAGSystem, prompts_dir: Path):
    """Factory function to create a section generation node."""
    generator = SectionGenerator(rag_system, prompts_dir)
    
    def node_function(state: PolicyGenerationState) -> PolicyGenerationState:
        """Node function for LangGraph."""
        try:
            print(f"Generating section: {section_name}")
            
            # Generate content
            content = generator.generate_section(state, section_name)
            
            # Extract citations (simplified - would need better parsing)
            citations = []
            if 'OECD' in content:
                citations.append("OECD Transfer Pricing Guidelines")
            if 'Rule 10' in content or 'CBDT' in content:
                citations.append(f"{state['company'].jurisdiction} Transfer Pricing Regulations")
            
            # Update state
            if 'sections' not in state:
                state['sections'] = {}
            
            state['sections'][section_name] = {
                'content': content,
                'status': 'generated',
                'citations': citations
            }
            
            # Update progress
            state['completed_sections'].append(section_name)
            progress = int((len(state['completed_sections']) / len(POLICY_SECTIONS)) * 100)
            
            # Log
            state['generation_log'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'section': section_name,
                'status': 'completed',
                'progress': progress
            })
            
            print(f"Completed section: {section_name} ({progress}% total)")
            
        except Exception as e:
            print(f"Error generating {section_name}: {e}")
            state['failed_sections'].append(section_name)
            state['errors'].append(f"{section_name}: {str(e)}")
            state['generation_log'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'section': section_name,
                'status': 'failed',
                'error': str(e)
            })
        
        return state
    
    return node_function
