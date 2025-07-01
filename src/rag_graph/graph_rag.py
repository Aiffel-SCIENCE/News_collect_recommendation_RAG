import os
from typing import TypedDict, List, Optional, Tuple
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from src.config_loader.settings import SETTINGS
from src.db.vector_db import PineconeDB
from ..services.web_search import perform_web_search
from ..services.advanced_retrieval import AdvancedRetrieval
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM, AutoModelForSequenceClassification
import torch
from collections import defaultdict
from supabase import create_client, Client

# --- 프로젝트 경로 설정 ---
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    # RAG용 OpenAI 모델
    rag_model = SETTINGS.get('OPENAI_RAG_MODEL', 'gpt-4.1')
    llm = ChatOpenAI(
        model_name=rag_model,
        temperature=0,
        openai_api_key=SETTINGS['OPENAI_API_KEY']
    )

    # Advanced Retrieval 인스턴스
    advanced_retrieval = AdvancedRetrieval()

    # Meerkat SLLM 셋업 (효율적인 로딩)
    meerkat_ckpt = 'dmis-lab/meerkat-7b-v1.0'
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    meerkat_tokenizer = AutoTokenizer.from_pretrained(meerkat_ckpt)
    meerkat_model = AutoModelForCausalLM.from_pretrained(
        meerkat_ckpt,
        torch_dtype=torch.bfloat16
    ).to(device)

    meerkat_pipe = pipeline(
        'text-generation',
        model=meerkat_model,
        tokenizer=meerkat_tokenizer,
        device=0 if torch.cuda.is_available() else -1
    )
    
    # Qwen3-Reranker 셋업 (Sequence Classification)
    qwen_tokenizer = AutoTokenizer.from_pretrained('Qwen/Qwen3-Reranker-0.6B')
    qwen_model = AutoModelForSequenceClassification.from_pretrained(
        'Qwen/Qwen3-Reranker-0.6B'
    ).to(device)
except Exception as e:
    raise RuntimeError(f"모델 초기화 오류: {e}")

# --- Supabase 초기화 ---
supabase: Optional[Client] = None
if SETTINGS.get('SUPABASE_URL') and SETTINGS.get('SUPABASE_ANON_KEY'):
    try:
        supabase = create_client(
            SETTINGS['SUPABASE_URL'], SETTINGS['SUPABASE_ANON_KEY']
        )
    except Exception:
        supabase = None

# --- Pinecone DB 초기화 ---
vector_db = PineconeDB()

# --- 상태 타입 정의 ---
class GraphState(TypedDict, total=False):
    user_id: str
    query: str
    chat_id: Optional[str]
    chat_history: List[BaseMessage]
    rewritten_query: str
    web_chunks: List[str]
    meerkat_chunks: List[str]
    db_chunks: List[str]
    reranked_chunks: List[str]
    source_info: List[Tuple[str, str]]  # (chunk_text, source_title) 튜플 리스트
    final_answer: str

# --- 청크 추출 유틸 ---
def extract_chunks(texts: List[str], max_chunks: int, chunk_size: int = 2000, overlap: int = 100) -> List[str]:
    """
    2000자 단위, overlap 적용하여 재귀적 청크 분할
    """
    chunks: List[str] = []
    for text in texts:
        start = 0
        while start < len(text) and len(chunks) < max_chunks:
            end = start + chunk_size
            chunks.append(text[start:end])
            start += (chunk_size - overlap)
    return chunks

# --- Qwen3-Reranker 점수 함수 ---
def score_with_qwen3(query: str, passage: str) -> float:
    inst = f"QUERY: {query}  PASSAGE: {passage}"
    inputs = qwen_tokenizer(
        inst, return_tensors='pt', truncation=True, max_length=512
    ).to(device)
    with torch.no_grad():
        logits = qwen_model(**inputs).logits
        # 라벨 1이 관련도 긍정 클래스
        score = torch.softmax(logits, dim=-1)[0,1].item()
    return score

# --- 노드 함수 정의 ---

def retrieve_from_chat_history(state: GraphState) -> dict:
    return {"chat_history": [], "source_info": []}


