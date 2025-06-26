'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import { IconThumbUp, IconThumbDown, IconShare, IconBookmark, IconLoader } from '@tabler/icons-react'

// ✅ 정확한 타입 선언
interface Article {
  ID: string
  title: string
  content: string
  published_at: string
  url: string
  summary?: string
  source?: string
  keywords?: string[]
}

interface Comment {
  id: string;
  author: string;
  date: string;
  text: string;
}

interface RelatedNews {
    id: string;
    title: string;
    published_at: string;
}

interface NewsResponse {
  article: Article | null
  success: boolean
  error_message?: string
}

export default function NewsDetailPage() {
  // ✅ useState에 명시적 타입 지정
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [upvotes, setUpvotes] = useState(0);
  const [downvotes, setDownvotes] = useState(0);
  const [comments, setComments] = useState<Comment[]>([]);
  const [relatedNews, setRelatedNews] = useState<RelatedNews[]>([]);

  const router = useRouter()
  const params = useParams()
  const newsId = params.newsid as string

  // API URL을 동적으로 결정
  const getApiUrl = () => {
    // 프로덕션 환경에서는 같은 서버의 포트 사용
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname
      if (hostname === '34.61.170.171') {
        return `http://${hostname}:8002/articles`
      }
    }
    // 개발 환경에서는 localhost 사용
    return 'http://127.0.0.1:8002/articles'
  }

  useEffect(() => {
    async function fetchArticleDetail() {
      if (!newsId) {
        setError('뉴스 ID가 없습니다.')
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        const apiUrl = getApiUrl()
        const response = await fetch(`${apiUrl}/${newsId}`, {
          headers: {
            accept: 'application/json',
            'Content-Type': 'application/json',
          },
        })
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const data: NewsResponse = await response.json()
        
        if (data.success && data.article) {
          setArticle(data.article)
          // Mock data for now
          setUpvotes(10)
          setDownvotes(2)
          setComments([
            {id: '1', author: '유저1', date: '2024-07-31', text: '좋은 기사입니다.'}
          ])
          setRelatedNews([
            {id: 'related-1', title: '관련 뉴스 1', published_at: '2024-07-31'}
          ])
        } else {
          setError(data.error_message || '뉴스를 찾을 수 없습니다.')
        }
      } catch (error) {
        console.error('Error fetching article:', error)
        setError('뉴스를 불러오는 중 오류가 발생했습니다.')
      } finally {
        setLoading(false)
      }
    }
    
    fetchArticleDetail()
  }, [newsId])

  const handleUpvote = () => { /* Logic for upvoting */ };
  const handleDownvote = () => { /* Logic for downvoting */ };
  const handleShare = () => { /* Logic for sharing */ };
  const handleBookmark = () => { /* Logic for bookmarking */ };
  const handleRelatedNewsClick = (id: string) => { router.push(`/news/${id}`) };

  if (loading) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center">
        <div className="text-2xl">뉴스를 불러오는 중...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center">
        <div className="text-2xl text-red-500 mb-4">오류 발생</div>
        <div className="text-lg text-gray-600 mb-4">{error}</div>
        <button 
          onClick={() => router.back()}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          뒤로 가기
        </button>
      </div>
    )
  }

  if (!article) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center">
        <div className="text-2xl">뉴스를 찾을 수 없습니다.</div>
        <button 
          onClick={() => router.back()}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 mt-4"
        >
          뒤로 가기
        </button>
      </div>
    )
  }

  return (
    <Box component="section" sx={{ p: 4, maxWidth: '800px', margin: '0 auto' }}>
      <Stack spacing={3}>
        <div>
          <h1 className="text-3xl font-bold mb-4">{article.title}</h1>
          <div className="text-sm text-gray-500 mb-2">
            {article.published_at && (
              <span>발행일: {new Date(article.published_at).toLocaleDateString('ko-KR')}</span>
            )}
            {article.source && (
              <span className="ml-4">출처: {article.source}</span>
            )}
          </div>
        </div>

        {article.summary && (
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-semibold mb-2">요약</h3>
            <p className="text-gray-700">{article.summary}</p>
          </div>
        )}

        <div className="prose max-w-none">
          <h3 className="font-semibold mb-2">본문</h3>
          <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">
            {article.content}
          </div>
        </div>

        {article.keywords && article.keywords.length > 0 && (
          <div>
            <h3 className="font-semibold mb-2">키워드</h3>
            <div className="flex flex-wrap gap-2">
              {article.keywords.map((keyword: string, index: number) => (
                <span key={index} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        )}

        {article.url && (
          <div className="pt-4 border-t">
            <a 
              href={article.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="inline-flex items-center px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
            >
              원문 보기 →
            </a>
          </div>
        )}

        <div className="pt-4 border-t">
          <button 
            onClick={() => router.back()}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
          >
            목록으로 돌아가기
          </button>
        </div>

        <div className="flex w-full flex-col">
          <div className="flex w-full items-center justify-between">
            <div className="flex items-center">
              <div
                className="flex cursor-pointer items-center space-x-2 hover:opacity-50"
                onClick={handleUpvote}
              >
                <IconThumbUp size={24} />
                <div className="text-lg">{upvotes}</div>
              </div>
              <div
                className="ml-4 flex cursor-pointer items-center space-x-2 hover:opacity-50"
                onClick={handleDownvote}
              >
                <IconThumbDown size={24} />
                <div className="text-lg">{downvotes}</div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <IconShare
                className="cursor-pointer hover:opacity-50"
                size={24}
                onClick={handleShare}
              />
              <IconBookmark
                className="cursor-pointer hover:opacity-50"
                size={24}
                onClick={handleBookmark}
              />
            </div>
          </div>

          <div className="mt-4 flex w-full">
            <div className="flex w-1/2 flex-col pr-4">
              <div className="text-2xl font-bold">{article.title}</div>
              <div className="mt-2 text-gray-500">{new Date(article.published_at).toLocaleDateString('ko-KR')}</div>
              <div className="mt-4 text-lg">{article.summary}</div>
              <div className="mt-4">
                <div className="flex flex-wrap">
                  {article.keywords?.map(keyword => (
                    <div
                      key={keyword}
                      className="mb-2 mr-2 rounded-full bg-gray-200 px-3 py-1 text-sm font-semibold text-gray-700"
                    >
                      {keyword}
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-4">
                <div className="text-xl font-bold">Comments</div>
                <div className="mt-2">
                  {comments.map(comment => (
                    <div key={comment.id} className="mt-2">
                      <div className="flex items-center">
                        <div className="text-lg font-bold">
                          {comment.author}
                        </div>
                        <div className="ml-2 text-gray-500">
                          {comment.date}
                        </div>
                      </div>
                      <div className="mt-1">{comment.text}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex w-1/2 flex-col pl-4">
              <div className="text-2xl font-bold">관련 뉴스</div>
              <div className="mt-2">
                {relatedNews.map(news => (
                  <div
                    key={news.id}
                    className="mt-2 cursor-pointer"
                    onClick={() => handleRelatedNewsClick(news.id)}
                  >
                    <div className="text-lg font-bold">{news.title}</div>
                    <div className="mt-1 text-gray-500">{new Date(news.published_at).toLocaleDateString('ko-KR')}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Stack>
    </Box>
  )
}
