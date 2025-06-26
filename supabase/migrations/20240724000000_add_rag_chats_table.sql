CREATE TABLE public.rag_chats (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    name text NOT NULL,
    messages jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT rag_chats_pkey PRIMARY KEY (id),
    CONSTRAINT rag_chats_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT rag_chats_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON UPDATE CASCADE ON DELETE CASCADE
);

ALTER TABLE public.rag_chats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow full access to own chats"
ON public.rag_chats
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = now();
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER handle_updated_at
BEFORE UPDATE ON public.rag_chats
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column(); 