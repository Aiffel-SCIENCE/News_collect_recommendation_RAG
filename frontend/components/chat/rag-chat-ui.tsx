"use client"

import { ChatbotUIContext } from "@/context/context"
import React, { FC, useContext, useEffect, useRef, useState } from "react"
import { sendRagQuery } from "@/lib/rag/rag"
import { WithTooltip } from "@/components/ui/with-tooltip"
import { IconCirclePlus, IconPlayerStop, IconSend, IconBrain, IconFileText, IconSearch } from "@tabler/icons-react"
import { TextareaAutosize } from "@/components/ui/textarea-autosize"
import { LiveProvider, LiveEditor, LiveError, LivePreview } from "react-live"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { Message, RagChat } from "@/types/rag-chat"
import { createRagChat, getRagChatById, updateRagChat } from "@/db/rag-chats"
import { useRouter, useSearchParams, useParams } from "next/navigation"

interface RagChatUIProps {
  chatId?: string
  workspaceId?: string
}

type UploadStatus = "idle" | "uploading" | "success" | "error"

export function RagChatUI({ chatId: propChatId, workspaceId: propWorkspaceId }: RagChatUIProps) {
  console.log('🔖 RagChatUI 마운트, props =', { workspaceId: propWorkspaceId, chatId: propChatId })
  
  const { profile, selectedWorkspace } = useContext(ChatbotUIContext)
  const router = useRouter()
  const searchParams = useSearchParams()
  const params = useParams()

  const [query, setQuery] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)
  const [chat, setChat] = useState<RagChat | null>(null)
  const [chatId, setChatId] = useState<string | null>(propChatId || null)

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle")

  const fileInputRef = useRef<HTMLInputElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)

  const [isInitializing, setIsInitializing] = useState(true)
  const [loadingError, setLoadingError] = useState<string | null>(null)
  const [forceProceed, setForceProceed] = useState(false)

  // 워크스페이스 ID 결정 (props 우선, context 차선)
  const workspaceId = propWorkspaceId || selectedWorkspace?.id || "default-workspace-id"

  // ==========================================================
  // ✨ 모든 Hook들을 컴포넌트 최상단으로 이동시킵니다.
  // ==========================================================

  useEffect(() => {
    let isMounted = true;
    
    const checkInitialization = () => {
      if (selectedWorkspace && profile) {
        if (isMounted) {
          setIsInitializing(false)
        }
      }
    }

    checkInitialization()

    const timeout = setTimeout(() => {
      if (isMounted) {
        console.log("Initialization timeout, proceeding anyway")
        setIsInitializing(false)
        setLoadingError("초기화 시간이 초과되었습니다. 계속 진행합니다.")
      }
    }, 5000)

    return () => {
      isMounted = false;
      clearTimeout(timeout)
    }
  }, [selectedWorkspace, profile])

  useEffect(() => {
    let isMounted = true;
    
    const timer = setTimeout(() => {
      if (isMounted) {
        console.log("Force proceeding after 3 seconds")
        setForceProceed(true)
      }
    }, 3000)

    return () => {
      isMounted = false;
      clearTimeout(timer)
    }
  }, [])

  // 1) propChatId가 있으면, 바로 메시지 fetch
  useEffect(() => {
    let isMounted = true;
    
    // URL 동적 세그먼트에서 chatId를 가져오거나 props로 전달된 propChatId 사용
    const urlChatId = params.chatid as string
    const queryChatId = searchParams.get('chatId')
    const finalChatId = propChatId || urlChatId || queryChatId
    
    console.log("ChatId check:", { 
      propChatId, 
      urlChatId: params.chatid, 
      queryChatId, 
      finalChatId 
    })
    
    if (finalChatId) {
      console.log("Setting chatId from prop/URL:", finalChatId)
      setChatId(finalChatId)
    }
  }, [propChatId, params.chatid, searchParams])

  // 2) chatId가 설정되면 메시지 fetch
  useEffect(() => {
    let isMounted = true;
    
    console.log("RagChatUI useEffect triggered with chatId:", chatId)
    console.log("Current conditions:", { 
      hasChatId: !!chatId, 
      hasWorkspace: !!workspaceId, 
      forceProceed,
      profile: !!profile
    })
    
    // chatId가 있으면 메시지를 가져옴
    if (chatId) {
      console.log("Starting to fetch chat history for chatId:", chatId)
      if (isMounted) {
        setIsHistoryLoading(true)
      }
      
      const timeoutId = setTimeout(() => {
        if (isMounted) {
          console.log("Chat history fetch timeout, proceeding anyway")
          setIsHistoryLoading(false)
          setChat(null)
          setMessages([])
        }
      }, 10000)

      getRagChatById(chatId)
        .then(chatRaw => {
          if (isMounted) {
            clearTimeout(timeoutId)
            console.log("Successfully fetched chat:", chatRaw)
            
            // messages를 Message[] 타입으로 변환
            const parsedMessages: Message[] = Array.isArray(chatRaw.messages) 
              ? chatRaw.messages 
              : chatRaw.messages 
                ? JSON.parse(chatRaw.messages as string)
                : []
            
            const chat: RagChat = {
              ...chatRaw,
              messages: parsedMessages
            }
            
            setChat(chat)
            setMessages(chat.messages)
          }
        })
        .catch(err => {
          if (isMounted) {
            clearTimeout(timeoutId)
            console.error("Failed to fetch chat history", err)
            console.error("Error details:", {
              message: err.message,
              stack: err.stack,
              chatId: chatId
            })
            toast.error("채팅 기록을 불러오는데 실패했습니다. 새 채팅을 시작합니다.")
            setChat(null)
            setMessages([])
          }
        })
        .finally(() => {
          if (isMounted) {
            clearTimeout(timeoutId)
            console.log("Finished fetching chat history, setting loading to false")
            setIsHistoryLoading(false)
          }
        })
    } else {
      console.log("No chatId provided, skipping fetch")
      if (isMounted) {
        setIsHistoryLoading(false)
      }
    }

    return () => {
      isMounted = false;
    }
  }, [chatId])

  // 3) propChatId가 없을 때만 신규 채팅 생성 (기존 로직)
  useEffect(() => {
    let isMounted = true;
    
    const checkAndCreateWorkspace = async () => {
      if (profile && !selectedWorkspace) {
        try {
          console.log("Checking for user workspace...")
          const response = await fetch(`/api/workspaces/user/${profile.id}`)
          if (response.ok) {
            const workspaces = await response.json()
            if (workspaces.length > 0) {
              console.log("Found existing workspace:", workspaces[0])
              return
            }
          }
          console.log("No workspace found, creating new one...")
          await createUserWorkspace(profile.id)
        } catch (error) {
          console.error("Error checking/creating workspace:", error)
          if (isMounted) {
            toast.error("워크스페이스 생성에 실패했습니다.")
          }
        }
      }
    }
    
    checkAndCreateWorkspace()
    
    return () => {
      isMounted = false;
    }
  }, [profile, selectedWorkspace])

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages])
  
  const createUserWorkspace = async (userId: string) => {
    try {
      console.log("Creating workspace for user:", userId)
      const response = await fetch("/api/workspaces/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "개인 워크스페이스", user_id: userId }),
      })
      if (!response.ok) {
        throw new Error("워크스페이스 생성에 실패했습니다.")
      }
      const workspace = await response.json()
      console.log("Created workspace:", workspace)
      return workspace
    } catch (error) {
      console.error("Error creating workspace:", error)
      throw error
    }
  }

  // ==========================================================
  // 핸들러 및 렌더링 로직
  // ==========================================================

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0]
      if (file.type !== "application/pdf") {
        toast.error("PDF 파일만 업로드할 수 있습니다.")
        return
      }
      setSelectedFile(file)
    }
  }

  const handleUploadFile = async () => {
    if (!selectedFile) return
    setUploadStatus("uploading")
    toast.info("파일 업로드를 시작합니다...")
    const formData = new FormData()
    formData.append("file", selectedFile)
    try {
      const response = await fetch("/api/upload-pdf", {
        method: "POST",
        body: formData
      })
      if (!response.ok) {
        throw new Error("파일 업로드에 실패했습니다.")
      }
      const result = await response.json()
      setUploadStatus("success")
      toast.success(
        `파일 "${selectedFile.name}" 업로드 및 처리 성공! 이제 이 파일에 대해 질문할 수 있습니다.`
      )
      console.log("Upload result:", result)
    } catch (error) {
      console.error("File upload error:", error)
      setUploadStatus("error")
      toast.error(`파일 업로드 오류: ${error instanceof Error ? error.message : "알 수 없는 오류"}`)
    } finally {
      setSelectedFile(null)
      setTimeout(() => setUploadStatus("idle"), 3000)
    }
  }

  const handleSendQuery = async () => {
    const currentQuery = query.trim()
    if (!currentQuery || !profile) {
      console.log("Missing required data:", { hasQuery: !!currentQuery, hasProfile: !!profile })
      toast.error("필수 정보가 누락되었습니다.")
      return
    }

    const userMessage: Message = { sender: "user", content: currentQuery, type: "text" }
    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setQuery("")
    setLoading(true)

    let currentChat = chat
    let currentChatId = chatId

    try {
      // propChatId가 없을 때만 새 채팅 생성
      if (!currentChat && !propChatId) {
        console.log("Creating new chat for query:", currentQuery)
        const newChatRaw = await createRagChat({
          user_id: profile.id,
          workspace_id: workspaceId,
          name: currentQuery.substring(0, 100),
          messages: [userMessage],
          description: 'RAG 채팅',
          folder_id: null,
          sharing: 'private'
        })
        
        // messages를 Message[] 타입으로 변환
        const parsedMessages: Message[] = Array.isArray(newChatRaw.messages) 
          ? newChatRaw.messages 
          : newChatRaw.messages 
            ? JSON.parse(newChatRaw.messages as string)
            : []
        
        const newChat: RagChat = {
          ...newChatRaw,
          messages: parsedMessages
        }
        
        currentChat = newChat
        setChat(newChat)
        currentChatId = newChat.id
        setChatId(newChat.id)
        if (selectedWorkspace) {
          router.replace(`/${selectedWorkspace.id}/rag-chat/${newChat.id}`)
        }
      } else if (currentChat) {
        console.log("Using existing chat:", currentChat.id)
        currentChatId = currentChat.id
      } else if (propChatId) {
        console.log("Using prop chatId:", propChatId)
        currentChatId = propChatId
      }

      const result = await sendRagQuery(currentQuery, profile, workspaceId, currentChatId || undefined)
      
      const assistantMessage: Message = {
          sender: "assistant",
          content: result.text || result.react_code || result.dashboard_html,
          type: result.type
      }
      
      const finalMessages = [...newMessages, assistantMessage]
      setMessages(finalMessages)

      if (currentChatId) {
        await updateRagChat(currentChatId, { messages: finalMessages })
      }

    } catch (error) {
      console.error("Error sending RAG query:", error)
      const errorMessage: Message = {
          sender: "error",
          content: "오류가 발생했습니다. RAG 서비스에 연결할 수 없습니다.",
          type: "error"
      }
      setMessages((prev: Message[]) => [...prev, errorMessage])
      toast.error("RAG 서비스 연결에 실패했습니다.")
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (event: React.KeyboardEvent<Element>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      handleSendQuery()
    }
  }
  
  const renderMessageContent = (message: Message) => {
    if (message.type === "react") {
      return (
        <LiveProvider code={message.content} noInline>
          <LiveEditor />
          <LiveError />
          <LivePreview />
        </LiveProvider>
      )
    } else if (message.type === "dashboard") {
      return (
        <div dangerouslySetInnerHTML={{ __html: message.content }} />
      )
    } else {
      return <div className="whitespace-pre-wrap">{message.content}</div>
    }
  }

  // ==========================================================
  // 최종 JSX 렌더링
  // ==========================================================

  return (
    <div className="flex flex-col h-full">
      {/* 로딩 상태 표시 */}
      {isInitializing && (
        <div className="flex items-center justify-center p-4 bg-blue-50 border-b">
          <div className="flex items-center space-x-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span className="text-sm text-blue-600">초기화 중...</span>
          </div>
        </div>
      )}

      {loadingError && (
        <div className="flex items-center justify-center p-4 bg-yellow-50 border-b">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-yellow-600">{loadingError}</span>
          </div>
        </div>
      )}

      {/* 채팅 기록 로딩 중 */}
      {isHistoryLoading && (
        <div className="flex items-center justify-center p-4 bg-gray-50 border-b">
          <div className="flex items-center space-x-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
            <span className="text-sm text-gray-600">채팅 기록을 불러오는 중...</span>
          </div>
        </div>
      )}

      {/* 프로필이 없는 경우 */}
      {!profile && (
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">사용자 정보를 불러오는 중...</p>
          </div>
        </div>
      )}

      {/* 메인 채팅 인터페이스 */}
      {profile && (
        <>
          <div 
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto p-4 space-y-4"
          >
            {messages.length === 0 && !loading && !isHistoryLoading && (
              <div className="text-center py-12">
                <div className="max-w-md mx-auto">
                  <IconSearch className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-700 mb-2">뉴스에 대해 질문해보세요</h3>
                  <p className="text-gray-500 text-sm mb-6">
                    최신 뉴스, 기술 동향, 과학 발전 등에 대해 자유롭게 질문하세요.
                    AI가 관련 정보를 찾아서 답변해드립니다.
                  </p>
                  <div className="grid grid-cols-1 gap-3">
                    <button
                      onClick={() => setQuery("최근 AI 기술 동향에 대해 알려주세요")}
                      className="text-left p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
                    >
                      <p className="font-medium text-gray-800">최근 AI 기술 동향</p>
                      <p className="text-sm text-gray-600">AI 분야의 최신 발전 상황</p>
                    </button>
                    <button
                      onClick={() => setQuery("과학 기술 뉴스 요약해주세요")}
                      className="text-left p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
                    >
                      <p className="font-medium text-gray-800">과학 기술 뉴스</p>
                      <p className="text-sm text-gray-600">주요 과학 기술 소식</p>
                    </button>
                    <button
                      onClick={() => setQuery("환경 관련 최신 뉴스 알려주세요")}
                      className="text-left p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
                    >
                      <p className="font-medium text-gray-800">환경 관련 뉴스</p>
                      <p className="text-sm text-gray-600">기후 변화와 환경 보호</p>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {messages.map((message: Message, index: number) => (
              <div
                key={index}
                className={cn(
                  "flex items-start space-x-3",
                  message.sender === "user" ? "justify-end" : "justify-start"
                )}
              >
                {message.sender === "assistant" && (
                  <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                    <IconBrain className="h-4 w-4 text-white" />
                  </div>
                )}
                <div
                  className={cn(
                    "max-w-2xl rounded-2xl px-6 py-4 shadow-sm",
                    message.sender === "user"
                      ? "bg-gradient-to-r from-blue-500 to-purple-600 text-white"
                      : "bg-white border border-gray-200"
                  )}
                >
                  {renderMessageContent(message)}
                </div>
                {message.sender === "user" && (
                  <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-gray-500 to-gray-600 rounded-full flex items-center justify-center">
                    <IconFileText className="h-4 w-4 text-white" />
                  </div>
                )}
              </div>
            ))}
            
            {loading && (
              <div className="flex justify-start space-x-3">
                <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                  <IconBrain className="h-4 w-4 text-white" />
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl px-6 py-4 shadow-sm">
                  <div className="flex items-center space-x-2">
                    <div className="h-2 w-2 animate-pulse rounded-full bg-blue-500" style={{ animationDelay: '0s' }}></div>
                    <div className="h-2 w-2 animate-pulse rounded-full bg-blue-500" style={{ animationDelay: '0.2s' }}></div>
                    <div className="h-2 w-2 animate-pulse rounded-full bg-blue-500" style={{ animationDelay: '0.4s' }}></div>
                    <span className="text-sm text-gray-500 ml-2">AI가 답변을 생성하고 있습니다...</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 입력 영역 */}
          <div className="bg-white border-t border-gray-200 p-6">
            {selectedFile && (
              <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                <div className="flex items-center space-x-3">
                  <IconFileText className="h-5 w-5 text-blue-600" />
                  <span className="text-sm font-medium text-blue-900">
                    선택된 파일: <strong>{selectedFile.name}</strong>
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
                    onClick={handleUploadFile}
                    disabled={uploadStatus === "uploading"}
                  >
                    {uploadStatus === "uploading" ? "업로드 중..." : "업로드"}
                  </button>
                  <button
                    className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
                    onClick={() => setSelectedFile(null)}
                  >
                    취소
                  </button>
                </div>
              </div>
            )}
            
            <div className="flex items-end space-x-4">
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf"
                onChange={handleFileChange}
              />
              <WithTooltip
                display={<div>PDF 파일 첨부</div>}
                trigger={
                  <button
                    className="flex-shrink-0 p-3 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <IconCirclePlus className="h-5 w-5" />
                  </button>
                }
              />

              <div className="flex-1">
                <TextareaAutosize
                  value={query}
                  onValueChange={setQuery}
                  onKeyDown={handleKeyDown}
                  placeholder="뉴스에 대해 질문해보세요..."
                  className="w-full resize-none rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  minRows={1}
                  maxRows={4}
                />
              </div>

              <WithTooltip
                display={<div>전송</div>}
                trigger={
                  <button
                    className="flex-shrink-0 p-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    onClick={handleSendQuery}
                    disabled={loading || !query.trim()}
                  >
                    {loading ? (
                      <IconPlayerStop className="h-5 w-5" />
                    ) : (
                      <IconSend className="h-5 w-5" />
                    )}
                  </button>
                }
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}