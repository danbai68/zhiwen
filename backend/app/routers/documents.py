from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import os, shutil
from ..database import get_db
from ..models import Document, KnowledgeBase
from ..security import get_current_user
from ..services.document_parser import load_document, split_documents

router = APIRouter(prefix="/documents", tags=["文档"])

UPLOAD_DIR = "data/uploads"


@router.post("/upload/{kb_id}")
async def upload_document(
        kb_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    # 1. 检查知识库是否存在且属于当前用户
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.user_id == current_user.id
    ).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 2. 检查文件类型
    allowed = [".pdf", ".docx", ".txt"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"仅支持 {allowed} 格式")

    # 3. 保存文件到本地
    kb_path = os.path.join(UPLOAD_DIR, str(kb_id))
    os.makedirs(kb_path, exist_ok=True)
    file_path = os.path.join(kb_path, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 4. 写入数据库（状态=processing）
    doc = Document(
        kb_id=kb_id,
        filename=file.filename,
        file_path=file_path,
        status="processing"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 5. 解析并切分
    try:
        raw_docs = load_document(file_path)
        chunks = split_documents(raw_docs)

        # 更新状态为完成
        doc.status = "done"
        doc.chunk_count = len(chunks)
        db.commit()

        return {
            "msg": "上传并解析成功",
            "document_id": doc.id,
            "filename": file.filename,
            "chunk_count": len(chunks)
        }
    except Exception as e:
        doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")