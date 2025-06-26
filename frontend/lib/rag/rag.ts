import { Tables } from "@/supabase/types"

export const sendRagQuery = async (
  query: string,
  profile: Tables<"profiles">,
  workspaceId: string,
  chatId?: string
) => {
  const response = await fetch("/api/rag", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ 
      query, 
      profileId: profile.id,
      workspaceId,
      chatId
    })
  })

  if (!response.ok) {
    throw new Error("Failed to send RAG query")
  }

  return response.json()
} 