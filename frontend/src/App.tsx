import { useState, useRef, useEffect, useCallback } from 'react'
import './App.css'
import { Message } from './components/Message'
import { useMessageFiltering } from './hooks/useMessageFiltering'

interface Message {
  type: 'user' | 'assistant' | 'command' | 'error' | 'result' | 'progress' | 'thinking' | 'final'
  content: string
  timestamp: Date
  sessionId?: string
  isCollapsed?: boolean
}



function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [debugMode, setDebugMode] = useState(false)
  const [sessionId] = useState(() => crypto.randomUUID())
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const copyToClipboard = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      // Show temporary toast or feedback
      const button = document.activeElement as HTMLButtonElement
      const originalText = button.innerText
      button.innerText = '✓ Copied!'
      setTimeout(() => {
        button.innerText = originalText
      }, 1000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [])

  const sendMessage = useCallback(async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input
    setInput('')
    setMessages(prev => [...prev, { 
      type: 'user', 
      content: userMessage,
      timestamp: new Date()
    }])
    setIsLoading(true)

    try {
      const response = await fetch('http://localhost:8003/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: userMessage,
          session_id: sessionId,
          debug_mode: debugMode
        })
      })

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) throw new Error('No reader available')

      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        
        // Keep the last incomplete line in buffer
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === 'done') {
                setIsLoading(false)
                // Clear progress and thinking messages when done
                setMessages(prev => prev.filter(msg => msg.type !== 'progress' && msg.type !== 'thinking'))
              } else if (data.content) {
                setMessages(prev => {
                  // Prevent duplicate messages
                  const lastMsg = prev[prev.length - 1]
                  if (lastMsg?.content === data.content && lastMsg?.type === data.type) {
                    return prev
                  }
                  
                  // In non-debug mode, filter out command and result messages
                  if (!debugMode && (data.type === 'command' || data.type === 'result')) {
                    return prev
                  }
                  
                  // Detect message types based on content patterns
                  let messageType = data.type
                  if (data.type === 'message') {
                    if (data.content.includes('🧠') || data.content.includes('💭') || 
                        data.content.includes('🔍') || data.content.includes('📍') || 
                        data.content.includes('💡') || data.content.includes('🔬')) {
                      messageType = 'thinking'
                    } else if (data.content.includes('📋 **Answer:**')) {
                      messageType = 'final'
                    }
                  }
                  
                  // Replace progress messages with the latest one
                  if (data.type === 'progress') {
                    const filtered = prev.filter(msg => msg.type !== 'progress')
                    return [...filtered, {
                      type: data.type,
                      content: data.content,
                      timestamp: new Date(),
                      sessionId: data.session_id
                    }]
                  }
                  
                  // Replace thinking messages with the latest one
                  if (messageType === 'thinking') {
                    const filtered = prev.filter(msg => msg.type !== 'thinking' && msg.type !== 'progress')
                    return [...filtered, {
                      type: messageType,
                      content: data.content,
                      timestamp: new Date(),
                      sessionId: data.session_id
                    }]
                  }
                  
                  // If final answer arrives, remove thinking messages
                  if (messageType === 'final') {
                    const filtered = prev.filter(msg => msg.type !== 'thinking' && msg.type !== 'progress')
                    return [...filtered, {
                      type: messageType,
                      content: data.content,
                      timestamp: new Date(),
                      sessionId: data.session_id
                    }]
                  }
                  
                  return [...prev, {
                    type: messageType,
                    content: data.content,
                    timestamp: new Date(),
                    sessionId: data.session_id
                  }]
                })
              }
            } catch (e) {
              console.error('Failed to parse SSE:', e)
            }
          }
        }
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date()
      }])
      setIsLoading(false)
    }
  }, [input, sessionId, debugMode])

  const filteredMessages = useMessageFiltering(messages, debugMode)

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto max-w-5xl p-4">
        <header className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800">
            DocBot - Read-only Document Explorer
          </h1>
          <p className="text-gray-600 mt-2">
            Explore your documents safely with bash commands. All write operations are blocked.
          </p>
        </header>
        
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="bg-gradient-to-b from-gray-50 to-white rounded-xl p-6 mb-4 h-[600px] overflow-y-auto shadow-inner">
            {messages.length === 0 && (
              <div className="text-center text-gray-500 mt-20">
                <p className="mb-2">Welcome! Try asking questions like:</p>
                <p className="text-sm italic">"Show me all text files in the document folder"</p>
                <p className="text-sm italic">"Search for TODO comments in the codebase"</p>
                <p className="text-sm italic">"What's the structure of this directory?"</p>
              </div>
            )}
            
            {filteredMessages.map((msg, idx) => (
              <Message
                key={idx}
                type={msg.type}
                content={msg.content}
                timestamp={msg.timestamp}
                sessionId={msg.sessionId}
                debugMode={debugMode}
                onCopyToClipboard={copyToClipboard}
              />
            ))}
            
            {/* Removed processing indicator - using thinking messages instead */}
            
            <div ref={messagesEndRef} />
          </div>

          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Ask about your documents..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg 
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg 
                       hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
            >
              Send
            </button>
          </div>
          
          <div className="mt-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer text-sm">
                  <input
                    type="checkbox"
                    checked={debugMode}
                    onChange={(e) => setDebugMode(e.target.checked)}
                    className="cursor-pointer"
                  />
                  <span className="text-gray-600">Debug mode</span>
                </label>
              </div>
              
              <div className="text-xs text-gray-500">
                Session: {sessionId.slice(0, 8)}...
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App