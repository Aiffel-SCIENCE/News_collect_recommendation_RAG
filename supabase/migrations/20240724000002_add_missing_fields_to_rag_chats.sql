-- Add missing fields to rag_chats table for DataListType compatibility
ALTER TABLE public.rag_chats 
ADD COLUMN description text DEFAULT '',
ADD COLUMN folder_id uuid REFERENCES public.folders(id) ON UPDATE CASCADE ON DELETE SET NULL,
ADD COLUMN sharing text DEFAULT 'private';

-- Update existing records to have default values
UPDATE public.rag_chats 
SET description = '뉴스 질문 채팅',
    sharing = 'private'
WHERE description IS NULL OR sharing IS NULL; 