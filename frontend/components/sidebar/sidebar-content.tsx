import { ContentType } from "@/types"
import { FC, useContext } from "react"
import { SidebarCreateButtons } from "./sidebar-create-buttons"
import { SidebarDataList } from "./sidebar-data-list"
import { SidebarSearch } from "./sidebar-search"
import { ChatbotUIContext } from "@/context/context"

interface SidebarContentProps {
  contentType: ContentType
  showSidebar: boolean
}

export const SidebarContent: FC<SidebarContentProps> = ({
  contentType,
  showSidebar
}) => {
  const {
    chats,
    newsChats,
    presets,
    prompts,
    files,
    collections,
    assistants,
    tools,
    models,
    folders
  } = useContext(ChatbotUIContext)

  const data = {
    chats,
    "news-chats": newsChats,
    presets,
    prompts,
    files,
    collections,
    assistants,
    tools,
    models
  }[contentType]

  const contentTypeFolders = folders.filter(
    folder => folder.type === contentType
  )

  if (!showSidebar) return null

  return (
    <div className="flex max-h-[calc(100%-50px)] grow flex-col">
      <div className="mt-2 flex items-center">
        <SidebarCreateButtons
          contentType={contentType}
          hasData={data.length > 0}
        />
      </div>

      <div className="mt-2">
        <SidebarSearch
          contentType={contentType}
          searchTerm=""
          setSearchTerm={() => {}}
        />
      </div>

      <SidebarDataList
        contentType={contentType}
        data={data}
        folders={contentTypeFolders}
      />
    </div>
  )
}
