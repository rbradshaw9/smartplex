interface WatchStatsProps {
  stats: {
    totalWatched: number
    hoursWatched: number
    favoriteGenre: string
    recentlyWatched: Array<{
      title: string
      type: string
      watchedAt: string
    }>
  }
}

export function WatchStats({ stats }: WatchStatsProps) {
  return (
    <div className="bg-slate-800 rounded-lg p-6">
      <h2 className="text-2xl font-semibold text-white mb-6">Your Watch Stats</h2>
      
      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="text-center">
          <div className="text-3xl font-bold text-blue-400">{stats.totalWatched}</div>
          <div className="text-slate-400 text-sm">Total Watched</div>
        </div>
        <div className="text-center">
          <div className="text-3xl font-bold text-green-400">{stats.hoursWatched}h</div>
          <div className="text-slate-400 text-sm">Hours Watched</div>
        </div>
        <div className="text-center">
          <div className="text-3xl font-bold text-purple-400">{stats.favoriteGenre}</div>
          <div className="text-slate-400 text-sm">Favorite Genre</div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-white mb-4">Recently Watched</h3>
        <div className="space-y-3">
          {stats.recentlyWatched.map((item, index) => (
            <div key={index} className="flex items-center justify-between bg-slate-700 rounded-lg p-4">
              <div>
                <div className="text-white font-medium">{item.title}</div>
                <div className="text-slate-400 text-sm capitalize">{item.type}</div>
              </div>
              <div className="text-slate-400 text-sm">
                {new Date(item.watchedAt).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}