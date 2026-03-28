import os
from typing import List, Dict, Any
from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from pinecone import Pinecone

def setup_settings():
    """Configures global LlamaIndex settings including the embedding model."""
    Settings.embed_model = OpenAIEmbedding(
        model="text-embedding-3-small",
        api_key=os.environ.get("OPENAI_API_KEY")
    )

def index_markdown(text: str, source_metadata: dict) -> int:
    """
    Chunks Markdown text into hierarchical nodes and indexes them into Pinecone
    using advanced retrieval features. Returns the number of nodes indexed.
    """
    setup_settings()
    
    api_key = os.environ.get("PINECONE_API_KEY")
    index_name = os.environ.get("PINECONE_INDEX_NAME", "legal-docs")
    if not api_key or not index_name:
        raise ValueError("Missing Pinecone credentials in environment.")
        
    pc = Pinecone(api_key=api_key)
    pinecone_index = pc.Index(index_name)
    
    vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Robust MD parsing handles nested headers preserving context
    parser = MarkdownNodeParser()
    doc = Document(text=text, metadata=source_metadata)
    nodes = parser.get_nodes_from_documents([doc])
    
    # Generating embeddings and inserting into Pinecone
    VectorStoreIndex(nodes, storage_context=storage_context)
    
    return len(nodes)

def retrieve_context(query: str, similarity_top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Fetches the most relevant markdown nodes from Pinecone using LlamaIndex.
    """
    setup_settings()
    
    api_key = os.environ.get("PINECONE_API_KEY")
    index_name = os.environ.get("PINECONE_INDEX_NAME", "legal-docs")
    if not api_key or not index_name:
        return []
        
    pc = Pinecone(api_key=api_key)
    pinecone_index = pc.Index(index_name)
    
    vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
    
    retriever = index.as_retriever(similarity_top_k=similarity_top_k)
    nodes = retriever.retrieve(query)
    
    return [
        {
            "text": n.node.get_content(),
            "metadata": n.node.metadata,
            "score": n.score
        }
        for n in nodes
    ]
