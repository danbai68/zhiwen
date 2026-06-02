import os
import httpx
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from .vector_store import search_kb

# 创建自定义 httpx 客户端，禁用 SSL 验证（解决国内网络问题）
http_client = httpx.Client(verify=False)

RAG_PROMPT = """你是一个专业的文档问答助手。请基于以下检索到的上下文回答问题。
如果上下文中没有相关信息，请明确说"根据提供的文档，我无法找到相关信息"。

上下文：
{context}

问题：{question}

请回答，并在回答末尾列出引用的文档来源。"""


def get_rag_answer(kb_id: int, question: str, history: list = None):
    """执行 RAG 流程：检索 + 生成回答"""
    # 1. 检索相关文档
    docs = search_kb(kb_id, question, k=3)

    if not docs:
        return "根据提供的文档，我无法找到相关信息。", []

    # 2. 构建上下文
    context = "\n\n".join([
        f"[来源: {doc.metadata.get('source', '未知')}]\n{doc.page_content}"
        for doc in docs
    ])

    # 3. 调用 Moonshot LLM（使用自定义 http_client）
    llm = ChatOpenAI(
        model="moonshot-v1-8k",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=os.getenv("OPENAI_BASE_URL"),
        temperature=0.3,
        streaming=True,
        http_client=http_client  # ← 禁用 SSL 验证
    )

    prompt = PromptTemplate(
        template=RAG_PROMPT,
        input_variables=["context", "question"]
    )

    # 4. 生成回答
    chain = prompt | llm
    response = chain.invoke({
        "context": context,
        "question": question
    })

    # 5. 提取来源
    sources = list(set([
        doc.metadata.get("source", "未知")
        for doc in docs
    ]))

    return response.content, sources