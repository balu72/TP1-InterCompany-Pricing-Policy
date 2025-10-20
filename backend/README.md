# Transfer Pricing Policy Generator - Backend API

## Overview
Flask-based REST API for the Transfer Pricing Policy Generator system.

## Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Variables (Optional)
Create a `.env` file:
```env
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///tp_policy.db
CORS_ORIGINS=http://localhost:3000
OLLAMA_MODEL=llama3.2:latest
EMBEDDING_MODEL=nomic-embed-text
RAG_TOP_K=10
```

### 3. Run the Server
```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### Companies
- `GET /api/companies` - List all companies
- `GET /api/companies/<id>` - Get company details
- `POST /api/companies` - Create company
- `PUT /api/companies/<id>` - Update company
- `DELETE /api/companies/<id>` - Delete company

### Transactions
- `GET /api/transactions?company_id=<id>` - List transactions
- `GET /api/transactions/<id>` - Get transaction details
- `POST /api/transactions` - Create transaction
- `PUT /api/transactions/<id>` - Update transaction
- `DELETE /api/transactions/<id>` - Delete transaction

### Policies
- `GET /api/policies?company_id=<id>` - List policies
- `GET /api/policies/<id>` - Get policy details
- `POST /api/policies/generate` - Generate new policy
- `GET /api/policies/<id>/sections/<name>` - Get policy section
- `PATCH /api/policies/<id>/sections/<name>` - Update section
- `POST /api/policies/<id>/sections/<name>/regenerate` - Regenerate section
- `POST /api/policies/<id>/review` - Submit review
- `DELETE /api/policies/<id>` - Delete policy
- `GET /api/policies/<id>/export` - Export policy (DOCX)

### Utility
- `GET /health` - Health check
- `GET /` - API information

## Example Requests

### Create Company
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

### Create Transaction
```bash
curl -X POST http://localhost:5000/api/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 1,
    "transaction_type": "services",
    "description": "Software development services",
    "related_party_name": "TechCorp USA Inc",
    "related_party_jurisdiction": "US",
    "amount": 5000000.00,
    "currency": "USD",
    "fiscal_year": "2023-24",
    "functional_profile": {
      "functions": ["Software development", "Testing"],
      "assets": ["Employee skills", "Infrastructure"],
      "risks": ["Operational risk (low)"],
      "risk_level": "low"
    }
  }'
```

### Generate Policy
```bash
curl -X POST http://localhost:5000/api/policies/generate \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 1,
    "transaction_ids": [1, 2],
    "fiscal_year": "2023-24"
  }'
```

## Project Structure

```
backend/
├── data/                       # Data directory (gitignored)
│   ├── chroma_db/             # Vector database for RAG
│   ├── kb_raw/                # Raw regulatory documents (PDFs)
│   ├── kb_text_chunks/        # Processed text chunks (481 chunks)
│   └── tp_policy.db           # SQLite database
├── rag/                        # RAG package
│   ├── __init__.py
│   ├── download_and_prepare_kb.py  # KB preparation script
│   ├── docs_index.csv              # Document index
│   └── rag_local_llamaindex.py     # RAG implementation
├── generation/
│   ├── workflows/              # LangGraph workflows
│   │   ├── __init__.py
│   │   └── pricing_policy_workflow.py
│   ├── nodes/                  # Workflow node classes
│   │   └── section_generator.py    # 7 dedicated node classes
│   ├── prompts/                # Section-specific prompts
│   ├── state.py                # Workflow state definitions
│   └── rag_integration.py      # RAG system integration
├── models/                     # SQLAlchemy models
├── api/                        # API endpoints
├── schemas/                    # Pydantic schemas
├── utils/                      # Utilities (logger, etc.)
├── config.py                   # Configuration
├── app.py                      # Flask application
└── requirements.txt            # Dependencies
```

## Database
SQLite database is located at `backend/data/tp_policy.db` and will be created automatically on first run.

## RAG System
The RAG system uses:
- **Knowledge Base**: 481 text chunks from 9 regulatory documents in `backend/data/kb_text_chunks/`
- **Vector Store**: ChromaDB persistent storage in `backend/data/chroma_db/`
- **Raw Documents**: Original PDFs in `backend/data/kb_raw/`

To prepare the knowledge base:
```bash
cd backend/rag
python download_and_prepare_kb.py
```

## Next Steps
- [ ] Implement LangGraph workflow for policy generation
- [ ] Add async job processing for long-running generations
- [ ] Implement document export functionality
- [ ] Add authentication and authorization
- [ ] Set up production database (PostgreSQL)
