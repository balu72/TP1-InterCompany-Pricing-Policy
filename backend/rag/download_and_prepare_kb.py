# download_and_prepare_kb.py
# Run this script to download authoritative PDFs, extract text, split into chunks, and write chunk metadata.
#
# Requirements:
#   pip install requests tqdm PyPDF2 pdfminer.six pandas
#
# Usage:
#   python download_and_prepare_kb.py
#
import os, csv, requests, pathlib, sys
from tqdm import tqdm
from urllib.parse import urlparse
from pathlib import Path
import io
try:
    from pdfminer.high_level import extract_text
except Exception as e:
    print('pdfminer not installed or failed to import. Install pdfminer.six', e)
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
OUT_RAW = BASE_DIR / 'kb_raw'
OUT_TEXT = BASE_DIR / 'kb_text_chunks'
OUT_RAW.mkdir(exist_ok=True)
OUT_TEXT.mkdir(exist_ok=True)

def download_file(url, out_path):
    print(f'Downloading: {url}')
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    total = int(resp.headers.get('content-length', 0))
    with open(out_path, 'wb') as f, tqdm(total=total, unit='B', unit_scale=True, desc=out_path.name) as pbar:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))

def safe_filename(s):
    return ''.join(c if c.isalnum() or c in '._-' else '_' for c in s)

# Read docs_index.csv
docs = []
with open(BASE_DIR / 'docs_index.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        docs.append(row)

for doc in docs:
    url = doc['url']
    filename = doc['local_filename']
    out_path = OUT_RAW / filename
    
    # Handle LOCAL files (already downloaded)
    if url.upper() == 'LOCAL':
        if not out_path.exists():
            print(f'LOCAL file not found: {out_path}')
            continue
        print(f'Processing LOCAL file: {filename}')
    # Skip if not an http(s) PDF link
    elif not url.lower().startswith('http'):
        print('Skipping non-http url:', url)
        continue
    # Try to download
    else:
        try:
            download_file(url, out_path)
        except Exception as e:
            print('Download failed for', url, e)
            continue
    
    # Extract text - handle HTML separately
    if filename.lower().endswith('.html') or filename.lower().endswith('.htm'):
        print(f'HTML file detected: {filename} - extracting text from HTML')
        try:
            with open(out_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            # Simple HTML text extraction (strip tags)
            from html.parser import HTMLParser
            class HTMLTextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                def handle_data(self, data):
                    self.text.append(data)
            parser = HTMLTextExtractor()
            parser.feed(html_content)
            text = ' '.join(parser.text)
        except Exception as e:
            print('HTML text extraction failed for', out_path, e)
            text = ''
    else:
        # PDF text extraction
        try:
            text = extract_text(str(out_path))
        except Exception as e:
            print('Text extraction failed for', out_path, e)
            text = ''
    # Simple chunking: split by 5000 characters
    chunk_size = 5000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)] if text else []
    meta_rows = []
    for i, ch in enumerate(chunks):
        chunk_file = OUT_TEXT / f"{doc['id']}_chunk_{i+1}.txt"
        with open(chunk_file, 'w', encoding='utf-8') as cf:
            cf.write(ch)
        meta_rows.append({
            'doc_id': doc['id'],
            'chunk_id': f"{doc['id']}_chunk_{i+1}",
            'chunk_file': str(chunk_file),
            'source_url': doc['url']
        })
    # write per-doc metadata csv
    if meta_rows:
        import pandas as pd
        pd.DataFrame(meta_rows).to_csv(OUT_TEXT / f"{doc['id']}_chunks_metadata.csv", index=False)
print('Done. Raw PDFs in kb_raw/, text chunks in kb_text_chunks/.')
