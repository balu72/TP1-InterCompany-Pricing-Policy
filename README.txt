Regulatory KB — Ready-to-run package
------------------------------------
What's included:
1) docs_index.csv         - Metadata and authoritative URLs for priority documents (OECD + India).
2) download_and_prepare_kb.py - Script to download PDFs, extract text, and create chunked files (requires Python packages listed below).
3) folder_structure/      - Example folder structure created by the script when run.
4) LICENSE & README files.

How to use:
1) Install dependencies:
   pip install requests tqdm PyPDF2 pdfminer.six pandas sentencepiece transformers  # optional for embeddings
   (or use your own embedding toolchain)
2) Run the script:
   python download_and_prepare_kb.py
3) Result: 'kb_raw/' will contain downloaded PDFs, 'kb_text_chunks/' will contain text chunks and metadata.
4) Use your embedding pipeline to create vectors from the chunks and ingest into your vector DB.

Notes:
- The package DOES NOT include the PDFs themselves (copyright). The script downloads them from official sources using the URLs in docs_index.csv.
- The docs_index.csv contains OECD and Indian official links gathered and verified at the time of packaging.
- Update the docs_index.csv with additional documents or jurisdictions as needed.
