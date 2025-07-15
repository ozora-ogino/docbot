import { memo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styles from './Message.module.css'

interface MessageProps {
  type: 'user' | 'assistant' | 'command' | 'error' | 'result' | 'progress' | 'thinking' | 'final'
  content: string
  timestamp: Date
  sessionId?: string
  debugMode: boolean
  onCopyToClipboard: (text: string) => void
}

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit'
  })
}

const MarkdownComponents = {
  pre: ({ node, children, ...props }: any) => {
    const codeString = String(children).replace(/\n$/, '');
    return (
      <div className="relative group">
        <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto" {...props}>
          {children}
        </pre>
        <button
          onClick={() => props.onCopyToClipboard?.(codeString)}
          className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 
                   transition-opacity bg-gray-700 text-white px-2 py-1 
                   rounded text-xs hover:bg-gray-600"
        >
          Copy
        </button>
      </div>
    );
  },
  code: ({ node, className, children, ...props }: any) => {
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
  h1: ({ node, ...props }: any) => (
    <h1 className="text-2xl font-bold text-gray-800 mt-6 mb-4" {...props} />
  ),
  h2: ({ node, ...props }: any) => (
    <h2 className="text-xl font-bold text-gray-800 mt-5 mb-3" {...props} />
  ),
  h3: ({ node, ...props }: any) => (
    <h3 className="text-lg font-semibold text-gray-800 mt-4 mb-2" {...props} />
  ),
  p: ({ node, ...props }: any) => (
    <p className="text-gray-700 mb-3 leading-relaxed" {...props} />
  ),
  a: ({ node, ...props }: any) => (
    <a className="text-indigo-600 hover:text-indigo-800 underline" target="_blank" rel="noopener noreferrer" {...props} />
  ),
  ul: ({ node, ...props }: any) => (
    <ul className="list-disc list-inside my-3 space-y-1 text-gray-700" {...props} />
  ),
  ol: ({ node, ...props }: any) => (
    <ol className="list-decimal list-inside my-3 space-y-1 text-gray-700" {...props} />
  ),
  li: ({ node, ...props }: any) => (
    <li className="ml-2" {...props} />
  ),
  blockquote: ({ node, ...props }: any) => (
    <blockquote className="border-l-4 border-indigo-400 bg-indigo-50 pl-4 py-2 italic my-3 text-gray-700 rounded-r-lg" {...props} />
  ),
  table: ({ node, ...props }: any) => (
    <div className="overflow-x-auto my-4">
      <table className="min-w-full border-collapse border border-gray-300" {...props} />
    </div>
  ),
  thead: ({ node, ...props }: any) => (
    <thead className="bg-gray-100" {...props} />
  ),
  th: ({ node, ...props }: any) => (
    <th className="border border-gray-300 px-4 py-2 text-left font-semibold text-gray-800" {...props} />
  ),
  td: ({ node, ...props }: any) => (
    <td className="border border-gray-300 px-4 py-2 text-gray-700" {...props} />
  ),
  hr: ({ node, ...props }: any) => (
    <hr className="my-4 border-gray-300" {...props} />
  ),
  strong: ({ node, ...props }: any) => (
    <strong className="font-bold text-gray-900" style={{ fontWeight: 700 }} {...props} />
  ),
  em: ({ node, ...props }: any) => (
    <em className="italic" {...props} />
  ),
}

export const Message = memo(function Message({ type, content, timestamp, debugMode, onCopyToClipboard }: MessageProps) {
  // Skip command and result messages in non-debug mode
  if (!debugMode && (type === 'command' || type === 'result')) {
    return null
  }

  const messageTypeLabel = type === 'user' ? 'You' : 
    type === 'command' ? 'Command' :
    type === 'result' ? 'Output' :
    type === 'error' ? 'Error' :
    type === 'thinking' ? 'Assistant' :
    type === 'final' ? 'Assistant' : 'Assistant'

  const messageClassName = `relative group rounded-xl px-5 py-4 transition-all duration-300 ${
    type === 'user' ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg' :
    type === 'command' ? 'bg-gray-900 text-emerald-400 font-mono text-sm border border-gray-700' :
    type === 'result' ? 'bg-gray-50 font-mono text-sm whitespace-pre-wrap border border-gray-200' :
    type === 'error' ? 'bg-red-50 text-red-800 border border-red-200' :
    type === 'progress' ? 'bg-amber-50 text-amber-800 italic border border-amber-200' :
    type === 'thinking' ? styles.thinkingMessage :
    type === 'final' ? styles.finalAnswer :
    styles.assistantMessage
  }`

  const proseClassName = type === 'final' 
    ? 'prose max-w-none prose-lg prose-headings:text-gray-900 prose-p:text-gray-800 prose-a:text-blue-700 prose-strong:text-gray-900 prose-strong:font-bold prose-code:text-pink-700 prose-pre:bg-gray-900 prose-pre:text-gray-100'
    : type === 'thinking' 
      ? 'prose max-w-none prose-sm prose-headings:text-gray-600 prose-p:text-gray-600 prose-a:text-gray-600 prose-strong:text-gray-700 italic'
      : 'prose max-w-none prose-sm prose-headings:text-gray-700 prose-p:text-gray-600 prose-a:text-blue-600 prose-strong:text-gray-800 prose-code:text-pink-600 prose-pre:bg-gray-800 prose-pre:text-gray-100'

  return (
    <div className={`mb-4 ${type === 'user' ? 'text-right' : 'text-left'} animate-fadeIn`}>
      <div className={`inline-block max-w-[85%] ${type === 'user' ? 'ml-auto' : ''}`}>
        {type !== 'progress' && (
          <div className="text-xs text-gray-500 mb-1 flex items-center gap-2">
            {type === 'thinking' && (
              <div className={styles.thinkingIndicator}>
                <div className={styles.thinkingDot}></div>
                <div className={styles.thinkingDot}></div>
                <div className={styles.thinkingDot}></div>
              </div>
            )}
            {type === 'final' && (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-indigo-700 bg-indigo-100 px-2 py-1 rounded-full">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Final Answer
              </span>
            )}
            <span>
              {messageTypeLabel} • {formatTime(timestamp)}
            </span>
          </div>
        )}
        
        <div className={messageClassName}>
          {type === 'progress' ? (
            <>
              <svg className="animate-spin h-4 w-4 mr-2 inline" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              <span className="text-sm">{content}</span>
            </>
          ) : (type === 'assistant' || type === 'thinking' || type === 'final') ? (
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              className={proseClassName}
              components={{
                ...MarkdownComponents,
                pre: (props: any) => MarkdownComponents.pre({ ...props, onCopyToClipboard })
              }}
            >
              {content}
            </ReactMarkdown>
          ) : (
            <span className={type === 'user' ? 'text-sm' : ''}>{content}</span>
          )}
          
          {(type === 'command' || type === 'result') && (
            <button
              onClick={() => onCopyToClipboard(content)}
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
  )
})