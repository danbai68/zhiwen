from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import KnowledgeBase, Conversation, Message
from ..security import get_current_user
from ..services.rag_chain import get_rag_answer
from ..services.vector_store import search_kb
import json
import asyncio
import os
import httpx

http_client = httpx.Client(verify=False)

router = APIRouter(prefix="/chat", tags=["问答"])


@router.post("/search/{kb_id}")
def search_test(
        kb_id: int,
        query: str,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """检索测试接口（非流式）"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.user_id == current_user.id
    ).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    results = search_kb(kb_id, query, k=3)
    return {
        "query": query,
        "results": [
            {
                "content": doc.page_content[:200] + "...",
                "source": doc.metadata.get("source", "未知")
            }
            for doc in results
        ]
    }


@router.post("/ask/{kb_id}")
async def ask(
        kb_id: int,
        question: str,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """RAG 问答接口（非流式，返回完整回答）"""
    # 检查权限
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.user_id == current_user.id
    ).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 创建或获取对话
    conversation = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.kb_id == kb_id
    ).first()

    if not conversation:
        conversation = Conversation(
            user_id=current_user.id,
            kb_id=kb_id,
            title=question[:20] + "..."
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 保存用户问题
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=question
    )
    db.add(user_msg)
    db.commit()

    # RAG 生成回答
    answer, sources = get_rag_answer(kb_id, question)

    # 保存助手回答
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        sources=sources
    )
    db.add(assistant_msg)
    db.commit()

    return {
        "answer": answer,
        "sources": sources,
        "conversation_id": conversation.id
    }


@router.post("/ask/stream/{kb_id}")
async def ask_stream(
        kb_id: int,
        question: str,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """RAG 流式问答接口（SSE）"""
    # 检查权限
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.user_id == current_user.id
    ).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 创建对话
    conversation = Conversation(
        user_id=current_user.id,
        kb_id=kb_id,
        title=question[:20] + "..."
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    # 保存用户问题
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=question
    )
    db.add(user_msg)
    db.commit()

    # 检索相关文档
    docs = search_kb(kb_id, question, k=3)
    sources = list(set([doc.metadata.get("source", "未知") for doc in docs]))

    # 构建上下文
    context = "\n\n".join([
        f"[来源: {doc.metadata.get('source', '未知')}]\n{doc.page_content}"
        for doc in docs
    ])

    # 流式生成
    from langchain_openai import ChatOpenAI
    from langchain.prompts import PromptTemplate

    llm = ChatOpenAI(
        model="moonshot-v1-8k",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=os.getenv("OPENAI_BASE_URL"),
        temperature=0.3,
        streaming=True,
        http_client=http_client
    )

    prompt = PromptTemplate(
        template="""你是一个专业的文档问答助手。请基于以下上下文回答问题。
如果上下文中没有相关信息，请明确说"根据提供的文档，我无法找到相关信息"。

上下文：
{context}

问题：{question}

请回答：""",
        input_variables=["context", "question"]
    )

    chain = prompt | llm

    full_answer = ""

    async def event_generator():
        nonlocal full_answer

        for chunk in chain.stream({
            "context": context,
            "question": question
        }):
            content = chunk.content
            full_answer += content
            yield f"data: {json.dumps({'token': content}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.01)

        # 发送结束标记
        yield f"data: {json.dumps({'done': True, 'sources': sources}, ensure_ascii=False)}\n\n"

        # 保存完整回答到数据库
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=full_answer,
            sources=sources
        )
        db.add(assistant_msg)
        db.commit()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )