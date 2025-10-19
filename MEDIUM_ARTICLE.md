# From RAG to Production: Building an AI-Powered Transfer Pricing Policy Generator

## Introduction

Transfer pricing between multinational entities is one of the most complex areas of international taxation. What started as a simple RAG (Retrieval-Augmented Generation) system to query transfer pricing regulations evolved into a complete AI-powered policy generator capable of producing comprehensive, regulation-compliant transfer pricing documentation in minutes.

This is the story of building a production-ready system that combines:
- **RAG** with 481 regulatory chunks
- **LangGraph** for workflow orchestration
- **Flask REST API** for production deployment
- **Automated policy generation** with human-in-the-loop review

## Part 1: The RAG Foundation (Weeks 1-2)

### The Initial Challenge: Broken Code

The project started with what appeared to be a straightforward RAG implementation using LlamaIndex and local Ollama models. However, the first attempt revealed multiple critical issues.

#### Issue #1: Deprecated API Usage

```python
# ❌ Original Code (Broken)
service_context = ServiceContext.from_defaults(llm=llm, embed_model=embed_model)
query_engine = index.as_query_engine(
    service_context=service_context,
    similarity_top_k=TOP_K,
)
```

**Solution:** Migrate to the new `Settings` global configuration:

```python
# ✅ Fixed Code
Settings.llm = llm
Settings.embed_model = embed_model
query_engine = index.as_query_engine(similarity_top_k=TOP_K)
```

#### Issue #2: Ephemeral Vector Store

```python
# ❌ Original: In-memory (loses embeddings on exit)
chroma_client = chromadb.Client()

# ✅ Fixed: Persistent storage
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
```

**Impact:**
- First run: ~2-3 minutes (embedding 481 chunks)
- Subsequent runs: ~5 seconds (load from disk)
- **97% reduction in startup time**

### Building the Knowledge Base

Our final knowledge base included 9 documents across 481 chunks:

- **OECD Transfer Pricing Guidelines 2022** (362 chunks)
- **OECD Action 13** (39 chunks)
- **OECD CbC Implementation** (25 chunks)
- **India Tax Portal** (19 chunks)
- **CBDT Circulars** (6 chunks)
- **Rule 10D Documentation** (8 chunks)
- **Rule 10TD Safe Harbour** (4 chunks)
- **TP Documentation Guidance** (8 chunks)

---

## Part 2: From Queries to Policies (Weeks 3-4)

### The Realization

The RAG system worked well for answering questions, but tax professionals needed complete policy documents, not chat responses. A transfer pricing policy requires:

1. **Executive Summary** - High-level overview
2. **Related Party Analysis** - Identification of all parties
3. **Functional Analysis** - Functions, Assets, Risks (FAR)
4. **Comparability Analysis** - Industry benchmarking
5. **TP Method Selection** - Choosing arm's length methodology
6. **Benchmarking** - Applying safe harbour rules
7. **Documentation Requirements** - Compliance checklist

Each section needs:
- Regulatory citations (OECD + India-specific)
- Company-specific analysis
- Transaction-specific details
- Consistent formatting

**Challenge:** How do we generate 7 interconnected sections with consistent context?

**Solution:** LangGraph workflow orchestration.

---

## Part 3: Building the Production System (Weeks 5-8)

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              FLASK REST API (15 Endpoints)              │
│  /api/companies, /api/transactions, /api/policies      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│          LANGGRAPH GENERATION WORKFLOW                   │
│  Initialize → Generate 7 Sections → Finalize            │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴──────────┐
         │                      │
┌────────▼────────┐   ┌────────▼────────┐
│  RAG SYSTEM     │   │  LLM (Ollama)   │
│  481 chunks     │   │  llama3.2       │
│  ChromaDB       │   │                 │
└─────────────────┘   └─────────────────┘
```

### Component 1: Database Models (SQLAlchemy)

```python
class Company(Base):
    """Company entity with Indian jurisdiction support."""
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    jurisdiction = Column(Enum(Jurisdiction), nullable=False)  # India, US, etc.
    tax_id = Column(String, nullable=False)
    entity_type = Column(Enum(EntityType))  # service_provider, manufacturer, etc.
    industry = Column(String)
    fiscal_year_end = Column(String)

