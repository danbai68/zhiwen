from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import KnowledgeBase, User
from ..schemas import KnowledgeBaseCreate, KnowledgeBaseResponse
from ..security import get_current_user

router = APIRouter(prefix="/kbs", tags=["知识库"])


@router.post("/", response_model=KnowledgeBaseResponse)
def create_kb(
        kb: KnowledgeBaseCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建知识库（需要登录）"""
    new_kb = KnowledgeBase(
        name=kb.name,
        description=kb.description,
        user_id=current_user.id
    )
    db.add(new_kb)
    db.commit()
    db.refresh(new_kb)
    return new_kb


@router.get("/", response_model=List[KnowledgeBaseResponse])
def list_kbs(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """列出当前用户的所有知识库（需要登录）"""
    return db.query(KnowledgeBase).filter(KnowledgeBase.user_id == current_user.id).all()


@router.delete("/{kb_id}")
def delete_kb(
        kb_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """删除知识库（只能删自己的，需要登录）"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.user_id == current_user.id
    ).first()

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在或无权限删除")

    db.delete(kb)
    db.commit()
    return {"msg": "删除成功"}