'use client'

import { NewsChatUI } from '@/components/chat/news-chat-ui'

interface Props {
  params: { 
    locale: string; 
    workspaceid: string; 
    chatid: string 
  }
}

export default function NewsChatDetailPage({ params }: Props) {
  console.log('🔖 [news-chat]/[chatid]/page.tsx (동적) 렌더링됨, params =', params);
  
  return (
    <div className="h-full w-full">
      <NewsChatUI
        workspaceId={params.workspaceid}
        chatId={params.chatid}
      />
    </div>
  )
} 