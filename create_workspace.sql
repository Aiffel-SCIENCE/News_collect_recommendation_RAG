-- 워크스페이스 테이블이 없다면 생성
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ,
    sharing TEXT NOT NULL DEFAULT 'private',
    default_context_length INTEGER NOT NULL,
    default_model TEXT NOT NULL CHECK (char_length(default_model) <= 1000),
    default_prompt TEXT NOT NULL CHECK (char_length(default_prompt) <= 100000),
    default_temperature REAL NOT NULL,
    description TEXT NOT NULL CHECK (char_length(description) <= 500),
    embeddings_provider TEXT NOT NULL CHECK (char_length(embeddings_provider) <= 1000),
    include_profile_context BOOLEAN NOT NULL,
    include_workspace_instructions BOOLEAN NOT NULL,
    instructions TEXT NOT NULL CHECK (char_length(instructions) <= 1500),
    is_home BOOLEAN NOT NULL DEFAULT FALSE,
    name TEXT NOT NULL CHECK (char_length(name) <= 100)
);

-- 기본 워크스페이스 생성 (모든 사용자용)
INSERT INTO workspaces (
    user_id, 
    name, 
    description, 
    default_context_length, 
    default_model, 
    default_prompt, 
    default_temperature, 
    include_profile_context, 
    include_workspace_instructions, 
    instructions, 
    is_home, 
    sharing, 
    embeddings_provider
) VALUES 
(
    '00000000-0000-0000-0000-000000000000', -- 시스템 사용자 ID
    '기본 워크스페이스', 
    '모든 사용자를 위한 기본 워크스페이스입니다.', 
    4000, 
    'gpt-4.1-nano', 
    '당신은 도움이 되는 AI 어시스턴트입니다.', 
    0.5, 
    true, 
    true, 
    '이 워크스페이스는 기본 설정으로 구성되어 있습니다.', 
    true, 
    'public', 
    'openai'
) ON CONFLICT DO NOTHING;

-- RLS 정책 설정
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

-- 모든 사용자가 기본 워크스페이스에 접근할 수 있도록 정책 설정
CREATE POLICY "Allow access to default workspace"
    ON workspaces
    FOR ALL
    USING (sharing = 'public' OR user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_workspaces_user_id ON workspaces (user_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_sharing ON workspaces (sharing); 