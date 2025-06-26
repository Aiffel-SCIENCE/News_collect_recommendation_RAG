import Loading from "@/app/[locale]/loading"
import { useChatHandler } from "@/components/chat/chat-hooks/use-chat-handler"
import { ChatbotUIContext } from "@/context/context"
import { getAssistantToolsByAssistantId } from "@/db/assistant-tools"
import { getChatFilesByChatId } from "@/db/chat-files"
import { getChatById } from "@/db/chats"
import { getMessageFileItemsByMessageId } from "@/db/message-file-items"
import { getMessagesByChatId } from "@/db/messages"
import { getMessageImageFromStorage } from "@/db/storage/message-images"
import { convertBlobToBase64 } from "@/lib/blob-to-b64"
import useHotkey from "@/lib/hooks/use-hotkey"
import { Tables } from "@/supabase/types"
import { LLMID, MessageImage } from "@/types"
import { useParams } from "next/navigation"
import { FC, useContext, useEffect, useState, useCallback } from "react"
import { ChatHelp } from "./chat-help"
import { useScroll } from "./chat-hooks/use-scroll"
import { ChatInput } from "./chat-input"
import { ChatMessages } from "./chat-messages"
import { ChatScrollButtons } from "./chat-scroll-buttons"
import { ChatSecondaryButtons } from "./chat-secondary-buttons"
import { IconHome, IconInfoCircle, IconSettings } from "@tabler/icons-react"
import Link from "next/link"
import { WithTooltip } from "@/components/ui/with-tooltip"

interface ChatUIProps {}

// This component will handle the actual chat interface rendering
const ChatInterface: FC<{ chat: Tables<"chats"> }> = ({ chat }) => {
  const {
    messagesStartRef,
    messagesEndRef,
    handleScroll,
    scrollToBottom,
    isAtTop,
    isAtBottom,
    isOverflowing,
    scrollToTop
  } = useScroll()

  return (
    <div className="relative flex h-full flex-col items-center">
      <div className="absolute left-4 top-2.5 flex items-center">
        {/* Home Button */}
        <Link href="/" passHref>
          <WithTooltip display={<div>Home</div>} trigger={<IconHome className="cursor-pointer" size={26} />} />
        </Link>
        <div className="ml-2">
            <ChatScrollButtons
              isAtTop={isAtTop}
              isAtBottom={isAtBottom}
              isOverflowing={isOverflowing}
              scrollToTop={scrollToTop}
              scrollToBottom={scrollToBottom}
            />
        </div>
      </div>

      <div className="absolute right-4 top-1 flex h-[40px] items-center space-x-2">
        <ChatSecondaryButtons />
      </div>

      <div className="bg-secondary flex max-h-[50px] min-h-[50px] w-full items-center justify-center border-b-2 font-bold">
        <div className="max-w-[200px] truncate sm:max-w-[400px] md:max-w-[500px] lg:max-w-[600px] xl:max-w-[700px]">
          {chat.name || "Chat"}
        </div>
      </div>

      <div
        className="flex size-full flex-col overflow-auto border-b"
        onScroll={handleScroll}
      >
        <div ref={messagesStartRef} />
        <ChatMessages />
        <div ref={messagesEndRef} />
      </div>

      <div className="relative w-full min-w-[300px] items-end px-2 pb-3 pt-0 sm:w-[600px] sm:pb-8 sm:pt-5 md:w-[700px] lg:w-[700px] xl:w-[800px]">
        <ChatInput />
      </div>

      <ChatHelp />
    </div>
  )
}