def rewrite_query(state: GraphState) -> dict:
    original_query = state.get('query', '')
    # LLM에게 쿼리 재작성 필요성 및 재작성 결과 요청
    prompt = (
        "아래 사용자의 검색 쿼리를 더 명확하고 정보 검색에 적합하게 재작성할 필요가 있는지 판단하세요. "
        "만약 재작성할 필요가 있다면, 재작성된 쿼리만 출력하세요. 필요 없다면 'NO_REWRITE'만 출력하세요.\n"
        f"사용자 쿼리: {original_query}"
    )
    resp = llm.invoke(prompt)
    rewritten = resp.content.strip()
    if rewritten == 'NO_REWRITE':
        rewritten = original_query
    return {"rewritten_query": rewritten}


def retrieve_web_chunks(state: GraphState) -> dict:
    query = state['rewritten_query']
    results = perform_web_search(query, max_results=5)
    
    chunks = []
    source_info = []
    
    for result in results:
        content = result.get('content', '')
        title = result.get('title', '웹 검색 결과')
        # 제목을 30자로 제한
        title_short = title[:30] + ('...' if len(title) > 30 else '')
        
        # 콘텐츠를 청크로 분할
        text_chunks = extract_chunks([content], max_chunks=2, chunk_size=2000, overlap=100)
        
        for chunk in text_chunks:
            chunks.append(chunk)
            source_info.append((chunk, f"웹: {title_short}"))
    
    return {"web_chunks": chunks, "source_info": source_info}


def retrieve_meerkat_chunks(state: GraphState) -> dict:
    messages = [
        {
            "role": "system",
            "content": "You are a helpful doctor or healthcare professional."
        },
        {
            "role": "user",
            "content": state['rewritten_query']
        }
    ]

    encodeds = meerkat_tokenizer.apply_chat_template(
        messages, return_tensors="pt"
    ).to(device)

    with torch.no_grad():
        generated_ids = meerkat_model.generate(
            encodeds,
            max_new_tokens=512,
            do_sample=True,
            pad_token_id=meerkat_tokenizer.eos_token_id
        )

    decoded = meerkat_tokenizer.batch_decode(generated_ids, skip_special_tokens=True)
    generated = decoded[0]
    print("✅ Meerkat 응답:", generated)

    chunks = extract_chunks([generated], max_chunks=4)
    
    # 기존 source_info 가져오기
    existing_source_info = state.get('source_info', [])
    meerkat_source_info = [(chunk, "AI: Meerkat 의료 전문가 모델") for chunk in chunks]
    
    return {"meerkat_chunks": chunks, "source_info": existing_source_info + meerkat_source_info}


def retrieve_db_chunks(state: GraphState) -> dict:
    docs = advanced_retrieval.advanced_retrieve(state['rewritten_query'])
    
    chunks = []
    existing_source_info = state.get('source_info', [])
    db_source_info = []
    
    for i, doc in enumerate(docs):
        content = doc['content']
        # 문서 제목이나 파일명 추출 (메타데이터에서)
        title = doc.get('title', doc.get('filename', f'문서 {i+1}'))
        title_short = title[:30] + ('...' if len(title) > 30 else '')
        
        text_chunks = extract_chunks([content], max_chunks=2, chunk_size=2000, overlap=100)
        
        for chunk in text_chunks:
            chunks.append(chunk)
            db_source_info.append((chunk, f"DB: {title_short}"))
    
    return {"db_chunks": chunks, "source_info": existing_source_info + db_source_info}


