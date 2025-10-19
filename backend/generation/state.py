"""State management for policy generation workflow."""
from typing import TypedDict, List, Dict, Optional
from dataclasses import dataclass

@dataclass
class CompanyData:
    """Company information for policy generation."""
    id: int
    name: str
    jurisdiction: str
    tax_id: str
    entity_type: str
    industry: Optional[str] = None
    fiscal_year_end: Optional[str] = None

@dataclass
class TransactionData:
    """Transaction information for policy generation."""
    id: int
    transaction_type: str
    description: str
    related_party_name: str
    related_party_jurisdiction: str
    amount: Optional[float] = None
    currency: str = "USD"
    functions: List[str] = None
    assets: List[str] = None
    risks: List[str] = None
    risk_level: str = "medium"

class PolicyGenerationState(TypedDict):
    """State for the policy generation workflow."""
    # Input data
    policy_id: int
    company: CompanyData
    transactions: List[TransactionData]
    fiscal_year: str
    
    # Retrieved context from RAG
    retrieved_context: Dict[str, List[str]]  # section_name -> list of relevant chunks
    
    # Generated sections
    sections: Dict[str, Dict[str, any]]  # section_name -> {content, status, citations}
    
    # Progress tracking
    current_section: str
    completed_sections: List[str]
    failed_sections: List[str]
    
    # Generation log
    generation_log: List[Dict[str, any]]
    
    # Error handling
    errors: List[str]

# Section names that will be generated
POLICY_SECTIONS = [
    "executive_summary",
    "related_parties",
    "functional_analysis",
    "comparability_analysis",
    "tp_method",
    "benchmarking",
    "documentation_requirements"
]
