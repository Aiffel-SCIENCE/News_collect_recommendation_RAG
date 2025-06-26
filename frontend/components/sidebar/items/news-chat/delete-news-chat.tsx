import { deleteNewsChat } from "@/db/news-chats"
import { ChatbotUIContext } from "@/context/context"
import { Tables } from "@/supabase/types"
import { IconTrash } from "@tabler/icons-react"
import { FC, useContext, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger
} from "@/components/ui/alert-dialog"

interface DeleteNewsChatProps {
  chat: Tables<"rag_chats">
}

export const DeleteNewsChat: FC<DeleteNewsChatProps> = ({ chat }) => {
  const { setNewsChats } = useContext(ChatbotUIContext)
  const [showAlertDialog, setShowAlertDialog] = useState(false)

  const handleDelete = async () => {
    try {
      await deleteNewsChat(chat.id)
      setNewsChats(prevChats => prevChats.filter(c => c.id !== chat.id))
      setShowAlertDialog(false)
    } catch (error) {
      console.error("Error deleting news chat:", error)
    }
  }

  return (
    <AlertDialog open={showAlertDialog} onOpenChange={setShowAlertDialog}>
      <AlertDialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="hover:bg-red-500 hover:text-white"
        >
          <IconTrash size={16} />
        </Button>
      </AlertDialogTrigger>

      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>뉴스 채팅 삭제</AlertDialogTitle>
          <AlertDialogDescription>
            이 뉴스 채팅을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <AlertDialogFooter>
          <AlertDialogCancel>취소</AlertDialogCancel>
          <AlertDialogAction onClick={handleDelete} className="bg-red-500">
            삭제
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
} 