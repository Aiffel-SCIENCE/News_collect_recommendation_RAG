'use client'

import { NewsChatUI } from '@/components/chat/news-chat-ui'

interface Props { 
  params: { 
    locale: string; 
    workspaceid: string 
  } 
}

export default function NewsChatPage({ params }: Props) {
  console.log('🔖 [news-chat]/page.tsx (인덱스) 렌더링됨, params =', params);
  
  return (
    <div className="h-full w-full">
      <NewsChatUI
        workspaceId={params.workspaceid}
      />
    </div>
  )
} 