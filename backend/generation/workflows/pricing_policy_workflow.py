"""LangGraph workflow for policy generation."""
from pathlib import Path
from typing import List
from langgraph.graph import StateGraph, END
from generation.state import PolicyGenerationState, POLICY_SECTIONS, CompanyData, TransactionData
from generation.rag_integration import RAGSystem, create_rag_system
from generation.nodes.section_generator import create_section_nodes
from utils.logger import get_logger

logger = get_logger(__name__)

class PolicyGenerationWorkflow:
    """Main workflow for generating transfer pricing policies."""
    
    def __init__(self, config):
        """Initialize workflow with config."""
        self.config = config
        self.rag_system = create_rag_system(config)
        self.prompts_dir = Path(__file__).parent.parent / 'prompts'
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create state graph
        workflow = StateGraph(PolicyGenerationState)
        
        # Create all 7 section node instances
        section_nodes = create_section_nodes(self.rag_system, self.prompts_dir)
        
        # Add nodes to workflow (node instances are callable)
        for section_name in POLICY_SECTIONS:
            workflow.add_node(section_name, section_nodes[section_name])
        
        # Add initialization node
        workflow.add_node("initialize", self._initialize_state)
        
        # Add finalization node
        workflow.add_node("finalize", self._finalize_policy)
        
        # Set entry point
        workflow.set_entry_point("initialize")
        
        # Add edges (sequential flow through sections)
        workflow.add_edge("initialize", POLICY_SECTIONS[0])
        
        for i in range(len(POLICY_SECTIONS) - 1):
            workflow.add_edge(POLICY_SECTIONS[i], POLICY_SECTIONS[i + 1])
        
        # Last section goes to finalize
        workflow.add_edge(POLICY_SECTIONS[-1], "finalize")
        
        # Finalize goes to END
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _initialize_state(self, state: PolicyGenerationState) -> PolicyGenerationState:
        """Initialize the state for generation."""
        logger.info("=" * 70)
        logger.info("INITIALIZING POLICY GENERATION WORKFLOW")
        logger.info("=" * 70)
        logger.info(f"Policy ID: {state['policy_id']}")
        logger.info(f"Company: {state['company'].name} ({state['company'].jurisdiction})")
        logger.info(f"Transactions: {len(state['transactions'])}")
        logger.info(f"Fiscal Year: {state['fiscal_year']}")
        
        # Initialize tracking fields
        state['completed_sections'] = []
        state['failed_sections'] = []
        state['sections'] = {}
        state['generation_log'] = []
        state['errors'] = []
        state['retrieved_context'] = {}
        
        # Log initialization
        from datetime import datetime
        state['generation_log'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'initialization',
            'status': 'started',
            'policy_id': state['policy_id']
        })
        
        logger.info(f"Workflow initialized successfully for {state['company'].name}")
        logger.info("Starting section-by-section generation...")
        
        return state
    
    def _finalize_policy(self, state: PolicyGenerationState) -> PolicyGenerationState:
        """Finalize the policy generation."""
        logger.info("=" * 70)
        logger.info("FINALIZING POLICY GENERATION")
        logger.info("=" * 70)
        
        from datetime import datetime
        
        # Check if all sections completed
        if len(state['completed_sections']) == len(POLICY_SECTIONS):
            status = 'completed'
            logger.info(f"✓ SUCCESS: All {len(POLICY_SECTIONS)} sections generated successfully")
        else:
            status = 'partial'
            logger.warning(f"⚠ PARTIAL: Generated {len(state['completed_sections'])}/{len(POLICY_SECTIONS)} sections")
            logger.warning(f"Failed sections: {state['failed_sections']}")
            if state['errors']:
                logger.error(f"Errors encountered: {state['errors']}")
        
        # Log finalization
        state['generation_log'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'finalization',
            'status': status,
            'completed_sections': len(state['completed_sections']),
            'failed_sections': len(state['failed_sections']),
            'errors': state['errors']
        })
        
        logger.info(f"Policy {state['policy_id']} generation workflow completed with status: {status}")
        
        return state
    
    def generate_policy(self, policy_id: int, company: CompanyData, 
                       transactions: List[TransactionData], fiscal_year: str) -> PolicyGenerationState:
        """
        Execute the workflow to generate a policy.
        
        Args:
            policy_id: Database ID of the policy
            company: Company information
            transactions: List of transactions
            fiscal_year: Fiscal year for the policy
            
        Returns:
            Final state with generated sections
        """
        # Create initial state
        initial_state: PolicyGenerationState = {
            'policy_id': policy_id,
            'company': company,
            'transactions': transactions,
            'fiscal_year': fiscal_year,
            'current_section': '',
            'completed_sections': [],
            'failed_sections': [],
            'sections': {},
            'retrieved_context': {},
            'generation_log': [],
            'errors': []
        }
        
        # Execute workflow
        print(f"\n{'='*60}")
        print(f"Starting Policy Generation Workflow")
        print(f"Policy ID: {policy_id}")
        print(f"Company: {company.name} ({company.jurisdiction})")
        print(f"Fiscal Year: {fiscal_year}")
        print(f"{'='*60}\n")
        
        final_state = self.workflow.invoke(initial_state)
        
        print(f"\n{'='*60}")
        print(f"Policy Generation Complete")
        print(f"Completed: {len(final_state['completed_sections'])}/{len(POLICY_SECTIONS)} sections")
        if final_state['failed_sections']:
            print(f"Failed: {final_state['failed_sections']}")
        print(f"{'='*60}\n")
        
        return final_state

def create_workflow(config) -> PolicyGenerationWorkflow:
    """Factory function to create workflow."""
    return PolicyGenerationWorkflow(config)
