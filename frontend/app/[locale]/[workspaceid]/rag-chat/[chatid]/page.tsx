"use client"

import { RagChatUI } from "@/components/chat/rag-chat-ui"

interface Props {
  params: {
    locale: string
    workspaceid: string
    chatid: string
  }
}

export default function ChatPage({ params }: Props) {
  console.log('🔖 [rag-chat]/[chatid]/page.tsx (동적) 렌더링됨, params =', params);
  
  return (
    <div className="h-full w-full">
      <RagChatUI
        workspaceId={params.workspaceid}
        chatId={params.chatid}
      />
    </div>
  )
} 