from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

VECTORSTORE_PATH = Path(__file__).parent.parent / "vectorstore"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 4

_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)


def build_vectorstore(file_paths: list[str]) -> FAISS:
    docs = []
    for path in file_paths:
        if path.endswith(".pdf"):
            loader = PyPDFLoader(path)
        else:
            loader = TextLoader(path)
        docs.extend(loader.load())

    chunks = _splitter.split_documents(docs)
    store = FAISS.from_documents(chunks, _embeddings)
    store.save_local(str(VECTORSTORE_PATH))
    return store


def load_vectorstore() -> FAISS | None:
    if not VECTORSTORE_PATH.exists():
        return None
    return FAISS.load_local(str(VECTORSTORE_PATH), _embeddings, allow_dangerous_deserialization=True)


def retrieve(query: str, store: FAISS) -> list:
    return store.similarity_search(query, k=TOP_K)
