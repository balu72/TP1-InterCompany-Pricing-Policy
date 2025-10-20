"""Dedicated node classes for each policy section using LangGraph."""
from pathlib import Path
from typing import Dict, List
from abc import ABC, abstractmethod
from datetime import datetime
from generation.state import PolicyGenerationState, POLICY_SECTIONS
from generation.rag_integration import RAGSystem


class BaseSectionNode(ABC):
    """Abstract base class for policy section generation nodes."""
    
    def __init__(self, rag_system: RAGSystem, prompts_dir: Path):
        """Initialize section node."""
        self.rag_system = rag_system
        self.prompts_dir = prompts_dir
    
    @abstractmethod
    def get_section_name(self) -> str:
        """Return the section name this node handles."""
        pass
    
    def load_template(self) -> str:
        """Load prompt template for this section."""
        section_name = self.get_section_name()
        template_file = self.prompts_dir / f"{section_name}_prompt.txt"
        with open(template_file, 'r') as f:
            return f.read()
    
    def format_transactions(self, transactions: List) -> str:
        """Format transactions for template."""
        formatted = []
        for i, txn in enumerate(transactions, 1):
            amount_str = f"{txn.amount:,.2f}" if txn.amount else "Not specified"
            formatted.append(f"""
Transaction {i}:
- Type: {txn.transaction_type}
- Description: {txn.description}
- Related Party: {txn.related_party_name} ({txn.related_party_jurisdiction})
- Amount: {txn.currency} {amount_str}
- Functions: {', '.join(txn.functions or [])}
- Assets: {', '.join(txn.assets or [])}
- Risks: {', '.join(txn.risks or [])}
- Risk Level: {txn.risk_level}
""")
        return "\n".join(formatted)
    
    def retrieve_context(self, jurisdiction: str, transaction_types: List[str]) -> str:
        """Retrieve relevant regulatory context from RAG."""
        query = self.build_context_query(jurisdiction, transaction_types)
        
        # Retrieve context chunks
        context_chunks = self.rag_system.retrieve_context(query)
        
        # Format context
        formatted_context = "\n\n---\n\n".join([f"REGULATORY SOURCE {i+1}:\n{chunk}" 
                                                 for i, chunk in enumerate(context_chunks)])
        
        return formatted_context
    
    def build_context_query(self, jurisdiction: str, transaction_types: List[str]) -> str:
        """Build RAG query for this section. Override for custom queries."""
        section_name = self.get_section_name()
        return f"{section_name} transfer pricing requirements {jurisdiction}"
    
    @abstractmethod
    def get_template_variables(self, state: PolicyGenerationState) -> Dict:
        """Get section-specific template variables."""
        pass
    
    def generate_section(self, state: PolicyGenerationState) -> str:
        """Generate content for this section."""
        # Load template
        template = self.load_template()
        
        # Get template variables
        template_vars = self.get_template_variables(state)
        
        # Fill template
        filled_template = template.format(**template_vars)
        
        # Generate using LLM via RAG system
        generated_content = self.rag_system.generate_with_context(
            prompt=filled_template,
            context_query=None  # Context already included in prompt
        )
        
        return generated_content
    
    def __call__(self, state: PolicyGenerationState) -> PolicyGenerationState:
        """Execute node - makes the class callable for LangGraph."""
        section_name = self.get_section_name()
        
        try:
            print(f"Generating section: {section_name}")
            
            # Generate content
            content = self.generate_section(state)
            
            # Extract citations
            citations = self.extract_citations(content, state)
            
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
    
    def extract_citations(self, content: str, state: PolicyGenerationState) -> List[str]:
        """Extract citations from generated content."""
        citations = []
        if 'OECD' in content:
            citations.append("OECD Transfer Pricing Guidelines")
        if 'Rule 10' in content or 'CBDT' in content:
            citations.append(f"{state['company'].jurisdiction} Transfer Pricing Regulations")
        return citations


class ExecutiveSummaryNode(BaseSectionNode):
    """Node for generating Executive Summary section."""
    
    def get_section_name(self) -> str:
        return "executive_summary"
    
    def build_context_query(self, jurisdiction: str, transaction_types: List[str]) -> str:
        return f"executive summary requirements for transfer pricing documentation in {jurisdiction}"
    
    def get_template_variables(self, state: PolicyGenerationState) -> Dict:
        transaction_types = list(set([txn.transaction_type for txn in state['transactions']]))
        related_jurisdictions = list(set([txn.related_party_jurisdiction for txn in state['transactions']]))
        regulatory_context = self.retrieve_context(state['company'].jurisdiction, transaction_types)
        
        return {
            'regulatory_context': regulatory_context,
            'company_name': state['company'].name,
            'jurisdiction': state['company'].jurisdiction,
            'tax_id': state['company'].tax_id,
            'entity_type': state['company'].entity_type,
            'industry': state['company'].industry or 'Not specified',
            'fiscal_year': state['fiscal_year'],
            'transactions_detail': self.format_transactions(state['transactions']),
            'transaction_summary': f"{len(state['transactions'])} transactions with entities in {', '.join(related_jurisdictions)}",
            'related_jurisdictions': ', '.join(related_jurisdictions)
        }


