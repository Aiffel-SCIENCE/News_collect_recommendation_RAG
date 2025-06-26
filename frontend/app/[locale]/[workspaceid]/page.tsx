'use client'

import { useEffect, useState, useContext } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import { ChatbotUIContext } from '@/context/context'
import { ChatInput } from '@/components/chat/chat-input'
import { IconSparkles, IconLoader } from '@tabler/icons-react'
import { Input } from '@/components/ui/input'

// 뉴스 데이터 타입
interface Article {
  id: string
  title?: string
  url?: string
  summary?: string
  published_at?: string
  similarity_score: number
}

interface NewsData {
  user_query_keywords: string[]
  recommended_news: Article[]
  success: boolean
  error_message?: string
}

export default function NewsListPage() {
  const router = useRouter()
  const pathname = usePathname().split('/')
  const { selectedWorkspace, chatMessages } = useContext(ChatbotUIContext)

  const [news, setNews] = useState<NewsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchUri = `http://34.61.170.171:8001/recommendations`

  // 뉴스 추천 데이터 로드
  useEffect(() => {
    async function loadNews() {
      setLoading(true)
      setError(null)
      
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 10000) // 10초 타임아웃

        const response = await fetch(fetchUri, {
          method: 'POST',
          headers: {
            accept: 'application/json',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
            query: selectedWorkspace?.interests || "과학 기술 뉴스",
            num_recommendations: 10
          }),
          signal: controller.signal
        })

        clearTimeout(timeoutId)

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const data: NewsData = await response.json()
        setNews(data)
      } catch (error: any) {
        console.error("Failed to fetch news recommendations:", error)
        
        if (error.name === 'AbortError') {
          setError("추천 서비스 연결 시간이 초과되었습니다. 서비스가 시작되지 않았을 수 있습니다.")
        } else if (error.message.includes('fetch')) {
          setError("추천 서비스에 연결할 수 없습니다. 서비스가 실행 중인지 확인해주세요.")
        } else {
          setError("뉴스 추천을 불러오는 중 오류가 발생했습니다.")
        }

        // 오류 시 더미 데이터 제공
        setNews({
          user_query_keywords: ["과학", "기술"],
          recommended_news: [
            {
              id: "dummy-1",
              title: "뉴스 추천 서비스를 사용할 수 없습니다",
              summary: "Docker 서비스를 시작하거나 네트워크 연결을 확인해주세요.",
              similarity_score: 0.0
            }
          ],
          success: false,
          error_message: error.message
        })
      } finally {
        setLoading(false)
      }
    }
    
    if (selectedWorkspace) {
      loadNews()
    }
  }, [fetchUri, selectedWorkspace])

  // 채팅 메시지 생기면 상세 페이지로 이동
  useEffect(() => {
    if (chatMessages.length > 0) {
      const chatPath = `/${pathname[1]}/chat/${chatMessages[0].message.chat_id}`
      router.push(chatPath)
    }
  }, [chatMessages, pathname, router])

  // 채팅 상태일 때 렌더링 생략
  if (chatMessages.length > 0) {
    return null
  }

  if (loading) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center">
        <div className="text-2xl">뉴스 추천을 불러오는 중...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center">
        <div className="text-2xl text-red-500 mb-4">오류 발생</div>
        <div className="text-lg text-gray-600 mb-4">{error}</div>
        <div className="text-sm text-gray-500">
          Docker 서비스를 시작하려면: docker-compose up -d
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center">
      <div className="text-4xl mb-8">뉴스 추천</div>
      
      {news && (
        <div className="w-full max-w-4xl px-4">
          <div className="mb-4">
            <h3 className="text-lg font-semibold">검색 키워드:</h3>
            <div className="flex flex-wrap gap-2 mt-2">
              {news.user_query_keywords.map((keyword, index) => (
                <span key={index} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">
                  {keyword}
                </span>
              ))}
            </div>
          </div>
          
          <div className="space-y-4">
            {news.recommended_news.map((article) => (
              <div key={article.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                <h4 className="text-lg font-semibold mb-2">{article.title}</h4>
                {article.summary && (
                  <p className="text-gray-600 mb-2">{article.summary}</p>
                )}
                {article.url && (
                  <a 
                    href={article.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    원문 보기
                  </a>
                )}
                <div className="text-sm text-gray-500 mt-2">
                  유사도 점수: {(article.similarity_score * 100).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
