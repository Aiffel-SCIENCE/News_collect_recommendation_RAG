'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useContext } from 'react'
import { createRagChat } from '@/db/rag-chats'
import { ChatbotUIContext } from '@/context/context'

interface Props { 
  params: { 
    locale: string; 
    workspaceid: string 
  } 
}

export default function IndexPage({ params }: Props) {
  console.log('🔖 [rag-chat]/page.tsx (인덱스) 렌더링됨, params =', params);
  
  const router = useRouter()
  const { profile } = useContext(ChatbotUIContext)

  useEffect(() => {
    async function go() {
      if (!profile) {
        console.log('Profile not loaded yet, waiting...')
        return
      }

      try {
        console.log('Creating new RAG chat...')
        // 1) API로 새 채팅 만들기
        const newChat = await createRagChat({
          user_id: profile.id,
          workspace_id: params.workspaceid,
          name: '새 대화',
          messages: [],
          folder_id: null,
          description: '새로운 RAG 대화',
          sharing: 'private'
        })
        
        console.log('New chat created:', newChat.id)
        
        // 2) 생성된 ID로 리다이렉트
        router.replace(
          `/${params.locale}/${params.workspaceid}/rag-chat/${newChat.id}`
        )
      } catch (error) {
        console.error('Error creating new chat:', error)
        // 에러 발생 시 기본 페이지로 리다이렉트
        router.replace(`/${params.locale}/${params.workspaceid}`)
      }
    }
    
    go()
  }, [params, router, profile])

  return (
    <div className="flex h-full w-full items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">새 대화를 생성 중입니다… 잠시만 기다려 주세요.</p>
      </div>
    </div>
  )
} 