'use client';

import { ReactNode } from 'react';

interface RagChatLayoutProps {
  children: ReactNode;
}

export default function RagChatLayout({ children }: RagChatLayoutProps) {
  console.log('🔖 RagChatLayout 렌더링됨, children 존재:', !!children);
  
  // 여기선 Dashboard를 쓰지 않고, 오로지 RagChatUI 계층만 렌더링
  return (
    <div className="rag-chat-fullscreen h-full w-full">
      {children}
    </div>
  );
} 