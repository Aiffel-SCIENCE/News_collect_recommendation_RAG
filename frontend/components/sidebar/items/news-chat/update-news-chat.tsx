import { updateNewsChat } from "@/db/news-chats"
import { ChatbotUIContext } from "@/context/context"
import { Tables } from "@/supabase/types"
import { IconEdit } from "@tabler/icons-react"
import { FC, useContext, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog"

interface UpdateNewsChatProps {
  chat: Tables<"rag_chats">
}

export const UpdateNewsChat: FC<UpdateNewsChatProps> = ({ chat }) => {
  const { setNewsChats } = useContext(ChatbotUIContext)
  const [showDialog, setShowDialog] = useState(false)
  const [name, setName] = useState(chat.name)

  const handleUpdate = async () => {
    try {
      await updateNewsChat(chat.id, { name })
      setNewsChats(prevChats => 
        prevChats.map(c => c.id === chat.id ? { ...c, name } : c)
      )
      setShowDialog(false)
    } catch (error) {
      console.error("Error updating news chat:", error)
    }
  }

  return (
    <Dialog open={showDialog} onOpenChange={setShowDialog}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon">
          <IconEdit size={16} />
        </Button>
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>뉴스 채팅 이름 수정</DialogTitle>
          <DialogDescription>
            뉴스 채팅의 이름을 수정하세요.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <Input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="채팅 이름을 입력하세요"
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setShowDialog(false)}>
            취소
          </Button>
          <Button onClick={handleUpdate}>수정</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
} 