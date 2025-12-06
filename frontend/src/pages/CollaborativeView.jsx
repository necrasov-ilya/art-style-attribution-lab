import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { 
  Send, LogOut, Loader2, AlertCircle, Clock, Users, 
  Palette, Sparkles, MessageCircle, X, User, Brain
} from 'lucide-react'
import { collaborativeAPI } from '../api'

// Clean think tags from response
const cleanThinkTags = (text) => {
  if (!text) return ''
  // Remove <think>...</think> blocks
  let cleaned = text.replace(/<think[^>]*>[\s\S]*?<\/think>/gi, '')
  // Remove unclosed <think> tags (streaming)
  cleaned = cleaned.replace(/<think[^>]*>[\s\S]*$/gi, '')
  // Clean up extra newlines
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n')
  return cleaned.trim()
}

// Check if text contains think tags (for "thinking" indicator)
const hasThinkTags = (text) => {
  if (!text) return false
  return /<think[^>]*>/i.test(text) && !/<\/think>/i.test(text)
}

// Generate or retrieve viewer ID
const getViewerId = () => {
  let viewerId = sessionStorage.getItem('collab_viewer_id')
  if (!viewerId) {
    viewerId = 'viewer_' + Math.random().toString(36).substr(2, 9)
    sessionStorage.setItem('collab_viewer_id', viewerId)
  }
  return viewerId
}

