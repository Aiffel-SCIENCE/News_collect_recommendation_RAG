import { WithTooltip } from "@/components/ui/with-tooltip"
import { ChatbotUIContext } from "@/context/context"
import { cn } from "@/lib/utils"
import { Tables } from "@/supabase/types"
import { IconRobotFace, IconNews } from "@tabler/icons-react"
import { useParams, useRouter } from "next/navigation"
import { FC, useContext, useRef } from "react"
import { DeleteNewsChat } from "./delete-news-chat"
import { UpdateNewsChat } from "./update-news-chat"

interface NewsChatItemProps {
  chat: Tables<"rag_chats">
}

export const NewsChatItem: FC<NewsChatItemProps> = ({ chat }) => {
  const { selectedWorkspace } = useContext(ChatbotUIContext)

  const router = useRouter()
  const params = useParams()
  const isActive = params.chatid === chat.id

  const itemRef = useRef<HTMLDivElement>(null)

  const handleClick = () => {
    if (!selectedWorkspace) return
    return router.push(`/${selectedWorkspace.id}/news-chat/${chat.id}`)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter") {
      e.stopPropagation()
      itemRef.current?.click()
    }
  }

  return (
    <div
      ref={itemRef}
      className={cn(
        "hover:bg-accent focus:bg-accent group flex w-full cursor-pointer items-center rounded p-2 hover:opacity-50 focus:outline-none",
        isActive && "bg-accent"
      )}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onClick={handleClick}
    >
      <IconNews
        className="bg-primary text-secondary border-primary rounded border-DEFAULT p-1"
        size={30}
      />

      <div className="ml-3 flex-1 truncate text-sm font-semibold">
        {chat.name}
      </div>

      <div
        onClick={e => {
          e.stopPropagation()
          e.preventDefault()
        }}
        className={`ml-2 flex space-x-2 ${!isActive && "w-11 opacity-0 group-hover:opacity-100"}`}
      >
        <UpdateNewsChat chat={chat} />
        <DeleteNewsChat chat={chat} />
      </div>
    </div>
  )
} 