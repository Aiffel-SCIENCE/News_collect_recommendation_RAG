import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { query, profileId, workspaceId, chatId } = body

    // Docker 컨테이너 간 통신을 위해 서비스 이름을 직접 사용합니다.
    const ragApiUrl = 'http://rag-api:8010/rag-chat';
    
    if (!ragApiUrl) {
      throw new Error("RAG_API_URL is not defined in environment variables.")
    }

    console.log('Sending request to RAG API:', ragApiUrl)
    console.log('Request body:', { query, profileId, workspaceId, chatId })

    // RAG API로 요청 전달
    const response = await fetch(ragApiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query,
        user_id: profileId,
        workspace_id: workspaceId,
        chat_id: chatId
      }),
    })

    if (!response.ok) {
      const errorData = await response.text()
      console.error(`RAG API request failed: ${response.status}`, errorData)
      throw new Error(`RAG API request failed: ${response.status}`)
    }
    
    const data = await response.json()
    console.log('RAG API response:', data)
    return NextResponse.json(data)

  } catch (error) {
    console.error('RAG API proxy error:', error)
    const errorResponse = {
      error: "RAG service connection failed.",
      message: "The RAG service is currently unavailable. Please try again later."
    }
    return NextResponse.json(errorResponse, { status: 500 })
  }
} 