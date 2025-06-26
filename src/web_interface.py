"""
PDF 처리 웹 인터페이스
Streamlit을 사용한 간단한 웹 UI
"""

import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import os

# 페이지 설정
st.set_page_config(
    page_title="PDF 프로세서",
    page_icon="📄",
    layout="wide"
)

# API 서버 URL
API_BASE_URL = "http://localhost:8001"

def check_server_health():
    """서버 상태 확인"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def upload_pdf(file):
    """PDF 파일 업로드"""
    try:
        files = {"file": file}
        response = requests.post(f"{API_BASE_URL}/upload-pdf", files=files)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"업로드 실패: {response.text}")
            return None
    except Exception as e:
        st.error(f"업로드 중 오류: {str(e)}")
        return None

def get_pdf_list():
    """PDF 목록 조회"""
    try:
        response = requests.get(f"{API_BASE_URL}/list-pdfs")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"목록 조회 실패: {response.text}")
            return None
    except Exception as e:
        st.error(f"목록 조회 중 오류: {str(e)}")
        return None

def search_pdfs(query, limit=10):
    """PDF 검색"""
    try:
        params = {"query": query, "limit": limit}
        response = requests.get(f"{API_BASE_URL}/search-pdfs", params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"검색 실패: {response.text}")
            return None
    except Exception as e:
        st.error(f"검색 중 오류: {str(e)}")
        return None

def delete_pdf(pdf_id):
    """PDF 삭제"""
    try:
        response = requests.delete(f"{API_BASE_URL}/pdf/{pdf_id}")
        return response.status_code == 200
    except Exception as e:
        st.error(f"삭제 중 오류: {str(e)}")
        return False

# 메인 앱
def main():
    st.title("📄 PDF 프로세서")
    st.markdown("PDF 파일을 업로드하고 GPT로 분석하여 MongoDB와 Pinecone DB에 저장하는 시스템")
    
    # 서버 상태 확인
    if not check_server_health():
        st.error("❌ PDF API 서버에 연결할 수 없습니다.")
        st.info("서버를 실행하려면: `python src/api/pdf_api.py`")
        return
    
    st.success("✅ PDF API 서버에 연결되었습니다.")
    
    # 사이드바 메뉴
    menu = st.sidebar.selectbox(
        "메뉴 선택",
        ["📤 PDF 업로드", "📋 PDF 목록", "🔍 PDF 검색", "📊 통계"]
    )
    
    if menu == "📤 PDF 업로드":
        st.header("PDF 파일 업로드")
        
        uploaded_file = st.file_uploader(
            "PDF 파일을 선택하세요",
            type=['pdf'],
            help="최대 50MB까지 업로드 가능합니다"
        )
        
        if uploaded_file is not None:
            # 파일 정보 표시
            file_size = len(uploaded_file.getvalue()) / (1024 * 1024)  # MB
            st.info(f"파일명: {uploaded_file.name}")
            st.info(f"파일 크기: {file_size:.2f} MB")
            
            if st.button("📤 업로드 및 처리"):
                with st.spinner("PDF를 처리하고 있습니다..."):
                    result = upload_pdf(uploaded_file)
                    
                    if result and result.get("success"):
                        st.success("✅ PDF 업로드 및 처리 완료!")
                        
                        # 결과 표시
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("📄 문서 정보")
                            st.write(f"**제목:** {result['title']}")
                            st.write(f"**요약:** {result['summary']}")
                            st.write(f"**파일 크기:** {result['file_size']:,} bytes")
                        
                        with col2:
                            st.subheader("💾 저장 상태")
                            st.write(f"**MongoDB:** {'✅ 성공' if result['mongo_saved'] else '❌ 실패'}")
                            st.write(f"**Pinecone:** {'✅ 성공' if result['pinecone_saved'] else '❌ 실패'}")
                            st.write(f"**PDF ID:** {result['pdf_id']}")
                    
                    elif result:
                        st.error(f"❌ 처리 실패: {result.get('error', '알 수 없는 오류')}")
    
    elif menu == "📋 PDF 목록":
        st.header("저장된 PDF 목록")
        
        # 필터 옵션
        col1, col2 = st.columns(2)
        with col1:
            limit = st.slider("표시 개수", 5, 50, 20)
        
        with col2:
            st.write("")  # 빈 공간
        
        if st.button("🔄 목록 새로고침"):
            with st.spinner("목록을 불러오는 중..."):
                data = get_pdf_list()
                
                if data and data.get("pdfs"):
                    pdfs = data["pdfs"]
                    
                    st.success(f"✅ {len(pdfs)}개의 PDF를 찾았습니다.")
                    
                    # 데이터프레임으로 표시
                    if pdfs:
                        df_data = []
                        for pdf in pdfs:
                            df_data.append({
                                "제목": pdf.get("title", "제목 없음"),
                                "요약": pdf.get("summary", "")[:100] + "..." if len(pdf.get("summary", "")) > 100 else pdf.get("summary", ""),
                                "키워드": ", ".join(pdf.get("llm_internal_keywords", [])[:3]),
                                "업로드 날짜": pdf.get("published_at", ""),
                                "PDF ID": pdf.get("ID", "")
                            })
                        
                        df = pd.DataFrame(df_data)
                        st.dataframe(df, use_container_width=True)
                        
                        # 삭제 기능
                        st.subheader("🗑️ PDF 삭제")
                        pdf_to_delete = st.selectbox(
                            "삭제할 PDF 선택",
                            options=[pdf["제목"] for pdf in df_data],
                            key="delete_select"
                        )
                        
                        if st.button("삭제"):
                            selected_pdf = next(pdf for pdf in df_data if pdf["제목"] == pdf_to_delete)
                            if delete_pdf(selected_pdf["PDF ID"]):
                                st.success("✅ PDF 삭제 완료")
                                st.rerun()
                            else:
                                st.error("❌ PDF 삭제 실패")
                    else:
                        st.info("표시할 PDF가 없습니다.")
                else:
                    st.info("저장된 PDF가 없습니다.")
    
    elif menu == "🔍 PDF 검색":
        st.header("PDF 내용 검색")
        
        # 검색 옵션
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input("검색어를 입력하세요", placeholder="예: 인공지능, 머신러닝, 기술...")
        
        with col2:
            search_limit = st.number_input("검색 결과 수", min_value=1, max_value=20, value=10)
        
        if st.button("🔍 검색"):
            if search_query.strip():
                with st.spinner("검색 중..."):
                    results = search_pdfs(search_query, search_limit)
                    
                    if results and results.get("results"):
                        st.success(f"✅ '{search_query}'에 대한 검색 결과: {len(results['results'])}개")
                        
                        for i, result in enumerate(results["results"], 1):
                            with st.expander(f"{i}. {result.get('title', '제목 없음')} (유사도: {result.get('similarity_score', 0):.3f})"):
                                st.write(f"**요약:** {result.get('summary', '요약 없음')}")
                                st.write(f"**카테고리:** {result.get('category', '기타')}")
                                st.write(f"**중요도:** {result.get('importance', 5)}/10")
                                st.write(f"**키워드:** {', '.join(result.get('keywords', []))}")
                                st.write(f"**업로드 날짜:** {result.get('uploaded_at', '')}")
                                st.write(f"**PDF ID:** {result.get('ID', '')}")
                    else:
                        st.info("검색 결과가 없습니다.")
            else:
                st.warning("검색어를 입력해주세요.")
    
    elif menu == "📊 통계":
        st.header("시스템 통계")
        
        # 서버 상태
        st.subheader("🖥️ 서버 상태")
        health_response = requests.get(f"{API_BASE_URL}/health")
        if health_response.status_code == 200:
            health_data = health_response.json()
            st.success("✅ 서버 정상 작동")
            st.write(f"**MongoDB:** {health_data.get('mongodb', 'unknown')}")
            st.write(f"**Pinecone:** {health_data.get('pinecone', 'unknown')}")
            st.write(f"**마지막 체크:** {health_data.get('timestamp', '')}")
        else:
            st.error("❌ 서버 연결 실패")
        
        # PDF 통계
        st.subheader("📄 PDF 통계")
        pdf_list = get_pdf_list()
        if pdf_list and pdf_list.get("pdfs"):
            pdfs = pdf_list["pdfs"]
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("총 PDF 수", len(pdfs))
            
            with col2:
                total_keywords = sum(len(pdf.get("llm_internal_keywords", [])) for pdf in pdfs)
                st.metric("총 키워드 수", total_keywords)
            
            with col3:
                avg_keywords = total_keywords / len(pdfs) if pdfs else 0
                st.metric("평균 키워드 수", f"{avg_keywords:.1f}")
            
            with col4:
                st.metric("처리 완료", len(pdfs))
            
            # 키워드별 분포
            st.subheader("📊 키워드 분포")
            all_keywords = []
            for pdf in pdfs:
                all_keywords.extend(pdf.get("llm_internal_keywords", []))
            
            if all_keywords:
                keyword_counts = {}
                for keyword in all_keywords:
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
                
                # 상위 10개 키워드만 표시
                top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                keyword_df = pd.DataFrame(top_keywords, columns=["키워드", "개수"])
                st.bar_chart(keyword_df.set_index("키워드"))
            else:
                st.info("키워드 데이터가 없습니다.")
        else:
            st.info("통계 데이터가 없습니다.")

if __name__ == "__main__":
    main() 