def rerank_chunks(state: GraphState) -> dict:
    merged: List[Tuple[str,int,str]] = []
    for source in ['web_chunks', 'meerkat_chunks', 'db_chunks']:
        for idx, txt in enumerate(state.get(source, [])):
            merged.append((source, idx, txt))
    
    # 점수 부여
    scored: List[Tuple[str,int,float,str]] = []
    for src, idx, txt in merged:
        sc = score_with_qwen3(state['rewritten_query'], txt)
        scored.append((src, idx, sc, txt))
    
    # doc 단위 그룹화
    group = defaultdict(list)
    for src, idx, sc, txt in scored:
        group[src].append((idx, sc, txt))
    
    # 각 doc 최고 score 집계
    doc_scores = {src: max(ch[1] for ch in lst) for src, lst in group.items()}
    
    # doc 순서 정렬
    sorted_docs = sorted(group.items(), key=lambda kv: doc_scores.get(kv[0], 0), reverse=True)
    
    final_chunks: List[str] = []
    reranked_source_info: List[Tuple[str, str]] = []
    
    # source_info에서 청크에 해당하는 출처 정보 찾기
    source_info_dict = {chunk: source for chunk, source in state.get('source_info', [])}
    
    for src, lst in sorted_docs:
        for idx, _, txt in sorted(lst, key=lambda x: x[0]):
            final_chunks.append(txt)
            # 해당 청크의 출처 정보 찾기
            if txt in source_info_dict:
                reranked_source_info.append((txt, source_info_dict[txt]))
    
    return {"reranked_chunks": final_chunks, "source_info": reranked_source_info}


def generate_final_answer(state: GraphState) -> dict:
    # 프롬프트 구성
    chunks_text = "\n\n".join(state['reranked_chunks'])
    prompt_text = f"""
당신은 신뢰할 수 있는 문서를 기반으로 전문적이고 친절한 한국어 답변을 제공하는 AI입니다.

아래 정보를 참고하여 사용자 질문에 다음 기준에 따라 응답해 주세요:

1. 내용 요약 기준
   - 중복되거나 불필요한 세부 사항은 제외하고, 핵심 정보만 선별하여 정리합니다.
   - 최신 정보 및 정책 변화가 있다면 그것부터 언급해 주세요.
   - 문단은 2~3개로 나누어 구성하고, 각 문단은 주제를 중심으로 자연스럽게 연결되도록 작성합니다.

2. 문체와 형식
   - 딱딱한 리포트 형식보다는, 뉴스 기사나 친절한 전문가가 설명하는 말투로 작성하세요.
   - 너무 기술적인 용어나 긴 정의는 피하고, 필요시 간단히 풀어 설명합니다.
   - Markdown 형식 (`##`, `**`, `-`)은 절대 사용하지 말고, 대신 자연스러운 강조 표현(예: "특히", "중요하게는") 등을 사용합니다.

[참고 정보]
{chunks_text}

[질문]
{ state['rewritten_query'] }

위 기준을 충실히 따르며, 간결하고 자연스럽게 답변해 주세요.
"""

    # LLM 응답 생성
    resp = llm.invoke(prompt_text)
    final_answer = resp.content.strip()

    # 출처 정보 추출 (최대 3개, 중복 제거)
    sources = []
    seen_sources = set()
    if 'source_info' in state:
        for chunk, source in state['source_info']:
            if source not in seen_sources and len(sources) < 3:
                sources.append(source)
                seen_sources.add(source)

    # 출처 추가
    if sources:
        final_answer += "\n\n📚 참고한 자료:\n"
        for i, source in enumerate(sources, 1):
            final_answer += f"{i}. {source}\n"

    return {"final_answer": final_answer}


# --- 그래프 구성 ---
workflow = StateGraph(GraphState)
workflow.add_node('retrieve_from_chat_history', retrieve_from_chat_history)
workflow.add_node('rewrite_query', rewrite_query)
workflow.add_node('retrieve_web_chunks', retrieve_web_chunks)
workflow.add_node('retrieve_meerkat_chunks', retrieve_meerkat_chunks)
workflow.add_node('retrieve_db_chunks', retrieve_db_chunks)
workflow.add_node('rerank_chunks', rerank_chunks)
workflow.add_node('generate_final_answer', generate_final_answer)

workflow.set_entry_point('retrieve_from_chat_history')
workflow.add_edge('retrieve_from_chat_history', 'rewrite_query')
workflow.add_edge('rewrite_query', 'retrieve_web_chunks')
workflow.add_edge('retrieve_web_chunks', 'retrieve_meerkat_chunks')
workflow.add_edge('retrieve_meerkat_chunks', 'retrieve_db_chunks')
workflow.add_edge('retrieve_db_chunks', 'rerank_chunks')
workflow.add_edge('rerank_chunks', 'generate_final_answer')
workflow.add_edge('generate_final_answer', END)

graph = workflow.compile()
