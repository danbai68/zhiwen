from fastapi import FastAPI
from .database import engine, Base
from . import models
from .routers import auth

# 自动创建所有表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="智问 API",
    description="AI智能知识库问答系统后端",
    version="0.3.0"
)

# 注册路由
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {
        "message": "Hello 智问",
        "status": "running",
        "docs": "访问 /docs 查看接口文档"
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "zhiwen-backend"}