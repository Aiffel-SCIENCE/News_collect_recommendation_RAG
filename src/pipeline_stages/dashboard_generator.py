import plotly.express as px
import pandas as pd

def generate_dashboard(chart_data: dict, react_code: str = None) -> dict:
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
    dashboard_html = ""
    
    # 1. 입력 데이터 유효성 검사
    if not chart_data or not chart_data.get("data"):
        print("대시보드 생성 스킵: chart_data가 비어있거나 'data' 키가 없습니다.")
        return {} # 빈 dict 반환

    # 2. 데이터프레임 변환
    try:
        df = pd.DataFrame(chart_data["data"])
        # 데이터프레임에 'label'과 'value' 컬럼이 있는지 확인
        if 'label' not in df.columns or 'value' not in df.columns:
            print(f"대시보드 생성 오류: 데이터에 'label' 또는 'value' 컬럼이 없습니다. 현재 컬럼: {df.columns}")
            return {}
    except Exception as e:
        print(f"대시보드 생성 오류: Pandas 데이터프레임 변환 실패 - {e}")
        return {}

    # 3. 차트 생성
    chart_type = chart_data.get("chart_type", "bar")
    title = chart_data.get("title", "Dashboard")
    x_axis = chart_data.get("x_axis_label") or "Label"
    y_axis = chart_data.get("y_axis_label") or "Value"
    fig = None
    try:
        print(f"'{chart_type}' 유형의 차트 생성 시도...")
        if chart_type == "bar":
            fig = px.bar(df, x='label', y='value', title=title, labels={'label': x_axis, 'value': y_axis})
        elif chart_type == "line":
            fig = px.line(df, x='label', y='value', title=title, labels={'label': x_axis, 'value': y_axis}, markers=True)
        elif chart_type == "pie":
            fig = px.pie(df, names='label', values='value', title=title)
        else:
            print(f"경고: 지원되지 않는 차트 유형 '{chart_type}'. 막대 그래프로 대체합니다.")
            fig = px.bar(df, x='label', y='value', title=title, labels={'label': x_axis, 'value': y_axis})
        
        # 차트 스타일 약간 조정
        fig.update_layout(title_x=0.5)

    except Exception as e:
        print(f"Plotly 차트 생성 중 오류 발생: {e}")
        return {}

    # 4. HTML 변환
    if fig:
        print("차트 생성 성공. HTML로 변환합니다.")
        # full_html=False: <script>와 <div>만 생성하여 삽입하기 좋게 만듦
        # include_plotlyjs='cdn': 인터넷을 통해 Plotly.js를 불러오므로 HTML 크기가 작아짐
        dashboard_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    # 5. 최종 결과 반환
    return {
        "dashboard_html": dashboard_html,
        "react_code": react_code # 입력받은 react_code는 그대로 다시 전달
    }