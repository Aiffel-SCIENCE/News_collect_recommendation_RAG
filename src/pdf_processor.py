"""
PDF 처리 모듈
PDF 파일을 파싱하고 GPT로 분석하여 MongoDB와 Pinecone DB에 저장
"""

import os
import sys
import hashlib
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import traceback

# 프로젝트 루트 경로 설정
_current_file_path = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(_current_file_path))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.config_loader.settings import SETTINGS
from src.db.vector_db import PineconeDB
from pymongo import MongoClient
import certifi
from openai import OpenAI
import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter
import io

class PDFProcessor:
    """PDF 파일 처리 및 분석 클래스"""
    
    def __init__(self):
        """PDF 프로세서 초기화"""
        self.openai_client = None
        self.pinecone_manager = None
        self.mongo_client = None
        self.articles_collection = None
        self.embedding_model_name = SETTINGS.get("SHARED_EMBEDDING_MODEL_NAME", "text-embedding-3-small")
        self.llm_model_name = SETTINGS.get("OPENAI_LLM_EXTRACTION_MODEL", "gpt-4.1-nano")
        
        self._initialize_clients()
    
    def _initialize_clients(self):
        """클라이언트들 초기화"""
        try:
            # OpenAI 클라이언트 초기화
            api_key = SETTINGS.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
            self.openai_client = OpenAI(api_key=api_key)
            print("✅ OpenAI 클라이언트 초기화 성공")
            
            # Pinecone DB 초기화
            self.pinecone_manager = PineconeDB()
            print("✅ Pinecone DB 초기화 성공")
            
            # MongoDB 클라이언트 초기화
            mongo_uri = SETTINGS.get("MONGO_URI")
            if not mongo_uri:
                raise ValueError("MONGO_URI가 설정되지 않았습니다.")
            
            self.mongo_client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
            self.mongo_client.admin.command('ping')  # 연결 테스트
            
            db_name = SETTINGS.get("MONGO_DB_NAME", "newsdb")
            db = self.mongo_client[db_name]
            
            articles_collection_name = SETTINGS.get("MONGO_ARTICLES_COLLECTION_NAME", "articles")
            self.articles_collection = db[articles_collection_name]
            print("✅ MongoDB 클라이언트 초기화 성공")
            
        except Exception as e:
            print(f"❌ 클라이언트 초기화 실패: {e}")
            traceback.print_exc()
            raise
    
    def extract_text_from_pdf(self, pdf_file: bytes) -> str:
        """PDF 파일에서 텍스트 추출"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file))
            text = ""
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            print(f"✅ PDF 텍스트 추출 완료 - {len(pdf_reader.pages)}페이지")
            return text.strip()
            
        except Exception as e:
            print(f"❌ PDF 텍스트 추출 실패: {e}")
            raise
    
    def truncate_text_for_analysis(self, text: str, max_chars: int = 3000) -> str:
        """GPT 분석용 텍스트 길이 제한"""
        if len(text) <= max_chars:
            return text
        
        # 문장 단위로 자르기 (더 자연스러운 분석을 위해)
        truncated = text[:max_chars]
        
        # 마지막 완전한 문장을 찾기
        last_period = truncated.rfind('.')
        last_exclamation = truncated.rfind('!')
        last_question = truncated.rfind('?')
        
        last_sentence_end = max(last_period, last_exclamation, last_question)
        
        if last_sentence_end > max_chars * 0.8:  # 80% 이상이면 문장 끝에서 자르기
            return truncated[:last_sentence_end + 1]
        else:
            return truncated + "..."
    
    def split_text_into_chunks(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """텍스트를 청크로 분할"""
        try:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
            
            chunks = splitter.split_text(text)
            print(f"✅ 텍스트 청크 분할 완료 - {len(chunks)}개 청크")
            return chunks
            
        except Exception as e:
            print(f"❌ 텍스트 청크 분할 실패: {e}")
            raise
    
    def analyze_content_with_gpt(self, text: str) -> Dict[str, Any]:
        """GPT를 사용하여 콘텐츠 분석"""
        try:
            # 텍스트 길이 제한 (GPT-3.5-turbo 토큰 제한 고려)
            text = self.truncate_text_for_analysis(text, max_chars=3000)
            
            prompt = f"""
다음 텍스트를 분석하여 다음 정보를 JSON 형태로 반환해주세요:

텍스트:
{text}

