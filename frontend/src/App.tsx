import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './App.css'

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

  const copyToClipboard = async (text: string) => {
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
  }

  const sendMessage = async () => {
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
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    })
  }

  return (
    <>
      <style>{`
        .assistant-message {
          background: linear-gradient(135deg, #ffffff 0%, #f8fafc 50%, #ffffff 100%);
          border: 1px solid #e5e7eb;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
          position: relative;
        }
        
        .assistant-message::after {
          content: '';
          position: absolute;
          left: 0;
          top: 0;
          bottom: 0;
          width: 3px;
          background: linear-gradient(180deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
          border-radius: 12px 0 0 12px;
          opacity: 0.8;
        }
        
        .thinking-message {
          background: linear-gradient(135deg, #fafafa 0%, #f3f4f6 100%);
          border: 1px solid #e5e7eb;
          position: relative;
          overflow: hidden;
        }
        
        .thinking-message::before {
          content: '';
          position: absolute;
          top: -2px;
          left: -2px;
          right: -2px;
          bottom: -2px;
          background: linear-gradient(60deg, #8b5cf6, #3b82f6, #8b5cf6);
          background-size: 300% 300%;
          animation: gradient 3s ease infinite;
          border-radius: inherit;
          opacity: 0.3;
          z-index: -1;
        }
        
        @keyframes gradient {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        
        .thinking-indicator {
          display: flex;
          gap: 4px;
          align-items: center;
        }
        
        .thinking-dot {
          width: 6px;
          height: 6px;
          background: #8b5cf6;
          border-radius: 50%;
          animation: thinking 1.4s ease-in-out infinite;
        }
        
        .thinking-dot:nth-child(1) { animation-delay: -0.32s; }
        .thinking-dot:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes thinking {
          0%, 80%, 100% {
            transform: scale(0.8);
            opacity: 0.5;
          }
          40% {
            transform: scale(1);
            opacity: 1;
          }
        }
        
        .final-answer {
          background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%);
          border: 2px solid #10b981;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
          position: relative;
        }
        
        .final-answer::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 3px;
          background: linear-gradient(90deg, #10b981, #3b82f6);
          border-radius: 2px 2px 0 0;
        }
      `}</style>
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
            
            {messages.map((msg, idx) => (
              <div key={idx} className={`mb-3 ${
                msg.type === 'user' ? 'text-right' : 'text-left'
              }`}>
                <div className={`inline-block max-w-[80%] ${
                  msg.type === 'user' ? 'ml-auto' : ''
                }`}>
                  {msg.type !== 'progress' && (
                    <div className="text-xs text-gray-500 mb-1 flex items-center gap-2">
                      {msg.type === 'thinking' && (
                        <div className="thinking-indicator">
                          <div className="thinking-dot"></div>
                          <div className="thinking-dot"></div>
                          <div className="thinking-dot"></div>
                        </div>
                      )}
                      {msg.type === 'final' && (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          Answer
                        </span>
                      )}
                      <span>
                        {msg.type === 'user' ? 'You' : 
                         msg.type === 'command' ? 'Command' :
                         msg.type === 'result' ? 'Output' :
                         msg.type === 'error' ? 'Error' :
                         msg.type === 'thinking' ? 'Assistant' :
                         msg.type === 'final' ? 'Assistant' : 'Assistant'
                        } • {formatTime(msg.timestamp)}
                      </span>
                    </div>
                  )}
                  
                  <div className={`relative group rounded-xl px-5 py-4 transition-all duration-300 ${
                    msg.type === 'user' ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg' :
                    msg.type === 'command' ? 'bg-gray-800 text-green-400 font-mono text-sm' :
                    msg.type === 'result' ? 'bg-gray-100 font-mono text-sm whitespace-pre-wrap' :
                    msg.type === 'error' ? 'bg-red-50 text-red-800 border border-red-200' :
                    msg.type === 'progress' ? 'bg-yellow-50 text-yellow-800 italic' :
                    msg.type === 'thinking' ? 'thinking-message' :
                    msg.type === 'final' ? 'final-answer' :
                    'bg-white border border-gray-200'
                  }`}>
                    {msg.type === 'progress' ? (
                      <>
                        <svg className="animate-spin h-4 w-4 mr-2 inline" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                        </svg>
                        <span className="text-sm">{msg.content}</span>
                      </>
                    ) : (msg.type === 'assistant' || msg.type === 'thinking' || msg.type === 'final') ? (
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        className={`prose max-w-none ${
                          msg.type === 'final' 
                            ? 'prose-lg prose-headings:text-gray-900 prose-p:text-gray-800 prose-a:text-blue-700 prose-strong:text-gray-900 prose-strong:font-bold prose-code:text-pink-700 prose-pre:bg-gray-900 prose-pre:text-gray-100'
                            : msg.type === 'thinking' 
                              ? 'prose-sm prose-headings:text-gray-600 prose-p:text-gray-600 prose-a:text-gray-600 prose-strong:text-gray-700 italic'
                              : 'prose-sm prose-headings:text-gray-700 prose-p:text-gray-600 prose-a:text-blue-600 prose-strong:text-gray-800 prose-code:text-pink-600 prose-pre:bg-gray-800 prose-pre:text-gray-100'
                        }`}
                        components={{
                          pre: ({ node, children, ...props }) => {
                            const codeString = String(children).replace(/\n$/, '');
                            return (
                              <div className="relative group">
                                <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto" {...props}>
                                  {children}
                                </pre>
                                <button
                                  onClick={() => copyToClipboard(codeString)}
                                  className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 
                                           transition-opacity bg-gray-700 text-white px-2 py-1 
                                           rounded text-xs hover:bg-gray-600"
                                >
                                  Copy
                                </button>
                              </div>
                            );
                          },
                          code: ({ node, className, children, ...props }) => {
                            const match = /language-(\w+)/.exec(className || '')
                            const isInline = !match
                            return isInline ? (
                              <code className="bg-gray-100 text-pink-600 rounded px-1 py-0.5 text-sm font-mono" {...props}>
                                {children}
                              </code>
                            ) : (
                              <code className="block text-sm font-mono" {...props}>
                                {children}
                              </code>
                            )
                          },
                          h1: ({ node, ...props }) => (
                            <h1 className="text-2xl font-bold text-gray-800 mt-6 mb-4" {...props} />
                          ),
                          h2: ({ node, ...props }) => (
                            <h2 className="text-xl font-bold text-gray-800 mt-5 mb-3" {...props} />
                          ),
                          h3: ({ node, ...props }) => (
                            <h3 className="text-lg font-semibold text-gray-800 mt-4 mb-2" {...props} />
                          ),
                          p: ({ node, ...props }) => (
                            <p className="text-gray-700 mb-3 leading-relaxed" {...props} />
                          ),
                          a: ({ node, ...props }) => (
                            <a className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer" {...props} />
                          ),
                          ul: ({ node, ...props }) => (
                            <ul className="list-disc list-inside my-3 space-y-1 text-gray-700" {...props} />
                          ),
                          ol: ({ node, ...props }) => (
                            <ol className="list-decimal list-inside my-3 space-y-1 text-gray-700" {...props} />
                          ),
                          li: ({ node, ...props }) => (
                            <li className="ml-2" {...props} />
                          ),
                          blockquote: ({ node, ...props }) => (
                            <blockquote className="border-l-4 border-blue-400 bg-blue-50 pl-4 py-2 italic my-3 text-gray-700" {...props} />
                          ),
                          table: ({ node, ...props }) => (
                            <div className="overflow-x-auto my-4">
                              <table className="min-w-full border-collapse border border-gray-300" {...props} />
                            </div>
                          ),
                          thead: ({ node, ...props }) => (
                            <thead className="bg-gray-100" {...props} />
                          ),
                          th: ({ node, ...props }) => (
                            <th className="border border-gray-300 px-4 py-2 text-left font-semibold text-gray-800" {...props} />
                          ),
                          td: ({ node, ...props }) => (
                            <td className="border border-gray-300 px-4 py-2 text-gray-700" {...props} />
                          ),
                          hr: ({ node, ...props }) => (
                            <hr className="my-4 border-gray-300" {...props} />
                          ),
                          strong: ({ node, ...props }) => (
                            <strong className="font-bold text-gray-900" style={{ fontWeight: 700 }} {...props} />
                          ),
                          em: ({ node, ...props }) => (
                            <em className="italic" {...props} />
                          ),
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    ) : (
                      <span className={msg.type === 'user' ? 'text-sm' : ''}>{msg.content}</span>
                    )}
                    
                    {(msg.type === 'command' || msg.type === 'result') && (
                      <button
                        onClick={() => copyToClipboard(msg.content)}
                        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 
                                 transition-opacity bg-gray-700 text-white px-2 py-1 
                                 rounded text-xs hover:bg-gray-600"
                      >
                        Copy
                      </button>
                    )}
                  </div>
                </div>
              </div>
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
    </>
  )
}

export default App