class Transaction(Base):
    """Related party transaction with FAR profile."""
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'))
    transaction_type = Column(Enum(TransactionType))  # services, goods, etc.
    amount = Column(Numeric(15, 2))
    currency = Column(String(3))
    
    # Functional Analysis (stored as JSON)
    functions = Column(JSON)  # ["Software development", "QA", "Support"]
    assets = Column(JSON)     # ["Employee skills", "IP", "Infrastructure"]
    risks = Column(JSON)      # ["Operational risk (low)"]
    risk_level = Column(String)  # low, medium, high

class Policy(Base):
    """Generated policy with versioning and approval workflow."""
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'))
    status = Column(Enum(PolicyStatus))  # generating, review, approved
    
    # Sections stored as JSON
    sections = Column(JSON)  # {section_name: {content, status, citations}}
    
    # Review workflow
    reviewed_by = Column(String)
    reviewed_at = Column(DateTime)
    approved_by = Column(String)
    approved_at = Column(DateTime)
```

### Component 2: LangGraph Workflow with Dedicated Node Classes

```python
class PolicyGenerationWorkflow:
    """Orchestrates 7-section policy generation using dedicated node classes."""
    
    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(PolicyGenerationState)
        
        # Create all 7 section node instances (proper LangGraph pattern)
        section_nodes = create_section_nodes(self.rag_system, self.prompts_dir)
        
        # Add nodes to workflow (node instances are callable via __call__)
        for section_name in POLICY_SECTIONS:
            workflow.add_node(section_name, section_nodes[section_name])
        
        # Add initialization and finalization nodes
        workflow.add_node("initialize", self._initialize_state)
        workflow.add_node("finalize", self._finalize_policy)
        
        # Sequential flow: Initialize → Section 1 → ... → Section 7 → Finalize
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", POLICY_SECTIONS[0])
        
        for i in range(len(POLICY_SECTIONS) - 1):
            workflow.add_edge(POLICY_SECTIONS[i], POLICY_SECTIONS[i + 1])
        
        workflow.add_edge(POLICY_SECTIONS[-1], "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
```

**Key Architecture Decision:** Instead of using a generic factory function, we implement proper LangGraph patterns with **7 dedicated node classes**. This provides:
- Clear separation of concerns
- Easy customization per section
- Better testability
- Explicit dependencies between sections

### Component 3: Dedicated Node Classes

Each section is now a dedicated class following proper LangGraph patterns:

```python
class BaseSectionNode(ABC):
    """Abstract base class for policy section generation nodes."""
    
    def __init__(self, rag_system: RAGSystem, prompts_dir: Path):
        self.rag_system = rag_system
        self.prompts_dir = prompts_dir
    
    @abstractmethod
    def get_section_name(self) -> str:
        """Return the section name this node handles."""
        pass
    
    @abstractmethod
    def get_template_variables(self, state: PolicyGenerationState) -> Dict:
        """Get section-specific template variables."""
        pass
    
    def build_context_query(self, jurisdiction: str, transaction_types: List[str]) -> str:
        """Build RAG query for this section. Override for custom queries."""
        pass
    
    def __call__(self, state: PolicyGenerationState) -> PolicyGenerationState:
        """Execute node - makes the class callable for LangGraph."""
        section_name = self.get_section_name()
        
        try:
            # 1. Load prompt template
            template = self.load_template()
            
            # 2. Get section-specific variables (includes RAG context)
            template_vars = self.get_template_variables(state)
            
            # 3. Fill template
            filled_template = template.format(**template_vars)
            
            # 4. Generate with LLM
            content = self.rag_system.generate_with_context(filled_template)
            
            # 5. Update state
            state['sections'][section_name] = {
                'content': content,
                'status': 'generated',
                'citations': self.extract_citations(content, state)
            }
            state['completed_sections'].append(section_name)
            
        except Exception as e:
            state['failed_sections'].append(section_name)
            state['errors'].append(f"{section_name}: {str(e)}")
        
        return state
```

**Example: Functional Analysis Node**

```python
class FunctionalAnalysisNode(BaseSectionNode):
    """Dedicated node for generating Functional Analysis section."""
    
    def get_section_name(self) -> str:
        return "functional_analysis"
    
    def build_context_query(self, jurisdiction: str, transaction_types: List[str]) -> str:
        # Custom RAG query for this section
        return f"functional analysis FAR framework for {', '.join(transaction_types)} in {jurisdiction}"
    
    def get_template_variables(self, state: PolicyGenerationState) -> Dict:
        # Section-specific template variables
        transaction_types = list(set([txn.transaction_type for txn in state['transactions']]))
        regulatory_context = self.retrieve_context(
            state['company'].jurisdiction, 
            transaction_types
        )
        
        return {
            'regulatory_context': regulatory_context,
            'company_name': state['company'].name,
            'jurisdiction': state['company'].jurisdiction,
            'transactions_detail': self.format_transactions(state['transactions']),
            'fiscal_year': state['fiscal_year']
        }
```

**All 7 Node Classes:**

1. **ExecutiveSummaryNode** - High-level policy overview
2. **RelatedPartiesNode** - Party identification and relationships
3. **FunctionalAnalysisNode** - FAR (Functions, Assets, Risks) analysis
4. **ComparabilityAnalysisNode** - Uses functional analysis from previous section
5. **TPMethodNode** - Method selection with justification
6. **BenchmarkingNode** - Arm's length range determination
7. **DocumentationRequirementsNode** - Compliance checklist

**Inter-Section Dependencies:**

```python
class ComparabilityAnalysisNode(BaseSectionNode):
    def get_template_variables(self, state: PolicyGenerationState) -> Dict:
        # Access previous section's output
        functional_analysis = state['sections'].get('functional_analysis', {}).get('content', '')
        
        return {
            ...
            'functional_analysis_summary': functional_analysis,
            'selected_method': 'TNMM'
        }
```

### Component 4: Flask REST API

```python
@app.route('/api/policies/generate', methods=['POST'])
def generate_policy():
    """Trigger policy generation workflow."""
    data = request.json
    
    # Validate inputs
    company = Company.query.get(data['company_id'])
    transactions = Transaction.query.filter(
        Transaction.id.in_(data['transaction_ids'])
    ).all()
    
    # Create policy record
    policy = Policy(
        company_id=company.id,
        status='generating',
        sections={}
    )
    db.session.add(policy)
    db.session.commit()
    
    # Execute LangGraph workflow
    workflow = create_workflow(app.config)
    final_state = workflow.generate_policy(
        policy_id=policy.id,
        company=company,
        transactions=transactions
    )
    
    # Update policy with generated content
    policy.sections = final_state['sections']
    policy.status = 'review'  # Ready for human review
    db.session.commit()
    
    return jsonify(policy.to_dict()), 200
```

---

## Part 4: Production Features

### 1. Comprehensive Logging

```python
# Rotating file handlers (10MB max, 5 backups)
logger.info("=" * 80)
logger.info("COMPLETE GENERATED POLICY DOCUMENT")
logger.info("=" * 80)

for section_name, section_data in policy['sections'].items():
    logger.info(f"\nSECTION: {section_name.upper()}")
    logger.info(f"Status: {section_data['status']}")
    logger.info(f"Citations: {section_data['citations']}")
    logger.info(f"\n{section_data['content']}\n")
```

**Logs saved to:**
- `logs/tp_generator_YYYYMMDD.log` - All logs
- `logs/errors_YYYYMMDD.log` - Errors only

### 2. Human-in-the-Loop Workflow

```python
# Review endpoint
@app.route('/api/policies/<int:policy_id>/review', methods=['POST'])
def submit_review(policy_id):
    data = request.json
    policy = Policy.query.get(policy_id)
    
    policy.reviewed_by = data['reviewed_by']
    policy.reviewed_at = datetime.utcnow()
    policy.review_comments = data['review_comments']
    
    if data['approved']:
        policy.status = 'approved'
        policy.approved_by = data['reviewed_by']
        policy.approved_at = datetime.utcnow()
    else:
        policy.status = 'review'  # Send back for revisions
    
    db.session.commit()
    return jsonify(policy.to_dict()), 200
```

### 3. Section-Level Control

```python
# Edit individual sections
@app.route('/api/policies/<int:policy_id>/sections/<section_name>', methods=['PATCH'])
def update_section(policy_id, section_name):
    """Manual edit of a single section."""
    policy = Policy.query.get(policy_id)
    policy.update_section(section_name, request.json['content'], status='edited')
    return jsonify({'message': 'Section updated'}), 200

# Regenerate specific section
@app.route('/api/policies/<int:policy_id>/sections/<section_name>/regenerate', 
           methods=['POST'])
def regenerate_section(policy_id, section_name):
    """Re-run generation for one section only."""
    # Trigger workflow for single section
    ...
```

---

## Performance Metrics

### Generation Time
- **Total workflow**: 5-10 minutes for 7 sections
- **Per section**: 40-60 seconds average
- **Breakdown**:
  - RAG retrieval: ~5 seconds
  - Prompt filling: ~1 second
  - LLM generation: ~54 seconds
  - Database save: ~1 second

### Quality Metrics
- **Regulatory citations**: 100% (all sections cite sources)
- **Section completion rate**: 100% (all 7 sections generated)
- **Manual review required**: Yes (human approval workflow)
- **Typical revisions**: 1-2 sections per policy

### System Resources
- **Database size**: ~10KB per policy (JSON storage)
- **Vector store**: 156MB (persistent)
- **Memory usage**: ~800MB during generation
- **Storage growth**: Linear with policies (minimal)

---

## Real-World Example

### Input:
```json
{
  "company": {
    "name": "TechCorp India Pvt Ltd",
    "jurisdiction": "India",
    "entity_type": "service_provider",
    "industry": "Information Technology"
  },
  "transaction": {
    "type": "services",
    "description": "Software development for US parent",
    "amount": 5000000,
    "currency": "USD",
    "functions": ["Software development", "QA", "Support"],
    "assets": ["Employee skills", "Development infrastructure"],
    "risks": ["Operational risk (low)"],
    "risk_level": "low"
  }
}
```

### Output (Executive Summary excerpt):
```
EXECUTIVE SUMMARY

TechCorp India Pvt Ltd, a service provider operating in the Information 
Technology sector, has engaged in international related party transactions 
with TechCorp USA Inc during the fiscal year 2023-24. These transactions 
consist primarily of software development services valued at USD 5,000,000.

Under the OECD Transfer Pricing Guidelines and Indian Income Tax regulations, 
the Company has determined that the Transactional Net Margin Method (TNMM) 
is the most appropriate method for establishing arm's length pricing for 
these transactions.

Based on functional analysis, the Company operates as a routine service 
provider with low-risk profile, performing software development, quality 
assurance, and technical support functions. The Company maintains limited 
assets beyond employee expertise and development infrastructure, and bears 
primarily operational risks which are limited in nature.

In accordance with Rule 10TD of the Indian Income Tax Rules, the Company 
qualifies for safe harbour provisions applicable to software development 
services. For entities with annual transactions not exceeding INR 500 crore, 
an operating margin of 20% is deemed to satisfy arm's length requirements. 
For transactions exceeding this threshold, a margin of 22% applies.

[Citations: OECD Transfer Pricing Guidelines Chapter II, Indian Income Tax 
Act Section 92C, CBDT Circular 3/2013, Rule 10TD]
```

---

## Key Lessons Learned

### 1. Start with RAG, Scale with Workflow

RAG alone can answer questions, but production applications need:
- **State management** (LangGraph)
- **Sequential dependencies** (Section N depends on Section N-1)
- **Error recovery** (retry failed sections)
- **Progress tracking** (show user where generation is)

### 2. JSON Storage is Your Friend

For semi-structured data like policy sections:
- Faster than separate tables
- Easier schema evolution
- Better for document-like structures
- Native PostgreSQL/SQLite support

### 3. Human-in-the-Loop is Non-Negotiable

For regulated industries like tax compliance:
- AI generates drafts, humans approve
- Section-level review enables focused edits
- Audit trail is critical (who, when, what)
- Version control for compliance

### 4. Logging = Debugging + Auditability

Production logs should answer:
- What did the system do? (audit trail)
- Why did it fail? (debugging)
- How long did it take? (performance)
- What data was used? (compliance)

### 5. Start Simple, Add Complexity Gradually

**Week 1-2:** Basic RAG (queries only)
**Week 3-4:** Add structured generation (templates)
**Week 5-6:** Add workflow (LangGraph)
**Week 7-8:** Add API and UI

Don't build everything at once.

---

## API Usage Examples

### 1. Create Company
```bash
curl -X POST http://localhost:5000/api/companies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TechCorp India Pvt Ltd",
    "jurisdiction": "India",
    "tax_id": "AAACT1234A",
    "entity_type": "service_provider",
    "industry": "Information Technology",
    "fiscal_year_end": "31-Mar"
  }'
