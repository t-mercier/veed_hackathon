import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) {
      return new Response(JSON.stringify({ error: 'No authorization header' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      })
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_ANON_KEY')!,
      { global: { headers: { Authorization: authHeader } } }
    )

    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      })
    }

    const { topic, mode, avatar, voice, robotic, avatar_image_url, mood, level, github_url } = await req.json()

    if (!topic || !mode) {
      return new Response(JSON.stringify({ error: 'Topic and mode are required' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      })
    }

    const { data: request, error: insertError } = await supabase
      .from('video_requests')
      .insert({
        user_id: user.id,
        topic,
        mode,
        avatar: avatar || null,
        mood: mood || 'friendly',
        level: level || 'beginner',
        github_url: github_url || null,
        status: 'pending',
      })
      .select('id')
      .single()

    if (insertError) {
      console.error('Insert error:', insertError)
      return new Response(JSON.stringify({ error: 'Failed to create request', details: insertError.message }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      })
    }

    // Fire-and-forget to Python backend
    // Map fields to match backend's GenerateRequest schema
    const backendUrl = Deno.env.get('BACKEND_URL')
    if (backendUrl) {
      const isRepo = mode === 'repo' || (github_url && github_url.startsWith('https://github.com/'))
      fetch(`${backendUrl}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request_id: request.id,
          prompt: isRepo ? (github_url || topic) : topic,
          url: github_url || null,
          mode: 'concept',   // backend routes based on prompt content, not mode
          mood: mood || 'friendly',
          level: level || 'beginner',
          avatar: avatar || null,
          voice: voice || null,
          robotic: robotic || false,
          avatar_image_url: avatar_image_url || null,
        }),
      }).catch(err => console.error('Failed to call backend:', err))
    } else {
      console.error('BACKEND_URL not set — cannot forward request to Python backend')
    }

    return new Response(JSON.stringify({ request_id: request.id }), {
      status: 200,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })

  } catch (err) {
    console.error('Edge function error:', err)
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })
  }
})
