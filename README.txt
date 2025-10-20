# Transfer Pricing Policy Generator

## Overview
AI-powered system for generating comprehensive Transfer Pricing policy documents using RAG (Retrieval-Augmented Generation) and LangGraph workflows.

## Project Structure

```
TP1-Intercompany-Price-Policy/
├── backend/
│   ├── data/                       # Data directory (runtime generated)
│   │   ├── chroma_db/             # Vector database for RAG
│   │   ├── kb_raw/                # Raw regulatory documents (PDFs)
│   │   ├── kb_text_chunks/        # Processed text chunks (481 chunks)
│   │   └── tp_policy.db           # SQLite database
│   ├── rag/                        # RAG package
│   │   ├── download_and_prepare_kb.py  # KB preparation script
│   │   ├── docs_index.csv              # Document index
│   │   └── rag_local_llamaindex.py     # RAG query system
│   ├── generation/                 # Policy generation system
│   │   ├── workflows/              # LangGraph workflows
│   │   ├── nodes/                  # 7 dedicated node classes
│   │   ├── prompts/                # Section templates
│   │   ├── state.py                # Workflow state
│   │   └── rag_integration.py      # RAG integration
│   ├── models/                     # Database models
│   ├── api/                        # REST API endpoints
│   ├── schemas/                    # Pydantic schemas
│   ├── utils/                      # Utilities
│   ├── app.py                      # Flask application
│   └── requirements.txt            # Dependencies
├── MEDIUM_ARTICLE.md               # Technical article
└── README.txt                      # This file
```

## Setup Instructions

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Prepare Knowledge Base
Download and process regulatory documents:
```bash
cd backend/rag
python download_and_prepare_kb.py
```

This will:
- Download 9 regulatory PDFs from OECD and India Tax Portal
- Extract and chunk text into 481 pieces
- Store in backend/data/kb_raw/ and backend/data/kb_text_chunks/

### 3. Initialize RAG System (Optional)
Test the RAG system interactively:
```bash
cd backend/rag
python rag_local_llamaindex.py
```

### 4. Start the API Server
```bash
cd backend
python app.py
```

Server will run on http://localhost:5000

## Features

- **RAG System**: 481 chunks from 9 regulatory documents (OECD + India)
- **LangGraph Workflow**: 7-section policy generation with dedicated node classes
- **REST API**: 15 endpoints for companies, transactions, and policies
- **Database**: SQLite with SQLAlchemy ORM
- **Logging**: Comprehensive logging with rotating file handlers

## Knowledge Base Documents

1. OECD Transfer Pricing Guidelines 2022 (362 chunks)
2. OECD Action 13 (39 chunks)
3. OECD CbC Implementation (25 chunks)
4. India Tax Portal (19 chunks)
5. CBDT Circular 03/2013 (6 chunks)
6. CBDT Circular 06/2017
7. Rule 10D Documentation (8 chunks)
8. Rule 10TD Safe Harbour (4 chunks)
9. TP Documentation Guidance India (8 chunks)

## Architecture

**RAG Pipeline:**
- LlamaIndex for document loading and indexing
- ChromaDB for persistent vector storage
- Ollama (llama3.2:latest) for LLM
- nomic-embed-text for embeddings

**Policy Generation:**
- LangGraph for workflow orchestration
- 7 dedicated node classes for sections:
  1. Executive Summary
  2. Related Parties
  3. Functional Analysis
  4. Comparability Analysis
  5. TP Method Selection
  6. Benchmarking
  7. Documentation Requirements

**Database:**
- SQLAlchemy ORM
- 3 main models: Company, Transaction, Policy
- JSON fields for flexible section storage

## API Usage

See backend/README.md for detailed API documentation and examples.

## Notes

- PDFs are downloaded from official sources (OECD, India Tax Portal)
- docs_index.csv contains verified URLs (as of October 2024)
- Update docs_index.csv to add new jurisdictions/documents
- The backend/data/ directory is created automatically on first run

## Requirements

- Python 3.8+
- Ollama with llama3.2:latest model
- ~500MB disk space for knowledge base
- ~800MB RAM during policy generation

## License

See LICENSE file for details.

## GitHub Repository

https://github.com/balu72/TP1-InterCompany-Pricing-Policy

Last Updated: October 2024
