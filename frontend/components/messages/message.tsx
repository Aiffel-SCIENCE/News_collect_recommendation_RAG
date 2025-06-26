import { useChatHandler } from "@/components/chat/chat-hooks/use-chat-handler"
import { ChatbotUIContext } from "@/context/context"
import { LLM_LIST } from "@/lib/models/llm/llm-list"
import { cn } from "@/lib/utils"
import { Tables } from "@/supabase/types"
import { LLM, LLMID, MessageImage, ModelProvider } from "@/types"
import {
  IconBolt,
  IconCaretDownFilled,
  IconCaretRightFilled,
  IconCircleFilled,
  IconFileText,
  IconMoodSmile,
  IconPencil
} from "@tabler/icons-react"
import Image from "next/image"
import { FC, useContext, useEffect, useRef, useState } from "react"
import { ModelIcon } from "../models/model-icon"
import { Button } from "../ui/button"
import { FileIcon } from "../ui/file-icon"
import { FilePreview } from "../ui/file-preview"
import { TextareaAutosize } from "../ui/textarea-autosize"
import { WithTooltip } from "../ui/with-tooltip"
import { MessageActions } from "./message-actions"
import { MessageMarkdown } from "./message-markdown"

const ICON_SIZE = 32

interface MessageProps {
  message: Tables<"messages">
  fileItems: Tables<"file_items">[]
  isEditing: boolean
  isLast: boolean
  onStartEdit: (message: Tables<"messages">) => void
  onCancelEdit: () => void
  onSubmitEdit: (value: string, sequenceNumber: number) => void
}

