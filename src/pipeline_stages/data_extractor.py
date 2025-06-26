from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from typing import List, Dict, Any, Optional

# --- Pydantic 모델 정의: LLM의 출력 형식을 강제하여 안정적인 JSON 획득 ---

class ChartDataItem(BaseModel):
    label: str = Field(description="차트의 각 항목을 나타내는 라벨 (예: '코스피', '삼성전자')")
    value: float = Field(description="해당 항목의 수치 값 (예: 2855.77, 1.55)")
    category: Optional[str] = Field(None, description="데이터를 그룹화할 수 있는 카테고리 (선택 사항)")

class ChartData(BaseModel):
    chart_type: str = Field(description="추천하는 차트 유형 (예: 'bar', 'line', 'pie')")
    title: str = Field(description="차트의 제목")
    data: List[ChartDataItem] = Field(description="차트를 구성하는 실제 데이터 목록")
    x_axis_label: Optional[str] = Field(None, description="X축의 이름 (예: '지수명', '종목')")
    y_axis_label: Optional[str] = Field(None, description="Y축의 이름 (예: '상승률(%)')")

class ExtractedContent(BaseModel):
    """입력된 텍스트에서 추출된 구조화된 차트 데이터와 React 코드"""
    chart_data: Optional[ChartData] = Field(None, description="시각화를 위한 구조화된 차트 데이터 (JSON)")
    react_code: Optional[str] = Field(None, description="데이터를 시각화하는 React 컴포넌트 코드 (문자열)")


# --- 데이터 추출 함수 ---

def extract_chart_data_and_react_code(question: str, generation_text: str, intent: str) -> dict:
    """
    LLM이 생성한 텍스트(generation_text)에서 차트용 JSON 데이터와 React 코드를 추출합니다.
    """
    # config.yaml 등에서 모델 정보를 불러오도록 수정 가능
    llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0) 
    structured_llm = llm.with_structured_output(ExtractedContent)
    
    # 사용자의 요청 유형에 따라 프롬프트 분기
    if intent == 'react':
        system_prompt = """
        당신은 전문가 React 개발자입니다. 제공된 텍스트 내용(마크다운 테이블 포함)과 사용자의 질문을 기반으로, 데이터를 시각화하는 단일 React 컴포넌트 코드를 생성해야 합니다.
        - `recharts` 또는 `nivo`와 같은 인기 있는 라이브러리를 사용하세요.
        - 코드는 바로 복사-붙여넣기 해서 사용할 수 있는 완성된 형태여야 합니다.
        - 코드만 생성하고 다른 설명은 절대 추가하지 마세요.
        """
    else: # 'dashboard' intent
        system_prompt = """
당신은 데이터 분석가이자 시각화 전문가입니다. 제공된 텍스트 내용과 사용자의 질문을 분석하여, 이 데이터를 가장 효과적으로 시각화할 수 있는 JSON 데이터를 생성해야 합니다.

**[중요 규칙]**
1.  **동일한 척도 사용**: 여러 항목을 비교하는 차트를 만들 때는, 모든 항목이 '상승률(%)', '거래량', '지수 값' 등 **반드시 동일한 의미와 단위를 가진 값**을 사용하도록 데이터를 추출하세요. 절대적인 값과 비율을 섞지 마세요.
2.  **적절한 차트 유형 추천**:
    - 시간에 따른 데이터 변화 추이를 보여줄 때는 'line' 차트를 추천하세요.
    - 여러 카테고리(예: 국가별, 종목별)의 값을 비교할 때는 **'bar' 차트를 추천**하세요.
    - 전체에서 각 항목이 차지하는 비중을 보여줄 때는 'pie' 차트를 추천하세요.

- 텍스트에 포함된 수치, 항목, 카테고리를 정확히 추출하여 `ChartData` JSON 형식에 맞게 정리하세요.
- 사용자의 질문 의도를 파악하여 적절한 `title`을 만드세요.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "사용자 질문: {question}\n\n분석할 텍스트:\n{text}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        result = chain.invoke({
            "question": question,
            "text": generation_text
        })
        
        # Pydantic 모델을 dict로 변환하여 반환
        return {
            "chart_data": result.chart_data.dict() if result.chart_data else {},
            "react_code": result.react_code if result.react_code else ""
        }
    except Exception as e:
        print(f"데이터 추출 중 오류 발생: {e}")
        return {"chart_data": {}, "react_code": ""}