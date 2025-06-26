export interface Message {
  sender: "user" | "assistant" | "error"
  content: any
  type?: "react" | "dashboard" | "text" | "error" | "file"
  file_name?: string
  file_url?: string
}

export interface RagChat {
  id: string
  user_id: string
  workspace_id: string
  name: string
  messages: Message[]
  description: string
  folder_id: string | null
  sharing: string
  created_at: string
  updated_at: string
} 