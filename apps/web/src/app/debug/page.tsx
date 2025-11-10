'use client'

export default function DebugPage() {
  const envVars = {
    'NEXT_PUBLIC_API_URL': process.env.NEXT_PUBLIC_API_URL,
    'NEXT_PUBLIC_SUPABASE_URL': process.env.NEXT_PUBLIC_SUPABASE_URL,
    'NEXT_PUBLIC_SUPABASE_ANON_KEY': process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? '***SET***' : 'NOT SET',
    'NEXT_PUBLIC_PLEX_CLIENT_ID': process.env.NEXT_PUBLIC_PLEX_CLIENT_ID,
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Environment Debug</h1>
        
        <div className="bg-slate-800 rounded-lg p-6 space-y-4">
          <h2 className="text-xl font-semibold mb-4">Environment Variables</h2>
          
          {Object.entries(envVars).map(([key, value]) => (
            <div key={key} className="flex items-center gap-4 p-3 bg-slate-700 rounded">
              <span className="font-mono text-sm text-blue-400 flex-shrink-0 w-64">{key}</span>
              <span className={`font-mono text-sm ${value ? 'text-green-400' : 'text-red-400'}`}>
                {value || '❌ NOT SET'}
              </span>
            </div>
          ))}
        </div>

        <div className="mt-8 bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-6">
          <h3 className="text-yellow-400 font-semibold mb-3">⚠️ Important</h3>
          <p className="text-slate-300 mb-2">
            If any environment variables show as "NOT SET", you need to configure them in Vercel:
          </p>
          <ol className="list-decimal list-inside space-y-2 text-slate-300 ml-4">
            <li>Go to Vercel Dashboard → Your Project → Settings → Environment Variables</li>
            <li>Add each missing variable</li>
            <li>Redeploy from the Deployments tab</li>
          </ol>
        </div>

        <div className="mt-8 bg-slate-800 rounded-lg p-6">
          <h3 className="font-semibold mb-3">Expected Values</h3>
          <div className="space-y-2 text-sm font-mono text-slate-400">
            <div>NEXT_PUBLIC_API_URL = https://smartplexapi-production.up.railway.app</div>
            <div>NEXT_PUBLIC_SUPABASE_URL = https://lecunkywsfuqumqzddol.supabase.co</div>
            <div>NEXT_PUBLIC_SUPABASE_ANON_KEY = (your Supabase anon key)</div>
            <div>NEXT_PUBLIC_PLEX_CLIENT_ID = smartplex-web-client</div>
          </div>
        </div>
      </div>
    </div>
  )
}