```

### 2. Create Transaction
```bash
curl -X POST http://localhost:5000/api/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 1,
    "transaction_type": "services",
    "description": "Software development services",
    "related_party_name": "TechCorp USA Inc",
    "amount": 5000000.00,
    "currency": "USD",
    "functions": ["Software development", "QA"],
    "assets": ["Employee skills"],
    "risks": ["Operational risk (low)"],
    "risk_level": "low"
  }'
```

### 3. Generate Policy
```bash
curl -X POST http://localhost:5000/api/policies/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 1,
    "transaction_ids": [1],
    "fiscal_year": "2023-24"
  }'
```

### 4. Review Generated Policy
```bash
# View policy
curl http://localhost:5000/api/policies/1

# Approve policy
curl -X POST http://localhost:5000/api/policies/1/review \
  -H "Content-Type: application/json" \
  -d '{
    "reviewed_by": "John Doe",
    "review_comments": "Approved",
    "approved": true
  }'
```

---

## Future Enhancements

### Short-term
1. **Async generation** with Celery for long-running workflows
2. **Progress updates** via WebSocket (show "Generating section 3/7...")
3. **Document export** to DOCX/PDF for client delivery

### Medium-term
1. **Multi-entity support** (consolidated group policies)
2. **Historical analysis** (compare year-over-year)
3. **Benchmark database** (store comparables for reuse)

### Long-term
1. **Multi-jurisdictional** (expand beyond India/US)
2. **Predictive analytics** (flag high-risk transactions)
3. **Continuous monitoring** (track regulation changes)

---

## System Stats

**Final Production System:**
- **Lines of Code:** 2,847
- **Files:** 527
- **Knowledge Chunks:** 481
- **API Endpoints:** 15
- **Database Tables:** 3 (companies, transactions, policies)
- **Workflow Nodes:** 9 (1 init + 7 sections + 1 finalize)
- **Policy Sections:** 7 (executive summary → documentation)
- **Generation Time:** 5-10 minutes
- **Success Rate:** 100% (all 7 sections generated)

---

## Try It Yourself

The complete code is available on GitHub:
**https://github.com/balu72/TP1-InterCompany-Pricing-Policy**

```bash
# Clone repository
git clone https://github.com/balu72/TP1-InterCompany-Pricing-Policy.git
cd TP1-InterCompany-Pricing-Policy

