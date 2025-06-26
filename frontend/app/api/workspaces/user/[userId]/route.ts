import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function GET(
  request: NextRequest,
  { params }: { params: { userId: string } }
) {
  try {
    const { userId } = params

    console.log('Fetching workspaces for user:', userId)

    const { data, error } = await supabase
      .from('workspaces')
      .select('*')
      .eq('user_id', userId)

    if (error) {
      console.error('Error fetching workspaces:', error)
      return NextResponse.json({ error: error.message }, { status: 500 })
    }

    console.log('Found workspaces:', data)
    return NextResponse.json(data)

  } catch (error) {
    console.error('API error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
} 