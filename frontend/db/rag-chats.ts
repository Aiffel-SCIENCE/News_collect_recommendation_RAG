import { supabase } from "@/lib/supabase/browser-client"
import { RagChat } from "@/types/rag-chat"

export const getRagChatById = async (chatId: string) => {
  console.log("getRagChatById called with chatId:", chatId)
  
  try {
    const { data, error } = await supabase
      .from("rag_chats")
      .select("*")
      .eq("id", chatId)
      .single()

    console.log("Supabase query result:", { data, error })

    if (error) {
      console.error("Supabase error in getRagChatById:", error)
      throw new Error(error.message)
    }

    if (!data) {
      console.log("No chat found with id:", chatId)
      throw new Error("Chat not found")
    }

    console.log("Successfully retrieved chat:", data)
    return data
  } catch (err) {
    console.error("Error in getRagChatById:", err)
    throw err
  }
}

export const getRagChatsByWorkspaceId = async (workspaceId: string) => {
  const { data, error } = await supabase
    .from("rag_chats")
    .select("*")
    .eq("workspace_id", workspaceId)

  if (error) {
    throw new Error(error.message)
  }

  return data
}

export const createRagChat = async (chat: Omit<RagChat, "id" | "created_at" | "updated_at">) => {
  console.log("createRagChat called with data:", chat)
  
  const ragChat = {
    ...chat,
    description: chat.description || "RAG 채팅",
    sharing: chat.sharing || "private",
    messages: chat.messages as any
  }
  
  const { data, error } = await supabase
    .from("rag_chats")
    .insert([ragChat])
    .select()
    .single()

  console.log("Supabase insert result:", { data, error })

  if (error) {
    console.error("Supabase error in createRagChat:", error)
    throw new Error(error.message)
  }

  console.log("Successfully created chat:", data)
  return data
}

export const updateRagChat = async (
  chatId: string,
  updates: Partial<RagChat>
) => {
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
    throw new Error(error.message)
  }

  return data
}

export const deleteRagChat = async (chatId: string) => {
  const { error } = await supabase.from("rag_chats").delete().eq("id", chatId)

  if (error) {
    throw new Error(error.message)
  }

  return true
} 