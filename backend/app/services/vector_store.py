import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

# 使用本地轻量级嵌入模型（免费，无需API Key）
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_vectorstore(kb_id: int):
    """获取指定知识库的向量数据库"""
    persist_dir = f"data/vectorstores/{kb_id}"
    os.makedirs(persist_dir, exist_ok=True)

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},  # 用CPU，不需要显卡
        encode_kwargs={"normalize_embeddings": True}
    )

    return Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings
    )


def add_documents_to_kb(kb_id: int, chunks: list[Document]):
    """将切分后的文本块存入向量库"""
    vectorstore = get_vectorstore(kb_id)

    for chunk in chunks:
        chunk.metadata.update({"kb_id": kb_id})

    vectorstore.add_documents(chunks)
    vectorstore.persist()
    return len(chunks)


def search_kb(kb_id: int, query: str, k: int = 5):
    """在知识库中检索最相关的文本块"""
    vectorstore = get_vectorstore(kb_id)
    return vectorstore.similarity_search(query, k=k)