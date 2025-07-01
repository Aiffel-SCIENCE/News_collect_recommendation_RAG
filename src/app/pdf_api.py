"""
PDF 업로드 및 처리 API
FastAPI를 사용하여 PDF 파일을 업로드하고 처리하는 엔드포인트
"""

import os
import sys
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import traceback

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(dotenv_path="/home/br631533333333_gmail_com/Aigen_science/.env")

# 프로젝트 루트 경로 설정
_current_file_path = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file_path)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ..services.pdf_processor import PDFProcessor

# FastAPI 앱 인스턴스
app = FastAPI(
    title="PDF 처리 API",
    description="PDF 파일을 업로드하고 GPT로 분석하여 MongoDB와 Pinecone DB에 저장하는 API",
    version="1.0.0"
)

# CORS 미들웨어 추가
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "*"  # 개발용으로 모든 origin 허용
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PDF 프로세서 인스턴스
pdf_processor = None

# 응답 모델
class PDFProcessResponse(BaseModel):
    success: bool
    pdf_id: str = None
    title: str = None
    summary: str = None
    mongo_saved: bool = False
    pinecone_saved: bool = False
    chunk_count: int = 0
    file_size: int = 0
    error: str = None

class PDFListResponse(BaseModel):
    pdfs: List[Dict[str, Any]]
    total_count: int

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화"""
    global pdf_processor
    try:
        pdf_processor = PDFProcessor()
        print("✅ PDF API 서버 초기화 완료")
    except Exception as e:
        print(f"❌ PDF API 서버 초기화 실패: {e}")
        raise

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "PDF 처리 API 서버가 실행 중입니다",
        "version": "1.0.0",
        "endpoints": {
            "upload_pdf": "/upload-pdf",
            "upload_pdf_batch": "/upload-pdf-batch",
            "list_pdfs": "/list-pdfs",
            "get_pdf": "/pdf/{pdf_id}",
            "delete_pdf": "/pdf/{pdf_id}",
            "search_pdfs": "/search-pdfs"
        }
    }

@app.post("/upload-pdf", response_model=PDFProcessResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """단일 PDF 파일 업로드 및 처리"""
    try:
        # 파일 타입 검증
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")
        
        # 파일 크기 검증 (50MB 제한)
        if file.size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="파일 크기는 50MB를 초과할 수 없습니다")
        
        # 파일 내용 읽기
        pdf_content = await file.read()
        
        # PDF 처리
        result = pdf_processor.process_pdf(pdf_content, file.filename)
        
        if result["success"]:
            return PDFProcessResponse(**result)
        else:
            raise HTTPException(status_code=500, detail=f"PDF 처리 실패: {result.get('error', '알 수 없는 오류')}")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"PDF 업로드 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.post("/upload-pdf-batch")
async def upload_pdf_batch(files: List[UploadFile] = File(...), urls: List[str] = None):
    """여러 PDF 파일 일괄 업로드 및 처리"""
    try:
        results = []
        
        for i, file in enumerate(files):
            try:
                # 파일 타입 검증
                if not file.filename.lower().endswith('.pdf'):
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": "PDF 파일이 아닙니다"
                    })
                    continue
                
                # 파일 크기 검증
                if file.size > 50 * 1024 * 1024:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": "파일 크기가 50MB를 초과합니다"
                    })
                    continue
                
                # 파일 내용 읽기
                pdf_content = await file.read()
                
                # URL 가져오기 (인덱스가 범위 내에 있는 경우)
                url = urls[i] if urls and i < len(urls) else None
                
                # PDF 처리
                result = pdf_processor.process_pdf(pdf_content, file.filename)
                result["filename"] = file.filename
                results.append(result)
                
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "message": f"{len(files)}개 파일 처리 완료",
            "results": results,
            "success_count": sum(1 for r in results if r.get("success", False)),
            "failure_count": sum(1 for r in results if not r.get("success", False))
        }
        
    except Exception as e:
        print(f"일괄 업로드 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.get("/list-pdfs", response_model=PDFListResponse)
async def list_pdfs(skip: int = 0, limit: int = 20, category: str = None):
    """저장된 PDF 목록 조회"""
    try:
        # MongoDB에서 PDF 목록 조회
        query = {"source": "pdf_upload"}
        if category:
            query["category"] = category
        
        cursor = pdf_processor.articles_collection.find(
            query,
            {
                "ID": 1,
                "title": 1,
                "summary": 1,
                "category": 1,
                "importance": 1,
                "uploaded_at": 1,
                "filename": 1,
                "chunk_count": 1,
                "file_size": 1
            }
        ).skip(skip).limit(limit).sort("uploaded_at", -1)
        
        pdfs = list(cursor)
        
        # 총 개수 조회
        total_count = pdf_processor.articles_collection.count_documents(query)
        
        return PDFListResponse(pdfs=pdfs, total_count=total_count)
        
    except Exception as e:
        print(f"PDF 목록 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.get("/pdf/{pdf_id}")
async def get_pdf(pdf_id: str):
    """특정 PDF 상세 정보 조회"""
    try:
        pdf = pdf_processor.articles_collection.find_one(
            {"ID": pdf_id, "source": "pdf_upload"},
            {"embedding": 0}  # 임베딩은 제외
        )
        
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF를 찾을 수 없습니다")
        
        return pdf
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"PDF 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.delete("/pdf/{pdf_id}")
async def delete_pdf(pdf_id: str):
    """PDF 삭제"""
    try:
        # MongoDB에서 삭제
        mongo_result = pdf_processor.articles_collection.delete_one({"ID": pdf_id})
        
        if mongo_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="PDF를 찾을 수 없습니다")
        
        # Pinecone에서 삭제 (선택사항)
        try:
            pdf_processor.pinecone_manager.get_index().delete(ids=[pdf_id])
            print(f"Pinecone에서 PDF ID {pdf_id} 삭제 완료")
        except Exception as e:
            print(f"Pinecone 삭제 실패 (무시됨): {e}")
        
        return {"message": "PDF 삭제 완료", "pdf_id": pdf_id}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"PDF 삭제 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.get("/search-pdfs")
async def search_pdfs(query: str, limit: int = 10):
    """PDF 내용 검색"""
    try:
        # 쿼리 임베딩 생성
        query_embedding = pdf_processor.generate_embedding(query)
        
        # Pinecone에서 유사한 벡터 검색
        matches = pdf_processor.pinecone_manager.query_vector(
            vector=query_embedding,
            top_k=limit,
            include_metadata=True
        )
        
        # 검색 결과에 MongoDB 데이터 추가
        results = []
        for match in matches:
            pdf_id = match.id
            pdf_data = pdf_processor.articles_collection.find_one(
                {"ID": pdf_id},
                {"embedding": 0}  # 임베딩은 제외
            )
            
            if pdf_data:
                pdf_data["similarity_score"] = match.score
                results.append(pdf_data)
        
        return {
            "query": query,
            "results": results,
            "total_found": len(results)
        }
        
    except Exception as e:
        print(f"PDF 검색 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        # MongoDB 연결 확인
        pdf_processor.mongo_client.admin.command('ping')
        
        # Pinecone 연결 확인
        pdf_processor.pinecone_manager.get_index()
        
        return {
            "status": "healthy",
            "mongodb": "connected",
            "pinecone": "connected",
            "timestamp": str(datetime.now())
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": str(datetime.now())
            }
        )

if __name__ == "__main__":
    uvicorn.run(
        "pdf_api:app",
        host="0.0.0.0",
        port=8013,
        reload=True,
        log_level="info"
    ) 