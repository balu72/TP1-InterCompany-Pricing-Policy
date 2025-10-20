import os
from pathlib import Path
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.storage import StorageContext
import chromadb

# === CONFIGURATION ===
# Get the project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent
CHUNKS_DIR = PROJECT_ROOT / "data" / "kb_text_chunks"
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_db"
LLM_MODEL = "llama3.2:latest"            # or "mistral", "phi3", etc.
EMBED_MODEL = "nomic-embed-text"
TOP_K = 10  # Increased from 5 to retrieve more relevant chunks

def main():
    """Main function to run the RAG system."""
    try:
        # === LOAD DOCUMENTS ===
        if not CHUNKS_DIR.exists():
            raise FileNotFoundError(f"Chunks directory not found: {CHUNKS_DIR}")
        
        print(f"Loading documents from: {CHUNKS_DIR}")
        documents = SimpleDirectoryReader(input_dir=str(CHUNKS_DIR)).load_data()
        print(f"Loaded {len(documents)} text chunks")

        # === EMBEDDING & VECTOR STORE ===
        print("Initializing embedding model and vector store...")
        embed_model = OllamaEmbedding(model_name=EMBED_MODEL)
        
        # Create persistent ChromaDB client
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = chroma_client.get_or_create_collection("regulatory_kb_local")
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # === CONFIGURE SETTINGS ===
        # Set global settings (replaces deprecated ServiceContext)
        llm = Ollama(model=LLM_MODEL, request_timeout=120)
        Settings.llm = llm
        Settings.embed_model = embed_model

        # === BUILD INDEX ===
        print("Building vector index...")
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
        )

        # === QUERY ENGINE ===
        query_engine = index.as_query_engine(
            similarity_top_k=TOP_K,
        )

        # === RUN INTERACTIVE LOOP ===
        print("\n" + "="*80)
        print("RAG is ready! Ask questions about OECD or TP regulations")
        print("Commands: 'exit' or 'quit' to stop")
        print("="*80 + "\n")
        
        while True:
            try:
                q = input("Q: ")
                if q.lower().strip() in ["exit", "quit", ""]:
                    print("Goodbye!")
                    break
                
                print("Searching...")
                response = query_engine.query(q)
                print(f"\nA: {response}\n")
                print("-"*80)
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Goodbye!")
                break
            except Exception as e:
                print(f"\nError processing query: {e}\n")
                print("-"*80)
                
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure the data/kb_text_chunks directory exists in the project root.")
    except Exception as e:
        print(f"Error initializing RAG system: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