class RelatedPartiesNode(BaseSectionNode):
    """Node for generating Related Parties section."""
    
    def get_section_name(self) -> str:
        return "related_parties"
    
    def build_context_query(self, jurisdiction: str, transaction_types: List[str]) -> str:
        return f"related party definition and identification requirements in {jurisdiction}"
    
    def get_template_variables(self, state: PolicyGenerationState) -> Dict:
        transaction_types = list(set([txn.transaction_type for txn in state['transactions']]))
        related_jurisdictions = list(set([txn.related_party_jurisdiction for txn in state['transactions']]))
        regulatory_context = self.retrieve_context(state['company'].jurisdiction, transaction_types)
        
        return {
            'regulatory_context': regulatory_context,
            'company_name': state['company'].name,
            'jurisdiction': state['company'].jurisdiction,
            'tax_id': state['company'].tax_id,
            'entity_type': state['company'].entity_type,
            'industry': state['company'].industry or 'Not specified',
            'fiscal_year': state['fiscal_year'],
            'transactions_detail': self.format_transactions(state['transactions']),
            'transaction_summary': f"{len(state['transactions'])} transactions with entities in {', '.join(related_jurisdictions)}",
            'related_jurisdictions': ', '.join(related_jurisdictions)
        }


class FunctionalAnalysisNode(BaseSectionNode):
    """Node for generating Functional Analysis section."""
    
    def get_section_name(self) -> str:
        return "functional_analysis"
    
    def build_context_query(self, jurisdiction: str, transaction_types: List[str]) -> str:
        return f"functional analysis FAR framework and requirements for {', '.join(transaction_types)} in {jurisdiction}"
    
    def get_template_variables(self, state: PolicyGenerationState) -> Dict:
        transaction_types = list(set([txn.transaction_type for txn in state['transactions']]))
        related_jurisdictions = list(set([txn.related_party_jurisdiction for txn in state['transactions']]))
        regulatory_context = self.retrieve_context(state['company'].jurisdiction, transaction_types)
        
        return {
            'regulatory_context': regulatory_context,
            'company_name': state['company'].name,
            'jurisdiction': state['company'].jurisdiction,
            'tax_id': state['company'].tax_id,
            'entity_type': state['company'].entity_type,
            'industry': state['company'].industry or 'Not specified',
            'fiscal_year': state['fiscal_year'],
            'transactions_detail': self.format_transactions(state['transactions']),
            'transaction_summary': f"{len(state['transactions'])} transactions with entities in {', '.join(related_jurisdictions)}",
            'related_jurisdictions': ', '.join(related_jurisdictions)
        }


class ComparabilityAnalysisNode(BaseSectionNode):
    """Node for generating Comparability Analysis section."""
    
    def get_section_name(self) -> str:
        return "comparability_analysis"
    
    def build_context_query(self, jurisdiction: str, transaction_types: List[str]) -> str:
        return f"comparability analysis five factors OECD guidelines {jurisdiction}"
    
    def get_template_variables(self, state: PolicyGenerationState) -> Dict:
        transaction_types = list(set([txn.transaction_type for txn in state['transactions']]))
        related_jurisdictions = list(set([txn.related_party_jurisdiction for txn in state['transactions']]))
        regulatory_context = self.retrieve_context(state['company'].jurisdiction, transaction_types)
        
        # Get functional analysis from previous section
        functional_analysis_summary = state['sections'].get('functional_analysis', {}).get('content', 'See functional analysis section')
        
        return {
            'regulatory_context': regulatory_context,
            'company_name': state['company'].name,
            'jurisdiction': state['company'].jurisdiction,
            'tax_id': state['company'].tax_id,
            'entity_type': state['company'].entity_type,
            'industry': state['company'].industry or 'Not specified',
            'fiscal_year': state['fiscal_year'],
            'transactions_detail': self.format_transactions(state['transactions']),
            'transaction_summary': f"{len(state['transactions'])} transactions with entities in {', '.join(related_jurisdictions)}",
            'related_jurisdictions': ', '.join(related_jurisdictions),
            'functional_analysis_summary': functional_analysis_summary,
            'selected_method': 'TNMM'  # Default, could be determined dynamically
        }