분석해야 할 항목:
1. 제목 (title): 텍스트의 주요 제목이나 주제
2. 요약 (summary): 텍스트의 핵심 내용을 200자 이내로 요약
3. 주요 키워드 (keywords): 텍스트에서 추출한 주요 키워드 5-10개
4. 카테고리 (category): 텍스트의 주제 분야 (예: 기술, 과학, 비즈니스, 교육 등)
5. 중요도 (importance): 1-10 점수로 텍스트의 중요도 평가

JSON 형태로만 응답해주세요.
"""
            
            response = self.openai_client.chat.completions.create(
                model=self.llm_model_name,
                messages=[
                    {"role": "system", "content": "당신은 텍스트 분석 전문가입니다. 요청된 정보만 JSON 형태로 정확히 반환해주세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # JSON 응답 파싱
            content = response.choices[0].message.content
            import json
            try:
                # JSON 부분만 추출
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1]
                
                analysis_result = json.loads(content.strip())
                print("✅ GPT 분석 완료")
                return analysis_result
                
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본 구조 반환
                print("⚠️ JSON 파싱 실패, 기본 구조 사용")
                return {
                    "title": "분석 실패",
                    "summary": text[:200] + "..." if len(text) > 200 else text,
                    "keywords": ["분석", "실패"],
                    "category": "기타",
                    "importance": 5
                }
                
        except Exception as e:
            print(f"❌ GPT 분석 실패: {e}")
            # 기본 구조 반환
            return {
                "title": "분석 오류",
                "summary": text[:200] + "..." if len(text) > 200 else text,
                "keywords": ["오류"],
                "category": "기타",
                "importance": 1
            }
    
    def generate_embedding(self, text: str) -> List[float]:
        """텍스트 임베딩 생성"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model_name,
                input=text
            )
            embedding = response.data[0].embedding
            print(f"✅ 임베딩 생성 완료 - 벡터 크기: {len(embedding)}")
            return embedding
            
        except Exception as e:
            print(f"❌ 임베딩 생성 실패: {e}")
            raise
    
    def generate_keyword_embeddings(self, keywords: List[str]) -> List[List[float]]:
        """키워드별 개별 임베딩 생성"""
        try:
            if not keywords:
                return []
            
            response = self.openai_client.embeddings.create(
                model=self.embedding_model_name,
                input=keywords
            )
            
            embeddings = [item.embedding for item in response.data]
            print(f"✅ 키워드 임베딩 생성 완료 - {len(embeddings)}개 키워드")
            return embeddings
            
        except Exception as e:
            print(f"❌ 키워드 임베딩 생성 실패: {e}")
            return []
    
    def save_to_mongodb(self, pdf_data: Dict[str, Any]) -> bool:
        """MongoDB에 PDF 데이터 저장"""
        try:
            # MongoDB에 저장
            result = self.articles_collection.insert_one(pdf_data)
            print(f"✅ MongoDB 저장 완료 - ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            print(f"❌ MongoDB 저장 실패: {e}")
            return False
    
    def save_to_pinecone(self, pdf_data: Dict[str, Any]) -> bool:
        """Pinecone DB에 벡터 저장"""
        try:
            if not pdf_data.get("embedding"):
                print(f"⚠️ 임베딩이 없어 Pinecone 저장을 건너뜁니다")
                return False
            
            # Pinecone에 저장할 데이터 구성
            vectors_to_upsert = [{
                "id": pdf_data["ID"],
                "values": pdf_data["embedding"],
                "metadata": {
                    "title": pdf_data.get("title", ""),
                    "source": "pdf_upload",
                    "category": pdf_data.get("category", "기타"),
                    "uploaded_at": pdf_data["uploaded_at"]
                }
            }]
            
            self.pinecone_manager.get_index().upsert(vectors=vectors_to_upsert)
            print(f"✅ Pinecone 저장 완료 - ID: {pdf_data['ID']}")
            return True
            
        except Exception as e:
            print(f"❌ Pinecone 저장 실패: {e}")
            return False
    
    def process_pdf(self, pdf_file: bytes, filename: str) -> Dict[str, Any]:
        """PDF 파일 처리 및 분석"""
        start_time = datetime.now()
        
        try:
            # 1. PDF 텍스트 추출
            full_text = self.extract_text_from_pdf(pdf_file)
            if not full_text:
                return {"success": False, "error": "PDF에서 텍스트를 추출할 수 없습니다"}

            # 2. 텍스트 청크 분할
            chunks = self.split_text_into_chunks(full_text, chunk_size=1000, chunk_overlap=200)
            if not chunks:
                return {"success": False, "error": "텍스트를 청크로 분할할 수 없습니다"}

            # 3. 첫 번째 청크로 전체 내용 분석 (제목, 요약 등)
            analysis_result = self.analyze_content_with_gpt(chunks[0])

            # 4. 고유 ID 생성
            pdf_hash = hashlib.sha256(pdf_file).hexdigest()
            pdf_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, pdf_hash))

            # 5. 모든 청크 임베딩 및 Pinecone 저장 준비
            pinecone_vectors = []
            for i, chunk in enumerate(chunks):
                chunk_id = f"{pdf_id}-{i}"
                embedding = self.generate_embedding(chunk)
                
                pinecone_vectors.append({
                    "id": chunk_id,
                    "values": embedding,
                    "metadata": {
                        "pdf_id": pdf_id,
                        "chunk_index": i,
                        "text": chunk,
                        "title": analysis_result.get("title", filename),
                        "category": analysis_result.get("category", "기타"),
                        "source": "pdf_upload"
                    }
                })

            # 6. Pinecone에 일괄 업로드
            if pinecone_vectors:
                self.pinecone_manager.get_index().upsert(vectors=pinecone_vectors)
                print(f"✅ Pinecone에 {len(chunks)}개 청크 저장 완료")
                pinecone_saved = True
            else:
                pinecone_saved = False

            # 7. MongoDB에 저장할 최종 데이터 구조
            final_data = {
                "ID": pdf_id,
                "source": "pdf_upload",
                "filename": filename,
                "title": analysis_result.get("title", filename),
                "summary": analysis_result.get("summary", ""),
                "keywords": analysis_result.get("keywords", []),
                "category": analysis_result.get("category", "기타"),
                "importance": analysis_result.get("importance", 5),
                "full_text_hash": pdf_hash,
                "uploaded_at": datetime.now().isoformat(),
                "processed_at": datetime.now().isoformat(),
                "file_size": len(pdf_file),
                "chunk_count": len(chunks),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
            }

            # 8. MongoDB에 저장
            mongo_saved = self.save_to_mongodb(final_data)

            return {
                "success": True,
                "pdf_id": pdf_id,
                "title": final_data["title"],
                "summary": final_data["summary"],
                "mongo_saved": mongo_saved,
                "pinecone_saved": pinecone_saved,
                "chunk_count": len(chunks),
                "file_size": len(pdf_file)
            }

        except Exception as e:
            print(f"❌ PDF 처리 중 심각한 오류 발생: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def delete_pdf(self, pdf_id: str) -> bool:
        """PDF 및 관련 벡터 삭제"""
        try:
            # MongoDB에서 문서 정보 가져오기 (청크 개수 등)
            pdf_doc = self.articles_collection.find_one({"ID": pdf_id})
            
            if not pdf_doc:
                print(f"MongoDB에서 PDF ID {pdf_id}를 찾을 수 없습니다.")
                return False
            
            # Pinecone에서 모든 관련 청크 삭제
            chunk_count = pdf_doc.get("chunk_count", 0)
            if chunk_count > 0:
                chunk_ids = [f"{pdf_id}-{i}" for i in range(chunk_count)]
                self.pinecone_manager.get_index().delete(ids=chunk_ids)
                print(f"Pinecone에서 {len(chunk_ids)}개 청크 삭제 완료")

            # MongoDB에서 문서 삭제
            self.articles_collection.delete_one({"ID": pdf_id})
            print(f"MongoDB에서 PDF ID {pdf_id} 삭제 완료")
            
            return True
            
        except Exception as e:
            print(f"❌ PDF 삭제 중 오류: {e}")
            return False

# 이 클래스의 인스턴스를 직접 실행하여 테스트할 수 있습니다.
if __name__ == '__main__':
    # 테스트용 코드
    try:
        processor = PDFProcessor()
        
        # 테스트 PDF 파일 경로 (프로젝트 루트 기준)
        test_pdf_path = os.path.join(_project_root, "test_documents", "sample.pdf")
        
        if not os.path.exists(test_pdf_path):
            print(f"테스트 파일 없음: {test_pdf_path}")
        else:
            with open(test_pdf_path, "rb") as f:
                pdf_bytes = f.read()
                filename = os.path.basename(test_pdf_path)
                
                print(f"--- PDF 처리 테스트 시작: {filename} ---")
                result = processor.process_pdf(pdf_bytes, filename)
                print("\n--- 처리 결과 ---")
                import json
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                if result.get("success"):
                    print("\n--- 삭제 테스트 시작 ---")
                    delete_result = processor.delete_pdf(result["pdf_id"])
                    print(f"삭제 성공: {delete_result}")

    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")
        traceback.print_exc() 