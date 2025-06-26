'use client'

import { useState, useEffect, useContext, useRef, FC, ChangeEvent, KeyboardEvent } from 'react'
import { useRouter } from 'next/navigation'
import { ChatbotUIContext } from '@/context/context'
import { createNewsChat, getNewsChatById, updateNewsChat, addMessageToNewsChat, getNewsChatsByWorkspaceId } from '@/db/news-chats'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { IconSend, IconPlus, IconHome, IconHistory, IconChevronDown, IconPaperclip } from '@tabler/icons-react'
import { RagChat, Message } from '@/types/rag-chat'
import { sendRagQuery } from '@/lib/rag/rag'

interface NewsChatUIProps {
  workspaceId: string
  chatId?: string
}

export const NewsChatUI: FC<NewsChatUIProps> = ({ workspaceId, chatId }) => {
  const router = useRouter()
  const { profile, selectedWorkspace } = useContext(ChatbotUIContext)
  
  const [currentChat, setCurrentChat] = useState<RagChat | null>(null)
  const [messages, setMessages] = useState<RagChat["messages"]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [chatHistory, setChatHistory] = useState<RagChat[]>([])
  const [showChatHistory, setShowChatHistory] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  
  const fileInputRef = useRef<HTMLInputElement>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 스크롤을 맨 아래로 이동
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 채팅 로드
  useEffect(() => {
    if (chatId) {
      loadChat(chatId)
    }
  }, [chatId])

  // 채팅 히스토리 로드
  useEffect(() => {
    if (workspaceId) {
      loadChatHistory()
    }
  }, [workspaceId])

  // 채팅 히스토리 드롭다운 외부 클릭 시 닫기
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element
      if (showChatHistory && !target.closest('.chat-history-dropdown')) {
        setShowChatHistory(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showChatHistory])

  const loadChatHistory = async () => {
    try {
      setIsLoadingHistory(true)
      const chats = await getNewsChatsByWorkspaceId(workspaceId)
      
      // messages를 Message[] 타입으로 변환
      const convertedChats: RagChat[] = chats.map(chat => {
        const parsedMessages: Message[] = Array.isArray(chat.messages) 
          ? chat.messages 
          : chat.messages 
            ? JSON.parse(chat.messages as string)
            : []
        
        return {
          ...chat,
          messages: parsedMessages
        }
      })
      
      setChatHistory(convertedChats)
    } catch (error) {
      console.error('Error loading chat history:', error)
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const loadChat = async (id: string) => {
    try {
      setIsLoading(true)
      const chatRaw = await getNewsChatById(id)
      
      if (chatRaw) {
        const parsedMessages: Message[] = Array.isArray(chatRaw.messages) 
          ? chatRaw.messages 
          : chatRaw.messages 
            ? JSON.parse(chatRaw.messages as string)
            : []
        
        const chat: RagChat = {
          ...chatRaw,
          messages: parsedMessages
        }
        
        setCurrentChat(chat)
        setMessages(chat.messages)
      } else {
        await createNewChat()
      }
      
      setShowChatHistory(false) // 채팅 로드 후 히스토리 닫기
    } catch (error) {
      console.error('Error loading chat:', error)
      // 채팅을 찾을 수 없으면 새 채팅 생성
      await createNewChat()
    } finally {
      setIsLoading(false)
    }
  }

  const createNewChat = async () => {
    if (!profile || !selectedWorkspace) return

    try {
      setIsCreating(true)
      console.log('Creating new news chat...')
      
      const newChatRaw = await createNewsChat({
        user_id: profile.id,
        workspace_id: workspaceId,
        name: '뉴스 질문',
        messages: [],
        description: '뉴스 질문 채팅',
        folder_id: null,
        sharing: 'private'
      })
      
      if (newChatRaw) {
        const parsedMessages: Message[] = Array.isArray(newChatRaw.messages) 
          ? newChatRaw.messages 
          : newChatRaw.messages 
            ? JSON.parse(newChatRaw.messages as string)
            : []
        
        const newChat: RagChat = {
          ...newChatRaw,
          messages: parsedMessages
        }
        
        console.log('New news chat created:', newChat.id)
        setCurrentChat(newChat)
        setMessages([])
        
        // URL 업데이트
        router.replace(`/${selectedWorkspace.id}/news-chat/${newChat.id}`)
        
        // 채팅 히스토리 새로고침
        await loadChatHistory()
      }
    } catch (error) {
      console.error('Error creating new chat:', error)
    } finally {
      setIsCreating(false)
    }
  }

  const handleChatSelect = (chat: RagChat) => {
    router.push(`/${selectedWorkspace?.id}/news-chat/${chat.id}`)
  }

  const formatChatTitle = (chat: RagChat) => {
    const date = new Date(chat.updated_at)
    const timeString = date.toLocaleString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
    
    // 첫 번째 사용자 메시지의 내용을 제목으로 사용
    const firstUserMessage = chat.messages?.find(msg => msg.sender === 'user')
    const title = firstUserMessage?.content?.substring(0, 30) || '뉴스 질문'
    
    return `${title} (${timeString})`
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !currentChat || !profile) return

    const userMessage = {
      sender: 'user' as const,
      content: inputValue,
      type: 'text' as const
    }

    const assistantMessage = {
      sender: 'assistant' as const,
      content: '뉴스 관련 질문에 대한 답변을 준비 중입니다...',
      type: 'text' as const
    }

    // 메시지 추가
    setMessages(prev => [...prev, userMessage, assistantMessage])
    const userInput = inputValue
    setInputValue('')

    try {
      // 데이터베이스에 사용자 메시지 저장
      await addMessageToNewsChat(currentChat.id, userMessage)
      await addMessageToNewsChat(currentChat.id, assistantMessage)
      
      // RAG API 호출
      console.log('Sending RAG query for news chat:', userInput)
      const result = await sendRagQuery(userInput, profile, workspaceId, currentChat.id)
      
      // 실제 응답으로 assistant 메시지 업데이트
      const actualAssistantMessage = {
        sender: 'assistant' as const,
        content: result.text || result.react_code || result.dashboard_html || '죄송합니다. 응답을 생성할 수 없습니다.',
        type: result.type || 'text'
      }
      
      // 메시지 목록에서 임시 메시지를 실제 응답으로 교체
      setMessages(prev => {
        const newMessages = [...prev]
        const lastIndex = newMessages.length - 1
        if (newMessages[lastIndex]?.sender === 'assistant') {
          newMessages[lastIndex] = actualAssistantMessage
        }
        return newMessages
      })
      
      // 데이터베이스에 실제 응답 저장
      await addMessageToNewsChat(currentChat.id, actualAssistantMessage)
      
    } catch (error) {
      console.error('Error sending message:', error)
      
      // 에러 메시지로 교체
      const errorMessage = {
        sender: 'assistant' as const,
        content: '죄송합니다. 응답을 생성하는 중 오류가 발생했습니다.',
        type: 'text' as const
      }
      
      setMessages(prev => {
        const newMessages = [...prev]
        const lastIndex = newMessages.length - 1
        if (newMessages[lastIndex]?.sender === 'assistant') {
          newMessages[lastIndex] = errorMessage
        }
        return newMessages
      })
      
      await addMessageToNewsChat(currentChat.id, errorMessage)
    }
  }

  const handleFileSelect = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      handleFileUpload(event.target.files[0])
    }
  }

  const handleFileUpload = async (file: File) => {
    if (!currentChat || !profile) return

    const userMessage = {
      sender: 'user' as const,
      content: `Uploading file: ${file.name}`,
      type: 'file' as const,
      file_name: file.name,
      file_url: '' // Will be updated after upload
    }
    
    setMessages(prev => [...prev, userMessage])

    try {
      // Simulate file upload
      console.log('Uploading file:', file.name)
      await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate network delay
      const fileUrl = `/path/to/uploaded/${file.name}` // Replace with actual file upload logic and URL
      
      const updatedMessage = {
        ...userMessage,
        content: `File uploaded: ${file.name}`,
        file_url: fileUrl
      }
      
      setMessages(prev => {
        const newMessages = [...prev]
        const lastIndex = newMessages.length - 1
        if (newMessages[lastIndex]?.sender === 'user' && newMessages[lastIndex]?.type === 'file') {
          newMessages[lastIndex] = updatedMessage
        }
        return newMessages
      })

      await addMessageToNewsChat(currentChat.id, updatedMessage)
    } catch (error) {
      console.error('Error uploading file:', error)
      
      const errorMessage = {
        sender: 'user' as const,
        content: `Error uploading file: ${file.name}`,
        type: 'text' as const
      }
      setMessages(prev => {
        const newMessages = [...prev]
        const lastIndex = newMessages.length - 1
        if (newMessages[lastIndex]?.sender === 'user' && newMessages[lastIndex]?.type === 'file') {
          newMessages[lastIndex] = errorMessage
        }
        return newMessages
      })
    }
  }

  const handleKeyPress = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleGoHome = () => {
    router.push('/')
  }

  if (isLoading) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">채팅을 불러오는 중...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full w-full flex-col">
      {/* 헤더 */}
      <div className="flex items-center justify-between p-4 border-b bg-background">
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleGoHome}
            className="flex items-center space-x-2"
          >
            <IconHome size={16} />
            <span>홈으로</span>
          </Button>
        </div>
        
        {/* 채팅 히스토리 선택 */}
        <div className="flex items-center space-x-2">
          <div className="relative chat-history-dropdown">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowChatHistory(!showChatHistory)}
              className="flex items-center space-x-2"
              disabled={isLoadingHistory}
            >
              <IconHistory size={16} />
              <span>채팅 기록</span>
              <IconChevronDown size={16} className={`transition-transform ${showChatHistory ? 'rotate-180' : ''}`} />
            </Button>
            
            {showChatHistory && (
              <div className="absolute top-full left-0 mt-1 w-80 max-h-96 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg z-50">
                <div className="p-2">
                  <div className="text-sm font-medium text-gray-700 mb-2 px-2">이전 채팅</div>
                  {isLoadingHistory ? (
                    <div className="flex items-center justify-center p-4">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                      <span className="ml-2 text-sm text-gray-500">로딩 중...</span>
                    </div>
                  ) : chatHistory.length === 0 ? (
                    <div className="text-center text-gray-500 p-4">
                      <p className="text-sm">채팅 기록이 없습니다</p>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {chatHistory.map((chat) => (
                        <button
                          key={chat.id}
                          onClick={() => handleChatSelect(chat)}
                          className={`w-full text-left p-2 rounded text-sm hover:bg-gray-100 transition-colors ${
                            currentChat?.id === chat.id ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
                          }`}
                        >
                          <div className="font-medium truncate">{formatChatTitle(chat)}</div>
                          <div className="text-xs text-gray-500 mt-1">
                            {chat.messages?.length || 0}개 메시지
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          
          <Button
            variant="outline"
            size="sm"
            onClick={createNewChat}
            disabled={isCreating}
            className="flex items-center space-x-2"
          >
            <IconPlus size={16} />
            <span>새로운 채팅 시작하기</span>
          </Button>
        </div>
        
        <div className="text-sm text-muted-foreground">
          뉴스 채팅
        </div>
      </div>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            <p>뉴스에 대해 무엇이든 물어보세요!</p>
            <p className="text-sm mt-2">예: &quot;최신 AI 뉴스는?&quot;, &quot;기술 트렌드에 대해 알려줘&quot;</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${
                message.sender === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`max-w-[70%] rounded-lg px-4 py-2 ${
                  message.sender === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-800'
                }`}
              >
                <p className="text-sm">{message.content}</p>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 입력 영역 */}
      <div className="border-t p-4">
        <div className="flex space-x-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => fileInputRef.current?.click()}
            disabled={!currentChat}
          >
            <IconPaperclip size={20} />
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf"
            onChange={handleFileSelect}
          />
          <Textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="뉴스에 대해 질문하세요..."
            className="flex-1 min-h-[60px] max-h-[120px] resize-none"
            disabled={!currentChat}
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || !currentChat}
            className="px-4"
          >
            <IconSend size={16} />
          </Button>
        </div>
      </div>
    </div>
  )
} 