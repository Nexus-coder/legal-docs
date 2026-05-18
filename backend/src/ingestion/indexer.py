from dataclasses import dataclass
from typing import Any, Callable, Dict, List
from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from pinecone import Pinecone
from src.config import settings

EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}
EMBEDDING_CHUNK_TOKENS = 1800
EMBEDDING_CHUNK_OVERLAP = 150


@dataclass(frozen=True)
class PineconePreflightResult:
    index_name: str
    embedding_model: str
    embedding_dimension: int
    index_dimension: int


class PineconePreflightError(RuntimeError):
    """Raised when the vector index cannot accept the configured embeddings."""


class PineconeDimensionMismatch(PineconePreflightError):
    def __init__(
        self,
        *,
        index_name: str,
        embedding_model: str,
        embedding_dimension: int,
        index_dimension: int,
    ):
        self.index_name = index_name
        self.embedding_model = embedding_model
        self.embedding_dimension = embedding_dimension
        self.index_dimension = index_dimension
        super().__init__(
            f"Pinecone index dimension {index_dimension} does not match embedding dimension {embedding_dimension}"
        )


def setup_settings():
    """Configures global LlamaIndex settings including the embedding model."""
    Settings.embed_model = OpenAIEmbedding(
        model=settings.OPENAI_EMBEDDING_MODEL, api_key=settings.OPENAI_API_KEY
    )


def embedding_dimension(model: str | None = None) -> int:
    model_name = model or settings.OPENAI_EMBEDDING_MODEL
    try:
        return EMBEDDING_DIMENSIONS[model_name]
    except KeyError as exc:
        raise PineconePreflightError(
            f"Unknown embedding dimension for model {model_name!r}"
        ) from exc


def pinecone_index_dimension() -> int:
    api_key = settings.PINECONE_API_KEY
    index_name = settings.PINECONE_INDEX_NAME
    if not api_key or not index_name:
        raise PineconePreflightError("Missing Pinecone credentials in environment.")

    pc = Pinecone(api_key=api_key)
    description = pc.describe_index(index_name)
    dimension = getattr(description, "dimension", None)
    if dimension is None and isinstance(description, dict):
        dimension = description.get("dimension")
    if dimension is None:
        raise PineconePreflightError(
            f"Could not determine dimension for Pinecone index {index_name!r}"
        )
    return int(dimension)


def validate_pinecone_index_dimension(
    *,
    index_dimension_provider: Callable[[], int] | None = None,
    embedding_model: str | None = None,
) -> PineconePreflightResult:
    model_name = embedding_model or settings.OPENAI_EMBEDDING_MODEL
    expected_dimension = embedding_dimension(model_name)
    actual_dimension = (
        index_dimension_provider() if index_dimension_provider else pinecone_index_dimension()
    )
    if actual_dimension != expected_dimension:
        raise PineconeDimensionMismatch(
            index_name=settings.PINECONE_INDEX_NAME,
            embedding_model=model_name,
            embedding_dimension=expected_dimension,
            index_dimension=actual_dimension,
        )
    return PineconePreflightResult(
        index_name=settings.PINECONE_INDEX_NAME,
        embedding_model=model_name,
        embedding_dimension=expected_dimension,
        index_dimension=actual_dimension,
    )


def index_markdown(text: str, source_metadata: dict, namespace: str | None = None) -> int:
    """
    Chunks Markdown text into hierarchical nodes and indexes them into Pinecone
    using advanced retrieval features. Returns the number of nodes indexed.
    """
    setup_settings()

    api_key = settings.PINECONE_API_KEY
    index_name = settings.PINECONE_INDEX_NAME
    if not api_key or not index_name:
        raise ValueError("Missing Pinecone credentials in environment.")

    pc = Pinecone(api_key=api_key)
    pinecone_index = pc.Index(index_name)

    vector_store_kwargs = {"pinecone_index": pinecone_index}
    if namespace:
        vector_store_kwargs["namespace"] = namespace
    vector_store = PineconeVectorStore(**vector_store_kwargs)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    nodes = embedding_safe_nodes(text, source_metadata)

    # Generating embeddings and inserting into Pinecone
    VectorStoreIndex(nodes, storage_context=storage_context)

    return len(nodes)


def embedding_safe_nodes(text: str, source_metadata: dict) -> list:
    """
    Split source text before embedding so no single node approaches the model limit.

    OpenAI embedding models reject inputs above 8192 tokens. Kenya Law judgments can
    contain very long paragraphs, so Markdown-only splitting is not enough.
    """
    splitter = TokenTextSplitter(
        chunk_size=EMBEDDING_CHUNK_TOKENS,
        chunk_overlap=EMBEDDING_CHUNK_OVERLAP,
    )
    doc = Document(text=text, metadata=source_metadata)
    return splitter.get_nodes_from_documents([doc])


def delete_document_vectors(canonical_url: str, namespace: str | None = None) -> None:
    """Remove vectors previously indexed for a Kenya Law canonical URL."""
    api_key = settings.PINECONE_API_KEY
    index_name = settings.PINECONE_INDEX_NAME
    if not api_key or not index_name:
        raise ValueError("Missing Pinecone credentials in environment.")

    pc = Pinecone(api_key=api_key)
    pinecone_index = pc.Index(index_name)
    delete_kwargs: dict[str, Any] = {"filter": {"canonical_url": {"$eq": canonical_url}}}
    if namespace:
        delete_kwargs["namespace"] = namespace
    pinecone_index.delete(**delete_kwargs)


def retrieve_context(
    query: str,
    similarity_top_k: int = 3,
    namespace: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Fetches the most relevant markdown nodes from Pinecone using LlamaIndex.
    """
    setup_settings()

    api_key = settings.PINECONE_API_KEY
    index_name = settings.PINECONE_INDEX_NAME
    if not api_key or not index_name:
        return []

    pc = Pinecone(api_key=api_key)
    pinecone_index = pc.Index(index_name)

    vector_store_kwargs = {"pinecone_index": pinecone_index}
    if namespace:
        vector_store_kwargs["namespace"] = namespace
    vector_store = PineconeVectorStore(**vector_store_kwargs)
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

    retriever = index.as_retriever(similarity_top_k=similarity_top_k)
    nodes = retriever.retrieve(query)

    return [
        {"text": n.node.get_content(), "metadata": n.node.metadata, "score": n.score}
        for n in nodes
    ]
