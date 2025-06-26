# src/app/rag_api.py

import os
import sys
from typing import Optional, List, Dict, Any
import traceback
from datetime import datetime

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(dotenv_path="/home/br631533333333_gmail_com/Aigen_science/.env")

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import time
from typing import AsyncGenerator
from fastapi.responses import StreamingResponse
import json

from fastapi.middleware.cors import CORSMiddleware

# --- 프로젝트 경로 설정 ---
_current_file_path = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file_path)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config_loader.settings import SETTINGS
# --- RAG 파이프라인 임포트 ---
from src.rag_graph.graph_rag import graph

# --- Pydantic 모델 정의 ---
# --- Pydantic 모델 정의 ---
class RAGRequest(BaseModel):
    user_id: str
    query: str
    chat_id: Optional[str] = None

class RAGResponse(BaseModel):
    type: str
    text: str
    dashboard_html: str
    react_code: str
    response_metadata: dict
    answer_source: str

# --- FastAPI 앱 설정 ---
fastapi_app = FastAPI(
    title="AIGEN Science - Hybrid RAG API",
    version="2.1.0"
)

# --- CORS 미들웨어 설정 ---
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000"
    "http://34.61.170.171:3000"
]
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health Check 엔드포인트 ---
@fastapi_app.get("/health")
async def health_check():
    """
    RAG API 서비스의 상태를 확인하는 헬스체크 엔드포인트.
    """
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# --- /rag-chat 엔드포인트 ---
@fastapi_app.post("/rag-chat", response_model=RAGResponse)
async def handle_rag_chat(request: RAGRequest):
    inputs = {"user_id": request.user_id, "query": request.query, "chat_id": request.chat_id}
    config = {'recursion_limit': 15}

    # 그래프 실행
    try:
        final_state = graph.invoke(inputs, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 모든 가능한 키를 가져와 응답
    response_data = {
        "type": final_state.get("intent", ""),
        "text": final_state.get("final_answer", ""),
        "dashboard_html": final_state.get("dashboard_html", ""),
        "react_code": final_state.get("react_code", ""),
        "response_metadata": final_state.get("response_metadata", {}),
        "answer_source": final_state.get("answer_source", "")
    }
    return response_data

# --- /rag-chat-stream 엔드포인트 ---
@fastapi_app.post("/rag-chat-stream")
async def handle_rag_chat_stream(request: RAGRequest):
    inputs = {"user_id": request.user_id, "query": request.query, "chat_id": request.chat_id}
    config = {'recursion_limit': 15}

    async def stream_generator():
        async for event in graph.astream(inputs, config=config):
            if 'finalization' in event:
                state = event['finalization']
                data = {
                    "type": state.get("intent", ""),
                    "text": state.get("final_answer", ""),
                    "dashboard_html": state.get("dashboard_html", ""),
                    "react_code": state.get("react_code", ""),
                    "response_metadata": state.get("response_metadata", {}),
                    "answer_source": state.get("answer_source", "")
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            elif '__end__' not in event:
                # 중간 단계 알림
                for node in event:
                    if node != '__end__':
                        info = {"step": node}
                        yield f"2:{json.dumps(info, ensure_ascii=False)}\n\n"
    return StreamingResponse(stream_generator(), media_type="text/event-stream")

# --- 서버 실행 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8010)
