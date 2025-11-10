'use client'

import { useState } from 'react'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Hello! I\'m your SmartPlex AI assistant. I can help you discover new content, analyze your viewing habits, or answer questions about your media library. What would you like to know?',
      timestamp: new Date(),
    },
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      console.log('💬 Starting chat request...')
      // Get auth token from Supabase
      const { createClientComponentClient } = await import('@supabase/auth-helpers-nextjs')
      const supabase = createClientComponentClient()
      const { data: { session } } = await supabase.auth.getSession()

      if (!session) {
        throw new Error('Not authenticated')
      }

      console.log('Session valid, calling AI chat API...')
      const apiUrl = `${process.env.NEXT_PUBLIC_API_URL}/ai/chat`
      console.log('API URL:', apiUrl)

      // Call the real AI chat API
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          message: inputMessage,
          chat_history: messages.map(m => ({
            role: m.role,
            content: m.content,
          })),
        }),
      })

      console.log('Chat response status:', response.status)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('Chat error response:', errorText)
        throw new Error(`API error: ${response.status}`)
      }

      const data = await response.json()
      console.log('✅ Chat response data:', data)
      
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.response || 'I apologize, but I couldn\'t generate a response.',
        timestamp: new Date(),
      }
      
      console.log('💬 Adding assistant message to state:', assistantMessage)
      setMessages(prev => {
        const updated = [...prev, assistantMessage]
        console.log('💬 Updated messages:', updated.length, 'total')
        return updated
      })
    } catch (error) {
      console.error('❌ Chat error:', error)
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error connecting to the AI service. Please try again later.',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="bg-slate-800 rounded-lg p-6 h-96 flex flex-col">
      <h2 className="text-xl font-semibold text-white mb-4">AI Chat Assistant</h2>
      
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.map((message, index) => (
          <div key={index} className={`${message.role === 'user' ? 'text-right' : 'text-left'}`}>
            <div className={`inline-block p-3 rounded-lg max-w-xs ${
              message.role === 'user' 
                ? 'bg-blue-600 text-white' 
                : 'bg-slate-700 text-slate-200'
            }`}>
              <p className="text-sm">{message.content}</p>
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {message.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="text-left">
            <div className="inline-block p-3 rounded-lg bg-slate-700 text-slate-200">
              <div className="flex items-center space-x-3">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-sm text-slate-400">AI is thinking...</span>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Input */}
      <div className="flex space-x-2">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="Ask me anything about your library..."
          className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
          disabled={isLoading}
        />
        <button
          onClick={handleSendMessage}
          disabled={isLoading || !inputMessage.trim()}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  )
}