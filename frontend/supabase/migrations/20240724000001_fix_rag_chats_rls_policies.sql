-- 기존 RLS 정책 삭제
DROP POLICY IF EXISTS "Allow full access to own chats" ON public.rag_chats;

-- 새로운 RLS 정책 생성
CREATE POLICY "Users can view own chats"
ON public.rag_chats
FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own chats"
ON public.rag_chats
FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own chats"
ON public.rag_chats
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own chats"
ON public.rag_chats
FOR DELETE
USING (auth.uid() = user_id); 