class TPMethodNode(BaseSectionNode):
    """Node for generating TP Method Selection section."""
    
    def get_section_name(self) -> str:
        return "tp_method"
    
    def build_context_query(self, jurisdiction: str, transaction_types: List[str]) -> str:
        return f"transfer pricing methods selection TNMM cost plus for {', '.join(transaction_types)} {jurisdiction}"
    
    def get_template_variables(self, state: PolicyGenerationState) -> Dict:
        transaction_types = list(set([txn.transaction_type for txn in state['transactions']]))
        related_jurisdictions = list(set([txn.related_party_jurisdiction for txn in state['transactions']]))
        regulatory_context = self.retrieve_context(state['company'].jurisdiction, transaction_types)
        
        # Get functional analysis from previous section
        functional_analysis_summary = state['sections'].get('functional_analysis', {}).get('content', 'See functional analysis section')
        
        return {
            'regulatory_context': regulatory_context,
            'company_name': state['company'].name,
            'jurisdiction': state['company'].jurisdiction,
            'tax_id': state['company'].tax_id,
            'entity_type': state['company'].entity_type,
            'industry': state['company'].industry or 'Not specified',
            'fiscal_year': state['fiscal_year'],
            'transactions_detail': self.format_transactions(state['transactions']),
            'transaction_summary': f"{len(state['transactions'])} transactions with entities in {', '.join(related_jurisdictions)}",
            'related_jurisdictions': ', '.join(related_jurisdictions),
            'functional_analysis_summary': functional_analysis_summary,
            'selected_method': 'TNMM'  # Default, could be determined dynamically
        }


class BenchmarkingNode(BaseSectionNode):
    """Node for generating Benchmarking section."""
    
    def get_section_name(self) -> str:
        return "benchmarking"
    
    def build_context_query(self, jurisdiction: str, transaction_types: List[str]) -> str:
        return f"arm's length range benchmarking safe harbour provisions {jurisdiction} IT services margins"
    
    def get_template_variables(self, state: PolicyGenerationState) -> Dict:
        transaction_types = list(set([txn.transaction_type for txn in state['transactions']]))
        related_jurisdictions = list(set([txn.related_party_jurisdiction for txn in state['transactions']]))
        regulatory_context = self.retrieve_context(state['company'].jurisdiction, transaction_types)
        
        return {
            'regulatory_context': regulatory_context,
            'company_name': state['company'].name,
            'jurisdiction': state['company'].jurisdiction,
            'tax_id': state['company'].tax_id,
            'entity_type': state['company'].entity_type,
            'industry': state['company'].industry or 'Not specified',
            'fiscal_year': state['fiscal_year'],
            'transactions_detail': self.format_transactions(state['transactions']),
            'transaction_summary': f"{len(state['transactions'])} transactions with entities in {', '.join(related_jurisdictions)}",
            'related_jurisdictions': ', '.join(related_jurisdictions),
            'selected_method': 'TNMM',
            'tested_party': state['company'].name,
            'pli': 'Operating Margin on Operating Costs'
        }


class DocumentationRequirementsNode(BaseSectionNode):
    """Node for generating Documentation Requirements section."""
    
    def get_section_name(self) -> str:
        return "documentation_requirements"
    
    def build_context_query(self, jurisdiction: str, transaction_types: List[str]) -> str:
        return f"transfer pricing documentation filing deadlines master file local file CbCR {jurisdiction}"
    
    def get_template_variables(self, state: PolicyGenerationState) -> Dict:
        transaction_types = list(set([txn.transaction_type for txn in state['transactions']]))
        related_jurisdictions = list(set([txn.related_party_jurisdiction for txn in state['transactions']]))
        regulatory_context = self.retrieve_context(state['company'].jurisdiction, transaction_types)
        
        return {
            'regulatory_context': regulatory_context,
            'company_name': state['company'].name,
            'jurisdiction': state['company'].jurisdiction,
            'tax_id': state['company'].tax_id,
            'entity_type': state['company'].entity_type,
            'industry': state['company'].industry or 'Not specified',
            'fiscal_year': state['fiscal_year'],
            'transactions_detail': self.format_transactions(state['transactions']),
            'transaction_summary': f"{len(state['transactions'])} transactions with entities in {', '.join(related_jurisdictions)}",
            'related_jurisdictions': ', '.join(related_jurisdictions)
        }


# Factory function to create node instances
def create_section_nodes(rag_system: RAGSystem, prompts_dir: Path) -> Dict[str, BaseSectionNode]:
    """
    Create all 7 section node instances.
    
    Returns:
        Dictionary mapping section names to node instances
    """
    return {
        'executive_summary': ExecutiveSummaryNode(rag_system, prompts_dir),
        'related_parties': RelatedPartiesNode(rag_system, prompts_dir),
        'functional_analysis': FunctionalAnalysisNode(rag_system, prompts_dir),
        'comparability_analysis': ComparabilityAnalysisNode(rag_system, prompts_dir),
        'tp_method': TPMethodNode(rag_system, prompts_dir),
        'benchmarking': BenchmarkingNode(rag_system, prompts_dir),
        'documentation_requirements': DocumentationRequirementsNode(rag_system, prompts_dir)
    }
