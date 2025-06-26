import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Docker 컨테이너 내부의 뉴스 추천 API로 요청 전달
    // 컨테이너 이름을 사용하여 같은 Docker 네트워크 내에서 통신
    const response = await fetch('http://news-recommendation-api:8001/recommendations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Recommendations API error:', error)
    return NextResponse.json(
      { 
        success: false, 
        error_message: '추천 서비스에 연결할 수 없습니다.',
        user_query_keywords: [],
        recommended_news: []
      },
      { status: 500 }
    )
  }
} 
