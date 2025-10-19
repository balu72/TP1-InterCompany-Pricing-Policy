"""Integration with existing RAG system."""
import sys
from pathlib import Path
from typing import List, Dict

# Add parent directory to path to import from src/
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from llama_index.core import VectorStoreIndex, Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

class RAGSystem:
    """Wrapper for the existing RAG system."""
    
    def __init__(self, chunks_dir: Path, chroma_db_path: Path, ollama_model: str = "llama3.2:latest", 
                 embed_model: str = "nomic-embed-text", top_k: int = 10):
        """Initialize RAG system."""
        self.chunks_dir = chunks_dir
        self.chroma_db_path = chroma_db_path
        self.ollama_model = ollama_model
        self.embed_model = embed_model
        self.top_k = top_k
        
        # Initialize components
        self._setup_rag()
    
    def _setup_rag(self):
        """Set up RAG components."""
        # Initialize embedding model
        embed_model = OllamaEmbedding(model_name=self.embed_model)
        
        # Initialize LLM
        llm = Ollama(model=self.ollama_model, request_timeout=120)
        
        # Set global settings
        Settings.llm = llm
        Settings.embed_model = embed_model
        
        # Initialize ChromaDB
        chroma_client = chromadb.PersistentClient(path=str(self.chroma_db_path))
        collection = chroma_client.get_or_create_collection("regulatory_kb_local")
        vector_store = ChromaVectorStore(chroma_collection=collection)
        
        # Create index
        self.index = VectorStoreIndex.from_vector_store(vector_store)
        
        # Create query engine
        self.query_engine = self.index.as_query_engine(similarity_top_k=self.top_k)
    
    def query(self, query_text: str) -> Dict[str, any]:
        """
        Query the RAG system and return response with context.
        
        Args:
            query_text: The query to search for
            
        Returns:
            Dict with 'response' and 'source_nodes' (context chunks)
        """
        response = self.query_engine.query(query_text)
        
        # Extract source nodes (retrieved chunks)
        source_nodes = []
        if hasattr(response, 'source_nodes'):
            for node in response.source_nodes:
                source_nodes.append({
                    'text': node.node.text,
                    'score': node.score,
                    'metadata': node.node.metadata if hasattr(node.node, 'metadata') else {}
                })
        
        return {
            'response': str(response),
            'source_nodes': source_nodes
        }
    
    def retrieve_context(self, query_text: str) -> List[str]:
        """
        Retrieve relevant context chunks without generating a response.
        
        Args:
            query_text: The query to search for
            
        Returns:
            List of relevant text chunks
        """
        retriever = self.index.as_retriever(similarity_top_k=self.top_k)
        nodes = retriever.retrieve(query_text)
        
        return [node.node.text for node in nodes]
    
    def generate_with_context(self, prompt: str, context_query: str = None) -> str:
        """
        Generate text using LLM with optional context retrieval.
        
        Args:
            prompt: The prompt to generate from
            context_query: Optional query to retrieve context first
            
        Returns:
            Generated text
        """
        if context_query:
            # Retrieve context first
            context_chunks = self.retrieve_context(context_query)
            
            # Augment prompt with context
            context_text = "\n\n".join([f"Context {i+1}:\n{chunk}" for i, chunk in enumerate(context_chunks)])
            full_prompt = f"{context_text}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        # Generate using LLM
        response = Settings.llm.complete(full_prompt)
        return str(response)

def create_rag_system(config) -> RAGSystem:
    """Factory function to create RAG system from config."""
    return RAGSystem(
        chunks_dir=config.get('RAG_CHUNKS_DIR'),
        chroma_db_path=config.get('RAG_CHROMA_DB'),
        ollama_model=config.get('OLLAMA_MODEL', 'llama3.2:latest'),
        embed_model=config.get('EMBEDDING_MODEL', 'nomic-embed-text'),
        top_k=config.get('RAG_TOP_K', 10)
    )
