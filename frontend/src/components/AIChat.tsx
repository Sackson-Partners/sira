import { useState, useRef, useEffect } from 'react'
import { api } from '../services/api'
import { PaperAirplaneIcon, SparklesIcon, XMarkIcon } from '@heroicons/react/24/outline'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface AIChatProps {
  isOpen: boolean
  onClose: () => void
}

export default function AIChat({ isOpen, onClose }: AIChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const history = messages.map(m => ({
        role: m.role,
        content: m.content,
      }))

      const response = await api.post('/api/v1/ai/chat', {
        message: userMessage,
        history,
      })

      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: response.data.response },
      ])
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to get AI response'
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Error: ${errorMsg}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed bottom-4 right-4 w-96 h-[32rem] bg-white rounded-xl shadow-2xl border border-gray-200 flex flex-col z-50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-primary-600 rounded-t-xl">
        <div className="flex items-center gap-2 text-white">
          <SparklesIcon className="h-5 w-5" />
          <span className="font-semibold text-sm">SIRA AI</span>
        </div>
        <button onClick={onClose} className="text-white/80 hover:text-white">
          <XMarkIcon className="h-5 w-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 text-sm mt-8">
            <SparklesIcon className="h-8 w-8 mx-auto mb-2 text-primary-300" />
            <p>Ask me about shipments, vessels, fleet, or market data.</p>
            <p className="mt-1">I can analyze risks and predict ETAs.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-3 py-2 text-sm text-gray-500">
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            placeholder="Ask SIRA AI..."
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="rounded-lg bg-primary-600 p-2 text-white hover:bg-primary-700 disabled:opacity-50"
          >
            <PaperAirplaneIcon className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