export const ChatUI: FC<ChatUIProps> = () => {
  useHotkey("o", () => handleNewChat())
  const params = useParams()
  const {
    setChatMessages,
    selectedChat,
    setSelectedChat,
    setChatSettings,
    setChatImages,
    assistants,
    setSelectedAssistant,
    setChatFileItems,
    setChatFiles,
    setShowFilesDisplay,
    setUseRetrieval,
    setSelectedTools,
    chatMessages
  } = useContext(ChatbotUIContext)
  const { handleNewChat, handleFocusChatInput } = useChatHandler()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchMessages = useCallback(async (chatId: string) => {
    const fetchedMessages = await getMessagesByChatId(chatId)

    const imagePromises = (fetchedMessages
      .flatMap(message => message.image_paths)
      .filter(path => path) as string[]).map(
      async (imagePath: string): Promise<MessageImage> => {
        const url = await getMessageImageFromStorage(imagePath)
        // Find the message id associated with this image path
        const message = fetchedMessages.find(m => m.image_paths.includes(imagePath))
        
        if (!url) {
          return { messageId: message!.id, path: imagePath, base64: "", url: "", file: null }
        }
        
        const response = await fetch(url)
        if (!response.ok) {
          return { messageId: message!.id, path: imagePath, base64: "", url: "", file: null }
        }

        const blob = await response.blob()
        const base64 = await convertBlobToBase64(blob)
        return { messageId: message!.id, path: imagePath, base64, url, file: null }
      }
    )
    const images: MessageImage[] = await Promise.all(imagePromises)
    setChatImages(images)

    const messageFileItemPromises = fetchedMessages.map(
      async message => await getMessageFileItemsByMessageId(message.id)
    )
    const messageFileItems = await Promise.all(messageFileItemPromises)
    const uniqueFileItems = messageFileItems.flatMap(item => item.file_items)
    setChatFileItems(uniqueFileItems)

    const chatFiles = await getChatFilesByChatId(chatId)
    setChatFiles(chatFiles.files.map(file => ({ id: file.id, name: file.name, type: file.type, file: null })))
    if (chatFiles.files.length > 0) {
      setUseRetrieval(true)
      setShowFilesDisplay(true)
    }

    const fetchedChatMessages = fetchedMessages.map(message => ({
      message,
      fileItems: messageFileItems
        .filter(mf => mf.id === message.id)
        .flatMap(mf => mf.file_items.map(fi => fi.id))
    }))
    setChatMessages(fetchedChatMessages)
  }, [setChatImages, setChatFileItems, setChatFiles, setUseRetrieval, setShowFilesDisplay, setChatMessages])

  const fetchChat = useCallback(async (chatId: string) => {
    let chat: Tables<"chats"> | null = null;
    let retries = 3; // Try a total of 3 times

    while (retries > 0 && !chat) {
        chat = await getChatById(chatId);
        if (chat) break;
        
        retries--;
        if (retries > 0) {
            await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
        }
    }
    
    if (!chat) {
      throw new Error("Chat not found after multiple retries.")
    }

    const currentChat = chat

    if (currentChat.assistant_id) {
      const assistant = assistants.find(a => a.id === currentChat.assistant_id)
      if (assistant) {
        setSelectedAssistant(assistant)
        const assistantTools = (
          await getAssistantToolsByAssistantId(assistant.id)
        ).tools
        setSelectedTools(assistantTools)
      }
    }

    setSelectedChat(currentChat)
    setChatSettings({
      model: currentChat.model as LLMID,
      prompt: currentChat.prompt,
      temperature: currentChat.temperature,
      contextLength: currentChat.context_length,
      includeProfileContext: currentChat.include_profile_context,
      includeWorkspaceInstructions: currentChat.include_workspace_instructions,
      embeddingsProvider: currentChat.embeddings_provider as "openai" | "local"
    })
    return currentChat
  }, [
    assistants,
    setSelectedAssistant,
    setSelectedTools,
    setSelectedChat,
    setChatSettings
  ])
  
  const resetChatState = useCallback(() => {
    setSelectedChat(null)
    setChatMessages([])
    setChatFileItems([])
    setChatFiles([])
    setChatImages([])
    setSelectedTools([])
    setShowFilesDisplay(false)
    setUseRetrieval(false)
  }, [/* list all setters from context */
    setSelectedChat, setChatMessages, setChatFileItems, setChatFiles, 
    setChatImages, setSelectedTools, setShowFilesDisplay, setUseRetrieval
  ])


  useEffect(() => {
    if (!params.chatid) {
      // If there is no chatid, we are on the base chat page
      resetChatState()
      setLoading(false)
      return
    }

    if (assistants.length === 0) {
      // Wait for assistants to be loaded
      setLoading(true)
      return
    }

    const chatId = params.chatid as string

    // If the chat is already selected and it's the correct one, do nothing.
    if (selectedChat && selectedChat.id === chatId) {
      setLoading(false)
      return;
    }

    setLoading(true)
    setError(null)
    resetChatState()

    const fetchData = async () => {
      try {
        const chat = await fetchChat(chatId)
        if (chat) {
          await fetchMessages(chatId)
        }
      } catch (err: any) {
        setError(err.message || "Failed to fetch chat data.")
      } finally {
        setLoading(false)
        handleFocusChatInput()
      }
    }

    fetchData()
  }, [
    params.chatid,
    assistants,
    selectedChat,
    fetchChat,
    fetchMessages,
    resetChatState,
    handleFocusChatInput
  ])

  if (loading) {
    return <Loading />
  }

  if (error) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center">
        <div className="text-2xl">오류</div>
        <div className="text-red-500">{error}</div>
        <button
          className="mt-4 rounded-md bg-blue-500 px-4 py-2 text-white"
          onClick={() => (window.location.href = "/")}
        >
          홈으로 돌아가기
        </button>
      </div>
    )
  }
  
  // If there's a chat id in url, but no selected chat, it means we are in a loading/error state handled above
  if (params.chatid && !selectedChat) {
    return <Loading />
  }
  
  // If no chat is selected (e.g., creating a new one), show the helper.
  if (!selectedChat) {
    return <ChatHelp />
  }

  // Once chat is loaded, render the main interface
  return <ChatInterface chat={selectedChat} />
}
