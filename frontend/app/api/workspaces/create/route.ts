import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const {
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
    } = body

    console.log('Creating workspace for user:', user_id)

    const { data, error } = await supabase
      .from('workspaces')
      .insert({
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
      })
      .select()
      .single()

    if (error) {
      console.error('Error creating workspace:', error)
      return NextResponse.json({ error: error.message }, { status: 500 })
    }

    console.log('Workspace created successfully:', data)
    return NextResponse.json(data)

  } catch (error) {
    console.error('API error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
} 