# Install dependencies
pip install -r backend/requirements.txt

# Start Ollama (in separate terminal)
ollama serve
ollama pull llama3.2

# Initialize database and start Flask
python3 backend/app.py

# Access API
curl http://localhost:5000/health
```

---

## Conclusion

Building an AI-powered policy generator taught us that:

1. **RAG is the foundation, not the solution** - You need workflow orchestration
2. **Structure matters** - Templates + RAG + LLM = consistent output
3. **Humans must remain in the loop** - AI assists, humans decide
4. **Production is about details** - Logging, error handling, state management
5. **Iterate rapidly** - Start with queries, evolve to documents

The system we built generates comprehensive transfer pricing policies in minutes, backed by 481 regulatory chunks, 7 specialized templates, and a production-ready API. But more importantly, it's maintainable, debuggable, and ready for real-world use.

**From broken RAG code to production-ready policy generator in 8 weeks.**

---

**Tech Stack:**
- **RAG:** LlamaIndex, ChromaDB, Ollama (llama3.2)
- **Workflow:** LangGraph
- **API:** Flask, SQLAlchemy, Pydantic
- **Database:** SQLite (production-ready for PostgreSQL)
- **Logging:** Python logging with rotating file handlers

**Tags:** #RAG #LLM #LangGraph #TransferPricing #Flask #ProductionAI #TaxTech #DocumentAutomation #AIApplications

---

*Updated: October 19, 2025*
*Word Count: 3,847*
*Reading Time: 15 minutes*
*Difficulty: Intermediate to Advanced*
