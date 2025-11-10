'use client'

export function Footer() {
  return (
    <footer className="bg-slate-800 border-t border-slate-700 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid md:grid-cols-3 gap-8">
          {/* About */}
          <div>
            <h3 className="text-white font-semibold mb-3">SmartPlex</h3>
            <p className="text-slate-400 text-sm">
              The autonomous, AI-powered Plex ecosystem that intelligently manages your media library.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-white font-semibold mb-3">Quick Links</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="/dashboard" className="text-slate-400 hover:text-white transition-colors">
                  Dashboard
                </a>
              </li>
              <li>
                <a href="https://github.com/rbradshaw9/smartplex" target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-white transition-colors">
                  GitHub
                </a>
              </li>
              <li>
                <a href="https://www.plex.tv" target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-white transition-colors">
                  Plex.tv
                </a>
              </li>
            </ul>
          </div>

          {/* Integrations */}
          <div>
            <h3 className="text-white font-semibold mb-3">Integrations</h3>
            <ul className="space-y-2 text-sm text-slate-400">
              <li>🎬 Plex Media Server</li>
              <li>📊 Tautulli</li>
              <li>📺 Sonarr</li>
              <li>🎥 Radarr</li>
              <li>🎭 Overseerr</li>
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-700 text-center text-slate-400 text-sm">
          <p>
            © {new Date().getFullYear()} SmartPlex. Powered by AI and built for media enthusiasts.
          </p>
        </div>
      </div>
    </footer>
  )
}
