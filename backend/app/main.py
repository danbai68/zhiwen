from fastapi import FastAPI

app = FastAPI(
    title="智问 API",
    description="AI智能知识库问答系统后端",
    version="0.1.0"
)

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