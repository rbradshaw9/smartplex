interface RecommendationsProps {
  recommendations: Array<{
    title: string
    reason: string
  }>
}

export function Recommendations({ recommendations }: RecommendationsProps) {
  return (
    <div className="bg-slate-800 rounded-lg p-6">
      <h2 className="text-2xl font-semibold text-white mb-6">AI Recommendations</h2>
      
      <div className="space-y-4">
        {recommendations.map((item, index) => (
          <div key={index} className="bg-slate-700 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-white font-medium">{item.title}</h3>
                <p className="text-slate-400 text-sm mt-1">{item.reason}</p>
              </div>
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm transition-colors">
                Request
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 bg-blue-600/10 border border-blue-600/20 rounded-lg">
        <div className="flex items-center space-x-2">
          <span className="text-blue-400 text-lg">🤖</span>
          <span className="text-blue-300 text-sm font-medium">
            AI Tip: These recommendations are based on your viewing history and trending content.
          </span>
        </div>
      </div>
    </div>
  )
}