export const Message: FC<MessageProps> = ({
  message,
  fileItems,
  isEditing,
  isLast,
  onStartEdit,
  onCancelEdit,
  onSubmitEdit
}) => {
  const {
    assistants,
    profile,
    isGenerating,
    setIsGenerating,
    firstTokenReceived,
    availableLocalModels,
    availableOpenRouterModels,
    chatMessages,
    selectedAssistant,
    chatImages,
    assistantImages,
    toolInUse,
    files,
    models
  } = useContext(ChatbotUIContext)

  const { handleSendMessage } = useChatHandler()

  const editInputRef = useRef<HTMLTextAreaElement>(null)

  const [isHovering, setIsHovering] = useState(false)
  const [editedMessage, setEditedMessage] = useState(message.content)

  const [showImagePreview, setShowImagePreview] = useState(false)
  const [selectedImage, setSelectedImage] = useState<MessageImage | null>(null)

  const [selectedFileItem, setSelectedFileItem] =
    useState<Tables<"file_items"> | null>(null)
  const [showFileItemPreview, setShowFileItemPreview] = useState(false)

  const [viewSources, setViewSources] = useState(false)

  const handleCopy = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(message.content)
    } else {
      const textArea = document.createElement("textarea")
      textArea.value = message.content
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      document.execCommand("copy")
      document.body.removeChild(textArea)
    }
  }

  const handleSendEdit = () => {
    onSubmitEdit(editedMessage, message.sequence_number)
    onCancelEdit()
  }

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (isEditing && event.key === "Enter" && event.metaKey) {
      handleSendEdit()
    }
  }

  const handleRegenerate = async () => {
    setIsGenerating(true)
    await handleSendMessage(
      editedMessage || chatMessages[chatMessages.length - 2].message.content,
      chatMessages,
      true
    )
  }

  const handleStartEdit = () => {
    onStartEdit(message)
  }

  useEffect(() => {
    setEditedMessage(message.content)

    if (isEditing && editInputRef.current) {
      const input = editInputRef.current
      input.focus()
      input.setSelectionRange(input.value.length, input.value.length)
    }
  }, [isEditing, message.content])

  const MODEL_DATA = [
    ...models.map(model => ({
      modelId: model.model_id as LLMID,
      modelName: model.name,
      provider: "custom" as ModelProvider,
      hostedId: model.id,
      platformLink: "",
      imageInput: false
    })),
    ...LLM_LIST,
    ...availableLocalModels,
    ...availableOpenRouterModels
  ].find(llm => llm.modelId === message.model) as LLM

  const messageAssistantImage = assistantImages.find(
    image => image.assistantId === message.assistant_id
  )?.base64

  const selectedAssistantImage = assistantImages.find(
    image => image.path === selectedAssistant?.image_path
  )?.base64

  const modelDetails = LLM_LIST.find(model => model.modelId === message.model)

  const fileAccumulator: Record<
    string,
    {
      id: string
      name: string
      count: number
      type: string
      description: string
    }
  > = {}

  const fileSummary = fileItems.reduce((acc, fileItem) => {
    const parentFile = files.find(file => file.id === fileItem.file_id)
    if (parentFile) {
      if (!acc[parentFile.id]) {
        acc[parentFile.id] = {
          id: parentFile.id,
          name: parentFile.name,
          count: 1,
          type: parentFile.type,
          description: parentFile.description
        }
      } else {
        acc[parentFile.id].count += 1
      }
    }
    return acc
  }, fileAccumulator)

  return (
    <div
      className={cn(
        "flex w-full justify-center",
        message.role === "user" ? "" : "bg-secondary"
      )}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
      onKeyDown={handleKeyDown}
    >
      <div className="relative flex w-full flex-col p-6 sm:w-[550px] sm:px-0 md:w-[650px] lg:w-[650px] xl:w-[700px]">
        <div className="absolute right-5 top-7 sm:right-0">
          <MessageActions
            onCopy={handleCopy}
            onEdit={handleStartEdit}
            isAssistant={message.role === "assistant"}
            isLast={isLast}
            isEditing={isEditing}
            isHovering={isHovering}
            onRegenerate={handleRegenerate}
          />
        </div>
        <div className="space-y-3">
          {message.role === "system" ? (
            <div className="flex items-center space-x-4">
              <IconPencil
                className="border-primary bg-primary text-secondary rounded border-DEFAULT p-1"
                size={ICON_SIZE}
              />

              <div className="text-lg font-semibold">Prompt</div>
            </div>
          ) : (
            <div className="flex items-start space-x-4">
              <WithTooltip
                display={
                  <div>
                    {MODEL_DATA?.modelName ||
                      selectedAssistant?.name ||
                      "Model"}
                  </div>
                }
                trigger={
                  message.role === "assistant" ? (
                    <ModelIcon
                      provider={
                        MODEL_DATA?.provider ||
                        (selectedAssistant
                          ? "custom"
                          : "custom")
                      }
                      height={ICON_SIZE}
                      width={ICON_SIZE}
                    />
                  ) : profile?.image_url ? (
                    <Image
                      className="rounded"
                      src={profile.image_url}
                      alt="profile image"
                      height={ICON_SIZE}
                      width={ICON_SIZE}
                    />
                  ) : (
                    <div
                      className="bg-primary text-secondary flex size-[32px] items-center justify-center rounded"
                      style={{
                        backgroundColor: profile?.profile_context
                          ? "transparent"
                          : "#a745a7"
                      }}
                    >
                      <IconMoodSmile />
                    </div>
                  )
                }
              />

              <div className="flex-1 space-y-4">
                {isEditing ? (
                  <div className="flex-1">
                    <TextareaAutosize
                      textareaRef={editInputRef}
                      className="bg-transparent"
                      value={editedMessage}
                      onValueChange={setEditedMessage}
                      maxRows={20}
                    />

                    <div className="mt-2 flex justify-end space-x-2">
                      <Button size="sm" onClick={onCancelEdit}>
                        Cancel
                      </Button>

                      <Button size="sm" onClick={handleSendEdit}>
                        Save
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 space-y-4">
                    <MessageMarkdown content={message.content} />

                    {fileItems.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {Object.values(fileSummary).map(file => (
                          <div
                            key={file.id}
                            className="flex cursor-pointer items-center space-x-2"
                          >
                            <FileIcon type={file.type} />

                            <div className="truncate text-sm">
                              {file.name}
                              {file.count > 1 && ` (${file.count})`}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {message.role === "assistant" &&
                      message.message_files.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {message.message_files.map(fileId => {
                            const file = files.find(f => f.id === fileId)
                            if (!file) return null

                            return (
                              <div
                                key={file.id}
                                className="flex cursor-pointer items-center space-x-2"
                              >
                                <FileIcon type={file.type} />

                                <div className="truncate text-sm">
                                  {file.name}
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}

                    {chatImages
                      .filter(image => image.messageId === message.id)
                      .map((image, index) => (
                        <Image
                          key={image.path}
                          className="cursor-pointer rounded hover:opacity-50"
                          src={image.base64}
                          alt="message image"
                          width={300}
                          height={300}
                          onClick={() => {
                            setSelectedImage(image)
                            setShowImagePreview(true)
                          }}
                          onKeyDown={(e: any) => {
                            if (e.key === "Enter") {
                              setSelectedImage(image)
                              setShowImagePreview(true)
                            }
                          }}
                        />
                      ))}

                    {showImagePreview && selectedImage && (
                      <FilePreview
                        type="image"
                        item={selectedImage}
                        isOpen={showImagePreview}
                        onOpenChange={setShowImagePreview}
                      />
                    )}

                    {message.role === "assistant" &&
                      fileItems.length > 0 &&
                      toolInUse === "retrieval" && (
                        <>
                          <div
                            className="flex cursor-pointer items-center space-x-1"
                            onClick={() => setViewSources(!viewSources)}
                          >
                            <IconBolt size={20} />
                            <div>
                              {viewSources
                                ? "Hide"
                                : `View ${fileItems.length} sources`}
                            </div>
                            {viewSources ? (
                              <IconCaretDownFilled size={20} />
                            ) : (
                              <IconCaretRightFilled size={20} />
                            )}
                          </div>

                          {viewSources && (
                            <div className="mt-1 space-y-2">
                              {fileItems.map(fileItem => {
                                const parentFile = files.find(
                                  file => file.id === fileItem.file_id
                                )

                                if (!parentFile) return null

                                return (
                                  <div
                                    key={fileItem.id}
                                    className="flex cursor-pointer items-center space-x-2"
                                    onClick={() => {
                                      setSelectedFileItem(fileItem)
                                      setShowFileItemPreview(true)
                                    }}
                                  >
                                    <FileIcon type={parentFile.type} />

                                    <div className="truncate text-sm">
                                      {parentFile.name}
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </>
                      )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {showImagePreview && selectedImage && (
        <FilePreview
          type="image"
          item={selectedImage}
          isOpen={showImagePreview}
          onOpenChange={setShowImagePreview}
        />
      )}

      {showFileItemPreview && selectedFileItem && (
        <FilePreview
          type="file_item"
          item={selectedFileItem}
          isOpen={showFileItemPreview}
          onOpenChange={isOpen => {
            setShowFileItemPreview(isOpen)
            if (!isOpen) {
              setSelectedFileItem(null)
            }
          }}
        />
      )}
    </div>
  )
}
