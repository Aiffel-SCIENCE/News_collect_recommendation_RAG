'use client'

import { useEffect, useState, useContext } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { ChatbotUIContext } from '@/context/context'
import { useChatHandler } from '@/components/chat/chat-hooks/use-chat-handler'
import { supabase } from '@/lib/supabase/browser-client'
import { IconThumbUp, IconThumbDown, IconShare, IconBookmark, IconMessagePlus } from '@tabler/icons-react'

// 뉴스 데이터 타입
interface Article {
  id: string
  title?: string
  url?: string
  summary?: string
  published_at?: string
  similarity_score: number
  image_url?: string
  keywords?: string[]
  related_news?: Article[]
  upvotes: number
  downvotes: number
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
  const { selectedWorkspace, chatMessages, profile } = useContext(ChatbotUIContext)
  const { handleNewChat } = useChatHandler()

  const [news, setNews] = useState<NewsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)

  // 사용자 ID 가져오기
  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      setUserId(user?.id || null)
    }
    getUser()
  }, [])

  // API URL을 동적으로 결정
  const getApiUrl = () => {
    // 프로덕션 환경에서는 같은 서버의 포트 사용
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname
      if (hostname === '34.61.170.171') {
        return `http://${hostname}:8001/recommendations`
      }
    }
    // 개발 환경에서는 localhost 사용
    return 'http://localhost:8001/recommendations'
  }

  // 개인화된 쿼리 생성 (프로필 컨텍스트 + 워크스페이스 + 사용자)
  const generatePersonalizedQuery = (context: string) => {
    let queryParts = []
    
    // 1. 프로필 컨텍스트 (사용자가 "What would you like the AI to know about you"에 입력한 내용)
    if (context && context.trim()) {
      queryParts.push(context)
    }
    
    // 2. 워크스페이스 관심사
    if (selectedWorkspace?.interests && selectedWorkspace.interests.trim()) {
      queryParts.push(selectedWorkspace.interests)
    }
    
    // 3. 워크스페이스 이름에서 키워드 추출
    if (selectedWorkspace?.name && selectedWorkspace.name !== "Home") {
      queryParts.push(`${selectedWorkspace.name} 관련 뉴스`)
    }
    
    // 4. 기본값 (아무것도 없을 때)
    if (queryParts.length === 0) {
      queryParts.push("과학 기술 뉴스")
    }
    
    // 모든 요소를 결합하여 개인화된 쿼리 생성
    const personalizedQuery = queryParts.join(" ")
    console.log('개인화된 쿼리 생성:', {
      profileContext: context,
      workspaceInterests: selectedWorkspace?.interests,
      workspaceName: selectedWorkspace?.name,
      finalQuery: personalizedQuery
    })
    
    return personalizedQuery
  }

  // 뉴스 상세 페이지로 이동하는 함수
  const onClickNewsDetail = (id: string) => {
    router.push(`./news/${id}`)
  }

  const handleAskAnythingClick = () => {
    console.log('Ask Anything 클릭됨, 뉴스 채팅 페이지로 이동')
    router.push(`/${pathname[1]}/${pathname[2]}/news-chat`)
  }

  // 뉴스 추천 데이터 로드
  useEffect(() => {
    async function loadNews() {
      if (!selectedWorkspace || !userId) return
      
      setLoading(true)
      setError(null)
      
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 60000) // 60초로 타임아웃 증가

        const apiUrl = getApiUrl()
        console.log('API URL:', apiUrl)
        console.log('User ID:', userId)
        console.log('Workspace:', selectedWorkspace.name)

        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            accept: 'application/json',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
            user_id: userId, // 실제 사용자 ID 사용
            query: generatePersonalizedQuery(profile?.profile_context || ""), // 워크스페이스별 쿼리
            profile_context: profile?.profile_context || null, // 프로필 컨텍스트 추가
            num_recommendations: 15
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
      } finally {
        setLoading(false)
      }
    }
    
    loadNews()
  }, [selectedWorkspace, userId, profile?.profile_context])

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

  const handleVote = (articleId: string, voteType: 'up' | 'down') => {
    console.log(`Voted ${voteType} for article ${articleId}`);
  };

  const handleShare = (articleId: string) => {
    console.log(`Shared article ${articleId}`);
  };

  const handleBookmark = (articleId: string) => {
    console.log(`Bookmarked article ${articleId}`);
  };

  const handleRelatedNewsClick = (id: string) => {
    router.push(`./news/${id}`)
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
        <div className="text-red-500">{error}</div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-screen-lg">
      <div className="flex w-full items-center justify-between border-b p-4">
        <div className="text-2xl font-bold">뉴스 추천</div>
        <a
          href="https://www.notion.so/Daily-News-1c94a5a1ff198008b31ee65fb54aa422"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center rounded-md bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
        >
          가이드북
        </a>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {/* Ask Anything section */}
        <div
          className="cursor-pointer border-b p-4 hover:bg-gray-100"
          onClick={handleAskAnythingClick}
        >
          <div className="flex items-center">
            <IconMessagePlus className="mr-3" size={24} />
            <div>
              <div className="text-xl font-bold">Ask Anything</div>
              <div className="text-gray-500">뉴스에 대해 질문해보세요</div>
            </div>
          </div>
        </div>

        {/* Recommended News section */}
        <div className="p-4">
          <h2 className="mb-4 text-xl font-bold">추천 뉴스</h2>
          {news && news.recommended_news.length > 0 ? (
            <div className="space-y-4">
              {news.recommended_news.map(article => (
                <div
                  key={article.id}
                  className="cursor-pointer rounded-lg border p-4 transition-shadow hover:shadow-md"
                  onClick={() => onClickNewsDetail(article.id)}
                >
                  <h3 className="mb-2 text-lg font-bold">{article.title}</h3>
                  <p className="mb-3 text-gray-600 line-clamp-3">
                    {article.summary}
                  </p>
                  <div className="flex items-center justify-between text-sm text-gray-500">
                    <span>
                      {new Date(
                        article.published_at || Date.now()
                      ).toLocaleDateString()}
                    </span>
                    <div className="flex items-center space-x-4">
                      <button
                        className="flex items-center"
                        onClick={e => {
                          e.stopPropagation()
                          handleVote(article.id, 'up')
                        }}
                      >
                        <IconThumbUp size={18} />
                        <span className="ml-1">{article.upvotes}</span>
                      </button>
                      <button
                        className="flex items-center"
                        onClick={e => {
                          e.stopPropagation()
                          handleVote(article.id, 'down')
                        }}
                      >
                        <IconThumbDown size={18} />
                        <span className="ml-1">{article.downvotes}</span>
                      </button>
                      <button
                        onClick={e => {
                          e.stopPropagation()
                          handleShare(article.id)
                        }}
                      >
                        <IconShare size={18} />
                      </button>
                      <button
                        onClick={e => {
                          e.stopPropagation()
                          handleBookmark(article.id)
                        }}
                      >
                        <IconBookmark size={18} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div>추천 뉴스 목록이 없습니다.</div>
          )}
        </div>
      </div>
      
      <div className="border-t p-4">
        <button
          className="flex w-full items-center justify-center rounded-lg border border-input p-3 text-muted-foreground hover:bg-secondary"
          onClick={() => handleNewChat()}
        >
          <IconMessagePlus className="mr-2" size={20} />
          새로운 채팅 시작하기
        </button>
      </div>
    </div>
  );
}