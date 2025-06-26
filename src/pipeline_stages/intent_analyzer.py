from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from config_loader.settings import SETTINGS

def analyze_intent(question: str, llm=None) -> dict:
    prompt = ChatPromptTemplate.from_template(
        """너는 사용자의 질문이 '일반 텍스트 답변(text)'이 필요한지, '대시보드(dashboard)' 또는 'React 코드(react)'가 필요한지 판단하는 AI야.\n- 여러 항목 비교, 추세, 분포, 비율, 통계 등은 'dashboard'\n- 'React 코드'가 필요하면 'react'\n- 단일 정보, 설명, 정의 등은 'text'\n아래 질문의 intent를 'dashboard', 'react', 'text' 중 하나로만 답해줘.\n질문: {question}\n"""
    )
    model_name = SETTINGS.get('OPENAI_KEYWORD_MODEL', 'gpt-4.1-nano')
    openai_api_key = SETTINGS.get('OPENAI_API_KEY')
    chain = prompt | (llm or ChatOpenAI(model_name=model_name, openai_api_key=openai_api_key))
    result = chain.invoke({"question": question}).content.strip().lower()
    if "react" in result:
        intent = "react"
    elif "dashboard" in result:
        intent = "dashboard"
    else:
        intent = "text"
    return {"intent": intent} 