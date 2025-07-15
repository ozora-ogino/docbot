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
  const [isComposing, setIsComposing] = useState(false)
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
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="container mx-auto max-w-6xl p-4">
        <header className="mb-8 text-center">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
              <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
              DocAgent
            </h1>
          </div>
          <p className="text-gray-600 text-lg max-w-2xl mx-auto">
            Your AI-powered assistant for intelligent document exploration
          </p>
          <div className="mt-3 flex items-center justify-center gap-2 text-sm text-gray-500">
            <span className="inline-flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              Safe mode enabled
            </span>
            <span className="text-gray-400">•</span>
            <span>All write operations blocked</span>
          </div>
        </header>
        
        <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100">
          <div className="bg-gradient-to-b from-gray-50 to-white rounded-xl p-6 mb-4 h-[calc(100vh-320px)] min-h-[400px] overflow-y-auto shadow-inner">
            {messages.length === 0 && (
              <div className="text-center mt-20">
                <div className="mb-8">
                  <div className="w-20 h-20 bg-gradient-to-br from-indigo-100 to-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-10 h-10 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                  </div>
                  <h2 className="text-xl font-semibold text-gray-800 mb-2">Ready to explore your documents</h2>
                  <p className="text-gray-600 mb-6">Ask me anything about your files and folders</p>
                </div>
                <div className="space-y-3 max-w-lg mx-auto">
                  <button
                    onClick={() => setInput('Show me all text files in the document folder')}
                    className="w-full text-left px-4 py-3 bg-gray-50 hover:bg-indigo-50 rounded-lg transition-colors group">
                    <span className="text-gray-700 group-hover:text-indigo-700">📁 "Show me all text files in the document folder"</span>
                  </button>
                  <button
                    onClick={() => setInput('Search for TODO comments in the codebase')}
                    className="w-full text-left px-4 py-3 bg-gray-50 hover:bg-indigo-50 rounded-lg transition-colors group">
                    <span className="text-gray-700 group-hover:text-indigo-700">🔍 "Search for TODO comments in the codebase"</span>
                  </button>
                  <button
                    onClick={() => setInput("What's the structure of this directory?")}
                    className="w-full text-left px-4 py-3 bg-gray-50 hover:bg-indigo-50 rounded-lg transition-colors group">
                    <span className="text-gray-700 group-hover:text-indigo-700">🗂️ "What's the structure of this directory?"</span>
                  </button>
                </div>
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
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !isComposing && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage()
                }
              }}
              onCompositionStart={() => setIsComposing(true)}
              onCompositionEnd={() => setIsComposing(false)}
              placeholder="Ask me anything about your documents..."
              className="flex-1 px-4 py-3 border border-gray-200 rounded-xl 
                       focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                       transition-all duration-200 text-gray-700"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl 
                       hover:from-indigo-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-200 shadow-md hover:shadow-lg transform hover:-translate-y-0.5
                       font-medium"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                  </svg>
                  Processing...
                </>
              ) : (
                'Send'
              )}
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