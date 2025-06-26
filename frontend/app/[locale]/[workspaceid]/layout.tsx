"use client"

import { Dashboard } from "@/components/ui/dashboard"
import { ChatbotUIContext } from "@/context/context"
import { getAssistantWorkspacesByWorkspaceId } from "@/db/assistants"
import { getChatsByWorkspaceId } from "@/db/chats"
import { getCollectionWorkspacesByWorkspaceId } from "@/db/collections"
import { getFileWorkspacesByWorkspaceId } from "@/db/files"
import { getFoldersByWorkspaceId } from "@/db/folders"
import { getModelWorkspacesByWorkspaceId } from "@/db/models"
import { getPresetWorkspacesByWorkspaceId } from "@/db/presets"
import { getPromptWorkspacesByWorkspaceId } from "@/db/prompts"
import { getAssistantImageFromStorage } from "@/db/storage/assistant-images"
import { getToolWorkspacesByWorkspaceId } from "@/db/tools"
import { getWorkspaceById, getHomeWorkspaceByUserId } from "@/db/workspaces"
import { convertBlobToBase64 } from "@/lib/blob-to-b64"
import { supabase } from "@/lib/supabase/browser-client"
import { LLMID } from "@/types"
import { useParams, useRouter, useSearchParams } from "next/navigation"
import { ReactNode, useContext, useEffect, useState } from "react"
import Loading from "../loading"

interface WorkspaceLayoutProps {
  children: ReactNode
}

// UUID 유효성 검사 함수
function isValidUUID(uuid: string): boolean {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
  return uuidRegex.test(uuid)
}

