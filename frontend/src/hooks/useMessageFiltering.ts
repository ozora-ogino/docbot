import { useMemo } from 'react'

interface Message {
  type: 'user' | 'assistant' | 'command' | 'error' | 'result' | 'progress' | 'thinking' | 'final'
  content: string
  timestamp: Date
  sessionId?: string
}

export function useMessageFiltering(messages: Message[], debugMode: boolean) {
  return useMemo(() => {
    if (debugMode) return messages
    
    return messages.filter(msg => 
      msg.type !== 'command' && msg.type !== 'result'
    )
  }, [messages, debugMode])
}