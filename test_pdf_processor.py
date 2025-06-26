"""
PDF 프로세서 테스트 스크립트
"""

import os
import sys
import requests
from pathlib import Path

def test_pdf_processor():
    """PDF 프로세서 테스트"""
    print("🧪 PDF 프로세서 테스트 시작")
    
    # API 서버 URL
    base_url = "http://localhost:8001"
    
    # 1. 헬스 체크
    print("\n1. 헬스 체크 테스트")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ 서버가 정상적으로 실행 중입니다")
            print(f"   상태: {response.json()}")
        else:
            print(f"❌ 서버 상태 확인 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        print("   PDF API 서버가 실행 중인지 확인해주세요 (python src/api/pdf_api.py)")
        return False
    
    # 2. PDF 목록 조회
    print("\n2. PDF 목록 조회 테스트")
    try:
        response = requests.get(f"{base_url}/list-pdfs")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ PDF 목록 조회 성공")
            print(f"   총 PDF 개수: {data['total_count']}")
            if data['pdfs']:
                print("   최근 PDF들:")
                for pdf in data['pdfs'][:3]:
                    print(f"     - {pdf['title']} ({pdf['category']})")
            else:
                print("   저장된 PDF가 없습니다")
        else:
            print(f"❌ PDF 목록 조회 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ PDF 목록 조회 중 오류: {e}")
    
    # 3. PDF 검색 테스트
    print("\n3. PDF 검색 테스트")
    try:
        response = requests.get(f"{base_url}/search-pdfs", params={"query": "기술", "limit": 5})
        if response.status_code == 200:
            data = response.json()
            print(f"✅ PDF 검색 성공")
            print(f"   검색어: {data['query']}")
            print(f"   검색 결과: {data['total_found']}개")
            if data['results']:
                print("   검색 결과:")
                for result in data['results'][:3]:
                    print(f"     - {result['title']} (유사도: {result.get('similarity_score', 0):.3f})")
            else:
                print("   검색 결과가 없습니다")
        else:
            print(f"❌ PDF 검색 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ PDF 검색 중 오류: {e}")
    
    print("\n✅ PDF 프로세서 테스트 완료")
    return True

def test_pdf_upload():
    """PDF 업로드 테스트"""
    print("\n📤 PDF 업로드 테스트")
    
    # 테스트 PDF 파일 경로
    test_pdf_path = "test.pdf"
    
    if not os.path.exists(test_pdf_path):
        print(f"❌ 테스트 PDF 파일이 없습니다: {test_pdf_path}")
        print("   테스트용 PDF 파일을 생성해주세요")
        return False
    
    base_url = "http://localhost:8001"
    
    try:
        # PDF 파일 업로드
        with open(test_pdf_path, "rb") as f:
            files = {"file": (test_pdf_path, f, "application/pdf")}
            response = requests.post(f"{base_url}/upload-pdf", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ PDF 업로드 성공")
            print(f"   PDF ID: {data['pdf_id']}")
            print(f"   제목: {data['title']}")
            print(f"   요약: {data['summary'][:100]}...")
            print(f"   MongoDB 저장: {'성공' if data['mongo_saved'] else '실패'}")
            print(f"   Pinecone 저장: {'성공' if data['pinecone_saved'] else '실패'}")
            print(f"   청크 수: {data['chunk_count']}")
            print(f"   파일 크기: {data['file_size']} bytes")
            return True
        else:
            print(f"❌ PDF 업로드 실패: {response.status_code}")
            print(f"   오류: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ PDF 업로드 중 오류: {e}")
        return False

def create_test_pdf():
    """테스트용 PDF 파일 생성"""
    print("\n📄 테스트 PDF 파일 생성")
    
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        test_pdf_path = "test.pdf"
        
        # 간단한 PDF 생성
        c = canvas.Canvas(test_pdf_path, pagesize=letter)
        c.drawString(100, 750, "테스트 PDF 문서")
        c.drawString(100, 720, "이 문서는 PDF 프로세서 테스트를 위해 생성되었습니다.")
        c.drawString(100, 690, "이 문서는 인공지능과 머신러닝 기술에 대한 내용을 포함합니다.")
        c.drawString(100, 660, "PDF 처리 시스템이 정상적으로 작동하는지 확인하기 위한 테스트 문서입니다.")
        c.drawString(100, 630, "이 문서는 MongoDB와 Pinecone DB에 저장되어 검색 가능합니다.")
        c.drawString(100, 600, "GPT를 통한 자동 분석이 수행되어 제목, 요약, 키워드가 추출됩니다.")
        c.drawString(100, 570, "벡터 임베딩이 생성되어 유사도 기반 검색이 가능합니다.")
        c.drawString(100, 540, "이 시스템은 문서 관리와 지식 검색을 위한 강력한 도구입니다.")
        c.save()
        
        print(f"✅ 테스트 PDF 파일 생성 완료: {test_pdf_path}")
        return True
        
    except ImportError:
        print("❌ reportlab 라이브러리가 설치되지 않았습니다")
        print("   pip install reportlab 명령으로 설치해주세요")
        return False
    except Exception as e:
        print(f"❌ 테스트 PDF 생성 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 PDF 프로세서 통합 테스트")
    print("=" * 50)
    
    # 1. 테스트 PDF 파일 생성
    if not os.path.exists("test.pdf"):
        if not create_test_pdf():
            return
    
    # 2. PDF 프로세서 테스트
    if not test_pdf_processor():
        return
    
    # 3. PDF 업로드 테스트
    test_pdf_upload()
    
    print("\n" + "=" * 50)
    print("🎉 모든 테스트 완료!")
    print("\n사용법:")
    print("1. PDF API 서버 실행: python src/api/pdf_api.py")
    print("2. 브라우저에서 http://localhost:8001/docs 접속하여 API 문서 확인")
    print("3. PDF 파일 업로드 및 검색 테스트")

if __name__ == "__main__":
    main() 