export default function WorkspaceLayout({ children }: WorkspaceLayoutProps) {
  const router = useRouter()

  const params = useParams()
  const searchParams = useSearchParams()
  const workspaceId = params.workspaceid as string

  const {
    setChatSettings,
    setAssistants,
    setAssistantImages,
    setChats,
    setCollections,
    setFolders,
    setFiles,
    setPresets,
    setPrompts,
    setTools,
    setModels,
    selectedWorkspace,
    setSelectedWorkspace,
    setSelectedChat,
    setChatMessages,
    setUserInput,
    setIsGenerating,
    setFirstTokenReceived,
    setChatFiles,
    setChatImages,
    setNewMessageFiles,
    setNewMessageImages,
    setShowFilesDisplay
  } = useContext(ChatbotUIContext)

  const [loading, setLoading] = useState(true)
  const [loadingError, setLoadingError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true;
    
    ;(async () => {
      try {
        const session = (await supabase.auth.getSession()).data.session

        if (!session) {
          if (isMounted) {
            return router.push("/login")
          }
          return;
        }

        if (!isValidUUID(workspaceId)) {
          console.warn(
            `Invalid workspace ID: ${workspaceId}, redirecting to home workspace`
          )
          try {
            const homeWorkspaceId = await getHomeWorkspaceByUserId(
              session.user.id
            )
            if (isMounted) {
              return router.push(`/${homeWorkspaceId}/chat`)
            }
          } catch (error) {
            console.error("Failed to get home workspace:", error)
            if (isMounted) {
              return router.push("/setup")
            }
          }
        }

        // 타임아웃 설정 (15초)
        const timeoutId = setTimeout(() => {
          if (isMounted) {
            console.log("Workspace data fetch timeout, proceeding anyway")
            setLoading(false)
            setLoadingError("워크스페이스 데이터 로딩 시간이 초과되었습니다.")
          }
        }, 15000)

        await fetchWorkspaceData(workspaceId)

        if (isMounted) {
          clearTimeout(timeoutId)

          setUserInput("")
          setChatMessages([])
          setSelectedChat(null)

          setIsGenerating(false)
          setFirstTokenReceived(false)

          setChatFiles([])
          setChatImages([])
          setNewMessageFiles([])
          setNewMessageImages([])
          setShowFilesDisplay(false)
        }
      } catch (error) {
        console.error("Error in workspace layout initialization:", error)
        if (isMounted) {
          setLoadingError("워크스페이스 초기화 중 오류가 발생했습니다.")
          setLoading(false)
        }
      }
    })()

    return () => {
      isMounted = false;
    }
  }, [workspaceId]) // selectedWorkspace 의존성 제거

  const fetchWorkspaceData = async (workspaceId: string) => {
    setLoading(true)
    setLoadingError(null)

    try {
      const workspace = await getWorkspaceById(workspaceId)
      setSelectedWorkspace(workspace)

      const results = await Promise.allSettled([
        getAssistantWorkspacesByWorkspaceId(workspaceId).then(data => {
          setAssistants(data.assistants)
          return data.assistants
        }),
        getChatsByWorkspaceId(workspaceId),
        getCollectionWorkspacesByWorkspaceId(workspaceId),
        getFoldersByWorkspaceId(workspaceId),
        getFileWorkspacesByWorkspaceId(workspaceId),
        getPresetWorkspacesByWorkspaceId(workspaceId),
        getPromptWorkspacesByWorkspaceId(workspaceId),
        getToolWorkspacesByWorkspaceId(workspaceId),
        getModelWorkspacesByWorkspaceId(workspaceId)
      ])

      // Handle assistants and their images
      if (results[0].status === "fulfilled") {
        const assistants = results[0].value
        setAssistantImages([]) // Clear previous images
        const imagePromises = assistants.map(async (assistant: any) => {
          if (!assistant.image_path) return null
          try {
            const url = await getAssistantImageFromStorage(assistant.image_path) || ""
            if (!url) return null
            const response = await fetch(url)
            if (!response.ok) return null
            const blob = await response.blob()
            const base64 = await convertBlobToBase64(blob)
            return { assistantId: assistant.id, path: assistant.image_path, base64, url }
          } catch (error) {
            console.error(`Error fetching image for assistant ${assistant.id}:`, error)
            return null
          }
        })
        const imageData = (await Promise.all(imagePromises)).filter((img: any) => img !== null)
        // @ts-ignore
        setAssistantImages(imageData)
      }

      // Handle other data types
      if (results[1].status === "fulfilled") setChats(results[1].value)
      if (results[2].status === "fulfilled") setCollections(results[2].value.collections)
      if (results[3].status === "fulfilled") setFolders(results[3].value)
      if (results[4].status === "fulfilled") setFiles(results[4].value.files)
      if (results[5].status === "fulfilled") setPresets(results[5].value.presets)
      if (results[6].status === "fulfilled") setPrompts(results[6].value.prompts)
      if (results[7].status === "fulfilled") setTools(results[7].value.tools)
      if (results[8].status === "fulfilled") setModels(results[8].value.models)
      
      results.forEach((result, index) => {
        if (result.status === "rejected") {
          console.error(`Failed to fetch data at index ${index}:`, result.reason)
        }
      })

      setChatSettings({
        model: (searchParams.get("model") ||
          workspace?.default_model ||
          "gpt-4-1106-preview") as LLMID,
        prompt:
          workspace?.default_prompt ||
          "You are a friendly, helpful AI assistant.",
        temperature: workspace?.default_temperature || 0.5,
        contextLength: workspace?.default_context_length || 4096,
        includeProfileContext: workspace?.include_profile_context || true,
        includeWorkspaceInstructions:
          workspace?.include_workspace_instructions || true,
        embeddingsProvider:
          (workspace?.embeddings_provider as "openai" | "local") || "openai"
      })
    } catch (error) {
      console.error("Error fetching workspace data:", error)
      setLoadingError("워크스페이스 데이터를 불러오는데 실패했습니다.")
      // 워크스페이스를 찾을 수 없는 경우 홈 워크스페이스로 리다이렉트
      try {
        const session = (await supabase.auth.getSession()).data.session
        if (session) {
          const homeWorkspaceId = await getHomeWorkspaceByUserId(session.user.id)
          router.push(`/${homeWorkspaceId}/chat`)
        }
      } catch (redirectError) {
        console.error("Failed to redirect to home workspace:", redirectError)
        router.push("/setup")
      }
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex size-full flex-col items-center justify-center">
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="text-lg text-gray-600">워크스페이스를 불러오는 중...</span>
        </div>
        {loadingError && (
          <div className="mt-4 text-sm text-red-600">{loadingError}</div>
        )}
      </div>
    )
  }

  return <Dashboard>{children}</Dashboard>
}
