import { supabase } from "@/lib/supabase/browser-client"
import { RagChat } from "@/types/rag-chat"

export const getNewsChatById = async (chatId: string) => {
  console.log("getNewsChatById called with chatId:", chatId)
  
  try {
    const { data, error } = await supabase
      .from("rag_chats")
      .select("*")
      .eq("id", chatId)
      .eq("name", "뉴스 질문")
      .maybeSingle()

    console.log("Supabase query result:", { data, error })

    if (error && error.code !== 'PGRST116') {
      console.error("Supabase error in getNewsChatById:", error)
      throw new Error(error.message)
    }

    if (!data) {
      console.log("No news chat found with id:", chatId)
      return null
    }

    console.log("Successfully retrieved news chat:", data)
    return data
  } catch (err) {
    console.error("Error in getNewsChatById:", err)
    throw err
  }
}

export const getNewsChatsByWorkspaceId = async (workspaceId: string) => {
  console.log("getNewsChatsByWorkspaceId called with workspaceId:", workspaceId)
  
  const { data, error } = await supabase
    .from("rag_chats")
    .select("*")
    .eq("workspace_id", workspaceId)
    .order("updated_at", { ascending: false })

  if (error) {
    console.error("Supabase error in getNewsChatsByWorkspaceId:", error)
    throw new Error(error.message)
  }

  console.log("Successfully retrieved news chats:", data)
  return data
}

export const createNewsChat = async (chat: Omit<RagChat, "id" | "created_at" | "updated_at">) => {
  console.log("createNewsChat called with data:", chat)
  
  // 뉴스 채팅으로 이름 설정하고 기본값 추가
  const newsChat = {
    ...chat,
    name: "뉴스 질문",
    description: chat.description || "뉴스 질문 채팅",
    sharing: chat.sharing || "private",
    messages: chat.messages as any
  }
  
  const { data, error } = await supabase
    .from("rag_chats")
    .insert([newsChat])
    .select()
    .single()

  console.log("Supabase insert result:", { data, error })

  if (error) {
    console.error("Supabase error in createNewsChat:", error)
    throw new Error(error.message)
  }

  console.log("Successfully created news chat:", data)
  return data
}

export const updateNewsChat = async (
  chatId: string,
  updates: Partial<RagChat>
) => {
  console.log("updateNewsChat called with chatId:", chatId, "updates:", updates)
  
  const updateData = {
    ...updates,
    ...(updates.messages && { messages: updates.messages as any })
  }
  
  const { data, error } = await supabase
    .from("rag_chats")
    .update(updateData)
    .eq("id", chatId)
    .select()
    .single()

  if (error) {
    console.error("Supabase error in updateNewsChat:", error)
    throw new Error(error.message)
  }

  console.log("Successfully updated news chat:", data)
  return data
}

export const deleteNewsChat = async (chatId: string) => {
  console.log("deleteNewsChat called with chatId:", chatId)
  
  const { error } = await supabase
    .from("rag_chats")
    .delete()
    .eq("id", chatId)

  if (error) {
    console.error("Supabase error in deleteNewsChat:", error)
    throw new Error(error.message)
  }

  console.log("Successfully deleted news chat:", chatId)
}

export const addMessageToNewsChat = async (
  chatId: string,
  message: RagChat["messages"][0]
) => {
  console.log("addMessageToNewsChat called with chatId:", chatId, "message:", message)
  
  // 먼저 현재 채팅을 가져옴
  const currentChat = await getNewsChatById(chatId)

  if (!currentChat) {
    throw new Error(`Chat with id ${chatId} not found.`)
  }
  
  // messages를 Message[] 타입으로 변환
  const currentMessages: RagChat["messages"] = Array.isArray(currentChat.messages) 
    ? currentChat.messages 
    : currentChat.messages 
      ? JSON.parse(currentChat.messages as string)
      : []
  
  // 새 메시지 추가
  const updatedMessages = [...currentMessages, message]
  
  // 채팅 업데이트
  return updateNewsChat(chatId, {
    messages: updatedMessages,
    updated_at: new Date().toISOString()
  })
} 