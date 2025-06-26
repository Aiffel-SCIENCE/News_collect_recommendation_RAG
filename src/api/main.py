from fastapi import FastAPI
from pydantic import BaseModel
import random
from datetime import datetime
app = FastAPI()

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
@app.get("/health")
async def health_check():
    """
    API 서비스의 상태를 확인하는 헬스체크 엔드포인트.
    """
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.post("/query", response_model=QueryResponse)
def handle_query(req: QueryRequest):
    print(f"📥 받은 질문: {req.query}")
    dummy_answer = random.choice([
        "mRNA 백신은 암 치료에도 적용되고 있어요.",
        "최근 mRNA 기술은 다양한 바이러스 대응에 활용됩니다.",
        "mRNA 백신 기술은 빠르게 진화하고 있습니다."
    ])
    return {"answer": dummy_answer}
