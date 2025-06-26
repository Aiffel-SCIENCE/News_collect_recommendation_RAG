import os
from pinecone import Pinecone as PineconeClient
from typing import Optional
import sys

# 프로젝트 루트 계산
_current_file_path = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file_path)))

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.config_loader.settings import SETTINGS

class PineconeDB:
    def __init__(self):
        self.api_key = SETTINGS.get("PINECONE_API_KEY") #
        self.index_name = SETTINGS.get("PINECONE_INDEX_NAME") #
        
        if not all([self.api_key, self.index_name]):
            print("PineconeDB: API 키 또는 인덱스 이름이 설정(config.yaml)되지 않았습니다.")
            raise ValueError("PineconeDB: API 키 또는 인덱스 이름이 설정(config.yaml)되지 않았습니다.")

        try:
            self.pinecone_client = PineconeClient(api_key=self.api_key)
            print(f"✅ PineconeDB: Pinecone 클라이언트 초기화 성공.")
            self.index = None
            self._connect_to_index()
        except Exception as e:
            print(f"PineconeDB: Pinecone 클라이언트 초기화 중 치명적 오류: {e}")
            raise

    def _connect_to_index(self):
        """Pinecone 인덱스에 연결하는 헬퍼 메서드입니다."""
        try:
            existing_indexes = [index_spec.name for index_spec in self.pinecone_client.list_indexes()]
            print(f"ℹPineconeDB: 사용 가능한 인덱스 목록: {existing_indexes}")

            if self.index_name not in existing_indexes:
                error_msg = f"Pinecone 인덱스 '{self.index_name}'를 찾을 수 없습니다. 사용 가능한 인덱스: {existing_indexes}. Pinecone에서 미리 생성해주세요."
                print(f"PineconeDB: {error_msg}")
                raise NameError(error_msg)

            self.index = self.pinecone_client.Index(self.index_name)
            print(f"PineconeDB: 인덱스 '{self.index_name}'에 성공적으로 연결되었습니다.")
            
            index_stats = self.index.describe_index_stats()
            print(f"PineconeDB: 인덱스 '{self.index_name}' 상태: {index_stats}")
        except Exception as e:
            self.index = None
            print(f"PineconeDB: 인덱스 '{self.index_name}' 연결 중 오류: {e}")
            raise

    def get_index(self):
        """연결된 Pinecone 인덱스 객체를 반환합니다. 연결되지 않은 경우 연결을 시도합니다."""
        if self.index is None:
            print("ℹ️ PineconeDB: 인덱스가 연결되지 않아 재연결을 시도합니다.")
            self._connect_to_index()
        
        if self.index is None:
            error_msg = f"PineconeDB: 인덱스 '{self.index_name}'에 최종적으로 연결할 수 없습니다."
            print(error_msg)
            raise ConnectionError(error_msg)
        return self.index

    # def query_vector(self, vector: list, top_k: int = 1, include_metadata=True): # 기존 코드
    def query_vector(self, vector: list, top_k: int = 1, include_metadata=True, filter: Optional[dict] = None):
        """
        주어진 벡터와 가장 유사한 벡터를 Pinecone 인덱스에서 검색합니다.
        필터 조건을 추가할 수 있습니다.
        """
        idx = self.get_index()
        if not vector:
            print("PineconeDB: 내용이 없는 빈 벡터는 쿼리할 수 없습니다. 빈 결과를 반환합니다.")
            return None
        
        try:
            query_params = {
                "vector": vector,
                "top_k": top_k,
                "include_metadata": include_metadata
            }
            if filter: # filter 인자가 제공되면 쿼리 파라미터에 추가
                query_params["filter"] = filter
            
            print(f"PineconeDB: 벡터 쿼리 중 (top_k={top_k}, filter={filter})...") # 로그에 filter 정보 추가
            query_response = idx.query(**query_params) # 수정된 query_params 사용
            print(f"PineconeDB: 벡터 쿼리 성공.")
            return query_response.get('matches', [])
        except Exception as e:
            print(f"PineconeDB: 벡터 쿼리 중 오류 발생: {e}")
            raise

    def upsert_vector(self, vector_id: str, vector: list, metadata: dict = None):
        """
        벡터를 Pinecone 인덱스에 업서트(업데이트 또는 삽입)합니다.
        """
        idx = self.get_index()
        if not vector_id or not vector:
            print("PineconeDB: 벡터 ID 또는 벡터 데이터가 없어 업서트할 수 없습니다. 작업을 건너뜁니다.")
            return False
        
        vectors_to_upsert = [(vector_id, vector, metadata or {})]
        
        try:
            print(f"PineconeDB: 벡터 ID '{vector_id}' 업서트 중...")
            upsert_response = idx.upsert(vectors=vectors_to_upsert)
            upserted_count = getattr(upsert_response, 'upserted_count', 0)
            
            if upserted_count > 0:
                print(f"PineconeDB: 벡터 ID '{vector_id}' 업서트 성공 (개수: {upserted_count}).")
                return True
            else:
                print(f"PineconeDB: 벡터 ID '{vector_id}' 업서트 응답에 'upserted_count'가 0 또는 없습니다: {upsert_response}")
                return False
        except Exception as e:
            print(f"PineconeDB: 벡터 ID '{vector_id}' 업서트 중 오류 발생: {e}")
            raise

if __name__ == '__main__':
    print("--- PineconeDB 직접 실행 테스트 ---")
    try:
        pinecone_manager = PineconeDB()


        print("PineconeDB 모듈 테스트 완료 (기본 초기화 및 인덱스 연결).")
    except Exception as e:
        print(f"PineconeDB 테스트 중 오류: {e}")