function CollaborativeView() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  
  // Session state
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [remainingTime, setRemainingTime] = useState(0)
  const [activeViewers, setActiveViewers] = useState(0)
  const [sessionClosed, setSessionClosed] = useState(false)
  
  // Chat state - dialog format
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([]) // [{role: 'user'|'assistant', content: string}]
  const [currentStreamContent, setCurrentStreamContent] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [questionError, setQuestionError] = useState('')
  
  const viewerId = useRef(getViewerId())
  const heartbeatInterval = useRef(null)
  const abortController = useRef(null)
  const messagesEndRef = useRef(null)
  
  // Load session data
  useEffect(() => {
    const loadSession = async () => {
      try {
        setLoading(true)
        const response = await collaborativeAPI.getSession(sessionId)
        setSession(response.data)
        setRemainingTime(response.data.remaining_seconds)
        setError(null)
      } catch (err) {
        console.error('Failed to load session:', err)
        if (err.response?.status === 404) {
          setError('Сессия не найдена или истекла')
        } else {
          setError('Ошибка загрузки сессии')
        }
      } finally {
        setLoading(false)
      }
    }
    
    loadSession()
  }, [sessionId])
  
  // Heartbeat for presence tracking
  useEffect(() => {
    if (!session || !session.is_active) return
    
    const sendHeartbeat = async () => {
      try {
        const response = await collaborativeAPI.heartbeat(sessionId, viewerId.current)
        setActiveViewers(response.data.active_viewers)
        setRemainingTime(response.data.remaining_seconds)
        
        // Update has_deep_analysis dynamically from heartbeat
        if (response.data.has_deep_analysis !== undefined) {
          setSession(prev => prev ? { ...prev, has_deep_analysis: response.data.has_deep_analysis } : prev)
        }
        
        // Check if session expired
        if (response.data.remaining_seconds <= 0) {
          setSessionClosed(true)
        }
      } catch (err) {
        console.error('Heartbeat failed:', err)
        // Check if session was closed by owner (404 or session inactive)
        if (err.response?.status === 404 || err.response?.data?.detail?.includes('не активна')) {
          setSessionClosed(true)
        }
      }
    }
    
    // Send initial heartbeat
    sendHeartbeat()
    
    // Set up interval (every 30 seconds)
    heartbeatInterval.current = setInterval(sendHeartbeat, 30000)
    
    return () => {
      if (heartbeatInterval.current) {
        clearInterval(heartbeatInterval.current)
      }
    }
  }, [session, sessionId])
  
  // Timer countdown
  useEffect(() => {
    if (remainingTime <= 0) return
    
    const timer = setInterval(() => {
      setRemainingTime(prev => Math.max(0, prev - 1))
    }, 1000)
    
    return () => clearInterval(timer)
  }, [remainingTime])
  
  // Format time as MM:SS
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  
  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }
  
  useEffect(() => {
    scrollToBottom()
  }, [messages, currentStreamContent])
  
  // Handle question submission with streaming
  const handleAskQuestion = useCallback(async () => {
    if (!question.trim() || isStreaming) return
    
    const userQuestion = question.trim()
    setQuestion('')
    setIsStreaming(true)
    setCurrentStreamContent('')
    setQuestionError('')
    
    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: userQuestion }])
    
    // Cancel any previous request
    if (abortController.current) {
      abortController.current.abort()
    }
    abortController.current = new AbortController()
    
    let fullResponse = ''
    
    try {
      // Use fetch for SSE streaming
      const response = await fetch(
        `/api/collaborative/${sessionId}/ask/stream`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ question: userQuestion }),
          signal: abortController.current.signal
        }
      )
      
      if (!response.ok) {
        throw new Error('Ошибка запроса')
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        
        // Parse SSE events - don't split on double newlines, process line by line
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            // Don't trim! Preserve spaces
            const data = line.slice(6)
            if (data === '[DONE]') {
              break
            } else if (data.startsWith('[ERROR]')) {
              setQuestionError(data.slice(8))
              break
            } else {
              fullResponse += data
              setCurrentStreamContent(fullResponse)
            }
          }
        }
      }
      
      // Add completed assistant message to chat
      if (fullResponse) {
        setMessages(prev => [...prev, { role: 'assistant', content: fullResponse }])
      }
      setCurrentStreamContent('')
      
    } catch (err) {
      if (err.name === 'AbortError') {
        // Request was cancelled
        return
      }
      console.error('Question failed:', err)
      setQuestionError('Ошибка при получении ответа. Попробуйте ещё раз.')
      // Remove the user message if there was an error
      setMessages(prev => prev.slice(0, -1))
    } finally {
      setIsStreaming(false)
    }
  }, [question, sessionId, isStreaming])
  
  // Handle exit
  const handleExit = () => {
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current)
    }
    navigate('/login')
  }
  
  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-[#141413] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-emerald-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Загрузка сессии...</p>
        </div>
      </div>
    )
  }
  
  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-[#141413] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-charcoal-900 border border-red-500/30 rounded-2xl p-8 text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-serif text-white mb-2">Сессия недоступна</h2>
          <p className="text-gray-400 mb-6">{error}</p>
          <button
            onClick={handleExit}
            className="px-6 py-3 bg-white text-black font-medium rounded-lg hover:bg-gray-200 transition-colors"
          >
            Перейти ко входу
          </button>
        </div>
      </div>
    )
  }
  
  // Session expired
  if (remainingTime <= 0 && session) {
    return (
      <div className="min-h-screen bg-[#141413] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-charcoal-900 border border-amber-500/30 rounded-2xl p-8 text-center">
          <Clock className="w-16 h-16 text-amber-500 mx-auto mb-4" />
          <h2 className="text-2xl font-serif text-white mb-2">Время истекло</h2>
          <p className="text-gray-400 mb-6">Сессия совместного анализа завершена.</p>
          <button
            onClick={handleExit}
            className="px-6 py-3 bg-white text-black font-medium rounded-lg hover:bg-gray-200 transition-colors"
          >
            Перейти ко входу
          </button>
        </div>
      </div>
    )
  }
  
  // Session closed by owner
  if (sessionClosed) {
    return (
      <div className="min-h-screen bg-[#141413] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-charcoal-900 border border-gray-500/30 rounded-2xl p-8 text-center">
          <X className="w-16 h-16 text-gray-500 mx-auto mb-4" />
          <h2 className="text-2xl font-serif text-white mb-2">Сессия завершена</h2>
          <p className="text-gray-400 mb-6">Владелец закрыл сессию совместного анализа.</p>
          <button
            onClick={handleExit}
            className="px-6 py-3 bg-white text-black font-medium rounded-lg hover:bg-gray-200 transition-colors"
          >
            Перейти ко входу
          </button>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-[#141413] text-white flex flex-col">
      {/* Grain overlay */}
      <div className="fixed inset-0 bg-grain pointer-events-none z-50 opacity-50" />
      
      {/* Navigation Bar - same style as main page */}
      <nav className="fixed top-0 left-0 right-0 h-20 z-40 flex items-center justify-between px-8 bg-gradient-to-b from-black/80 to-transparent pointer-events-none">
        <div className="flex items-center gap-6 pointer-events-auto">
          <div className="flex items-center gap-3">
            <img src="/images/logo.svg" alt="Logo" className="w-8 h-8" />
            <span className="font-serif text-xl tracking-wide text-white drop-shadow-lg">Heritage Frame</span>
          </div>
        </div>
        
        <div className="pointer-events-auto flex items-center gap-4">
          {/* Status badges */}
          <div className="hidden sm:flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/20 border border-emerald-500/30 rounded-full text-emerald-400 text-sm backdrop-blur-sm">
              <Users size={14} />
              <span>{activeViewers}</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/20 border border-amber-500/30 rounded-full text-amber-400 text-sm backdrop-blur-sm">
              <Clock size={14} />
              <span>{formatTime(remainingTime)}</span>
            </div>
          </div>
          
          <button
            onClick={handleExit}
            className="p-2 text-gray-300 hover:text-white hover:bg-white/10 rounded-full transition-all"
            title="Выйти"
          >
            <LogOut size={20} />
          </button>
        </div>
      </nav>
      
      {/* Main content */}
      <main className="flex-1 pt-24 pb-24 md:pb-8">
        <div className="max-w-4xl mx-auto px-4">
          
          {/* Welcome message */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-full text-emerald-400 text-sm mb-4">
              <Sparkles size={16} />
              <span>Совместный анализ</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-serif text-white mb-2">
              Вы присоединились к обсуждению
            </h1>
            <p className="text-gray-400">
              Задавайте вопросы об этом произведении искусства
            </p>
          </motion.div>
          
          {/* Image and info card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden mb-8"
          >
            {/* Image */}
            <div className="aspect-video relative bg-black/50">
              <img
                src={session.image_url}
                alt="Анализируемое изображение"
                className="w-full h-full object-contain"
              />
            </div>
            
            {/* Info */}
            <div className="p-6">
              <div className="flex flex-wrap items-center justify-between gap-4 text-sm">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Palette className="w-5 h-5 text-gold-400" />
                    <span className="text-white font-medium">{session.top_artist || 'Неизвестно'}</span>
                  </div>
                  {session.top_style && (
                    <>
                      <span className="w-1.5 h-1.5 bg-gray-500 rounded-full" />
                      <span className="text-gray-400">{session.top_style}</span>
                    </>
                  )}
                  {session.top_genre && (
                    <>
                      <span className="w-1.5 h-1.5 bg-gray-500 rounded-full" />
                      <span className="text-gray-400">{session.top_genre}</span>
                    </>
                  )}
                </div>
                
                {/* Deep analysis badge */}
                {session.has_deep_analysis && (
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-[#827DBD]/10 border border-[#827DBD]/30 rounded-full">
                    <Brain size={14} className="text-[#827DBD]" />
                    <span className="text-[#827DBD] text-xs font-medium">Глубокий анализ</span>
                  </div>
                )}
              </div>
              
              {/* Mobile status badges */}
              <div className="flex sm:hidden items-center gap-3 mt-4 pt-4 border-t border-white/10">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/20 border border-emerald-500/30 rounded-full text-emerald-400 text-sm">
                  <Users size={14} />
                  <span>{activeViewers} активных</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/20 border border-amber-500/30 rounded-full text-amber-400 text-sm">
                  <Clock size={14} />
                  <span>{formatTime(remainingTime)}</span>
                </div>
              </div>
            </div>
          </motion.div>
          
          {/* Chat dialog */}
          {(messages.length > 0 || isStreaming) && (
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-8 max-h-[60vh] overflow-y-auto">
              <div className="space-y-6">
                {messages.map((msg, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex items-start gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                  >
                    {msg.role === 'user' ? (
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/20">
                        <User size={20} className="text-white" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 border border-gold-400/30" style={{ backgroundColor: '#141413' }}>
                        <img src="/images/logo.svg" alt="OMNIA" className="w-6 h-6" />
                      </div>
                    )}
                    <div className={`flex-1 min-w-0 overflow-hidden ${msg.role === 'user' ? 'text-right' : ''}`}>
                      <p className={`text-xs font-medium mb-2 uppercase tracking-wider ${msg.role === 'user' ? 'text-blue-400' : 'text-gold-400'}`}>
                        {msg.role === 'user' ? 'Вы' : 'OMNIA Engine'}
                      </p>
                      <div className={`prose prose-invert prose-sm max-w-none break-words overflow-wrap-anywhere ${
                        msg.role === 'user' 
                          ? 'bg-blue-500/10 border border-blue-500/20 rounded-2xl rounded-tr-sm px-4 py-3 inline-block max-w-[85%]' 
                          : 'bg-gold-500/5 border border-gold-500/20 rounded-2xl rounded-tl-sm px-5 py-4'
                      }`}>
                        <ReactMarkdown
                          components={{
                            p: ({children}) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
                            strong: ({children}) => <strong className="text-white font-semibold">{children}</strong>,
                            em: ({children}) => <em className="text-gold-300">{children}</em>,
                            ul: ({children}) => <ul className="list-disc pl-4 space-y-1 my-2">{children}</ul>,
                            ol: ({children}) => <ol className="list-decimal pl-4 space-y-1 my-2">{children}</ol>,
                            li: ({children}) => <li className="text-gray-300">{children}</li>,
                          }}
                        >{cleanThinkTags(msg.content)}</ReactMarkdown>
                      </div>
                    </div>
                  </motion.div>
                ))}
                
                {/* Streaming response */}
                {isStreaming && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-start gap-4"
                  >
                    {/* Avatar changes color when thinking */}
                    {hasThinkTags(currentStreamContent) ? (
                      <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg shadow-[#827DBD]/30" style={{ backgroundColor: '#827DBD' }}>
                        <Brain size={20} className="text-white animate-pulse" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 border border-gold-400/30" style={{ backgroundColor: '#141413' }}>
                        <img src="/images/logo.svg" alt="OMNIA" className="w-6 h-6" />
                      </div>
                    )}
                    <div className="flex-1 min-w-0 overflow-hidden">
                      <p className={`text-xs font-medium mb-2 uppercase tracking-wider ${hasThinkTags(currentStreamContent) ? 'text-[#827DBD]' : 'text-gold-400'}`}>
                        {hasThinkTags(currentStreamContent) ? 'OMNIA Engine думает...' : 'OMNIA Engine'}
                      </p>
                      
                      <div className={`rounded-2xl rounded-tl-sm px-5 py-4 prose prose-invert prose-sm max-w-none break-words overflow-wrap-anywhere ${
                        hasThinkTags(currentStreamContent) 
                          ? 'bg-[#827DBD]/10 border border-[#827DBD]/20' 
                          : 'bg-gold-500/5 border border-gold-500/20'
                      }`}>
                        {cleanThinkTags(currentStreamContent) ? (
                          <ReactMarkdown
                            components={{
                              p: ({children}) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
                              strong: ({children}) => <strong className="text-white font-semibold">{children}</strong>,
                              em: ({children}) => <em className="text-gold-300">{children}</em>,
                              ul: ({children}) => <ul className="list-disc pl-4 space-y-1 my-2">{children}</ul>,
                              ol: ({children}) => <ol className="list-decimal pl-4 space-y-1 my-2">{children}</ol>,
                              li: ({children}) => <li className="text-gray-300">{children}</li>,
                            }}
                          >{cleanThinkTags(currentStreamContent)}</ReactMarkdown>
                        ) : (
                          <div className="flex items-center gap-2 text-gray-400">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>{hasThinkTags(currentStreamContent) ? 'Анализирую...' : 'Генерирую ответ...'}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>
          )}
          {/* Error display */}
          {questionError && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm"
            >
              {questionError}
            </motion.div>
          )}
          
          {/* Question input - Desktop */}
          <div className="hidden md:block">
            <div className="flex gap-4">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleAskQuestion()}
                placeholder="Задайте вопрос об этом произведении..."
                disabled={isStreaming}
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-6 py-4 text-white placeholder-gray-500 focus:border-gold-500 focus:ring-1 focus:ring-gold-500/50 focus:outline-none transition-colors disabled:opacity-50"
              />
              <button
                onClick={handleAskQuestion}
                disabled={!question.trim() || isStreaming}
                className="px-6 py-4 bg-gradient-to-r from-gold-600 to-gold-500 text-black font-medium rounded-xl hover:shadow-[0_0_30px_rgba(212,175,55,0.3)] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isStreaming ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
                <span>Спросить</span>
              </button>
            </div>
          </div>
        </div>
      </main>
      
      {/* Question input - Mobile (fixed bottom) */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 bg-black/95 backdrop-blur-sm border-t border-white/10 p-4 z-40">
        <div className="flex gap-3">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleAskQuestion()}
            placeholder="Задайте вопрос..."
            disabled={isStreaming}
            className="flex-1 bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:border-gold-500 focus:ring-1 focus:ring-gold-500/50 focus:outline-none transition-colors disabled:opacity-50 text-sm"
          />
          <button
            onClick={handleAskQuestion}
            disabled={!question.trim() || isStreaming}
            className="px-4 py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-black rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isStreaming ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default CollaborativeView
