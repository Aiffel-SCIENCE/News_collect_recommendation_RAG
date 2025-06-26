'use client';

import { ReactNode } from 'react';

interface NewsChatLayoutProps {
  children: ReactNode;
}

export default function NewsChatLayout({ children }: NewsChatLayoutProps) {
  console.log('🔖 NewsChatLayout 렌더링됨, children 존재:', !!children);
  
  // Dashboard를 우회하고 직접 children 렌더링
  return (
    <div className="news-chat-fullscreen h-full w-full">
      {children}
    </div>
  );
} 