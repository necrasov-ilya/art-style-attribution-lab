import { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { analysisAPI, historyAPI, deepAnalysisAPI, collaborativeAPI } from '../api'
import { motion, AnimatePresence, useScroll, useTransform } from 'framer-motion'
import { QRCodeSVG } from 'qrcode.react'
import { 
  Upload, X, Search, Zap, LogOut, LogIn, Palette, Brush, BookOpen, 
  Sparkles, Loader2, Download, History, ChevronLeft, ChevronRight, 
  Maximize2, PanelRightClose, PanelRightOpen, Image as ImageIcon,
  Share2, Info, Layers, Eye, Menu, Clock, Sun, Compass, Heart, User,
  Users, Copy, Check, Link2, Brain
} from 'lucide-react'

// Clean think tags from LLM response
const cleanThinkTags = (text) => {
  if (!text) return ''
  // Remove <think>...</think> blocks
  let cleaned = text.replace(/<think[^>]*>[\s\S]*?<\/think>/gi, '')
  // Remove <thinking>...</thinking> blocks
  cleaned = cleaned.replace(/<thinking[^>]*>[\s\S]*?<\/thinking>/gi, '')
  // Remove unclosed <think> tags (streaming)
  cleaned = cleaned.replace(/<think[^>]*>[\s\S]*$/gi, '')
  cleaned = cleaned.replace(/<thinking[^>]*>[\s\S]*$/gi, '')
  // Clean up extra newlines
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n')
  return cleaned.trim()
}

// Check if text contains unclosed think tags (for "thinking" indicator)
const hasThinkingInProgress = (text) => {
  if (!text) return false
  // Has opening tag but no closing tag = still thinking
  const hasOpenThink = /<think[^>]*>/i.test(text)
  const hasCloseThink = /<\/think>/i.test(text)
  const hasOpenThinking = /<thinking[^>]*>/i.test(text)
  const hasCloseThinking = /<\/thinking>/i.test(text)
  return (hasOpenThink && !hasCloseThink) || (hasOpenThinking && !hasCloseThinking)
}

// Reusable blocked overlay component - minimal pulsing dot animation
const BlockedOverlay = ({ show, accentColor = 'gold' }) => {
  if (!show) return null
  
  const dotColors = {
    gold: 'bg-gold-400',
    purple: 'bg-purple-400',
    emerald: 'bg-emerald-400',
  }
  
  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center backdrop-blur-[2px] bg-black/20 rounded-2xl">
      <div className="flex gap-1.5">
        <div className={`w-2 h-2 rounded-full ${dotColors[accentColor]} animate-pulse`} style={{ animationDelay: '0ms' }} />
        <div className={`w-2 h-2 rounded-full ${dotColors[accentColor]} animate-pulse`} style={{ animationDelay: '150ms' }} />
        <div className={`w-2 h-2 rounded-full ${dotColors[accentColor]} animate-pulse`} style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  )
}

// Icon mapping for inline markers
const MARKER_ICONS = {
  palette: Palette,
  brush: Brush,
  layers: Layers,
  heart: Heart,
  clock: Clock,
  user: User,
  info: Info,
}

// Simple tooltip explanations for marker types
const MARKER_EXPLANATIONS = {
  color: (label, value) => `Цвет "${label}" (${value}) — один из ключевых оттенков в палитре произведения`,
  technique: (label) => `"${label}" — художественный приём или техника исполнения`,
  composition: (label) => `"${label}" — композиционный принцип организации пространства`,
  mood: (label) => `"${label}" — эмоциональное настроение, передаваемое произведением`,
  era: (label) => `"${label}" — художественное направление или исторический период`,
  artist: (label) => `${label} — художник, чьё влияние прослеживается в работе`,
}

// Global tooltip state - only one tooltip open at a time
let globalActiveTooltip = null
let globalTooltipSetter = null

// Inline marker component with tooltip
const InlineMarker = ({ type, value, label, icon, markerId }) => {
  const [showTooltip, setShowTooltip] = useState(false)
  
  // Close this tooltip when another opens
  useEffect(() => {
    const checkAndClose = () => {
      if (globalActiveTooltip !== markerId && showTooltip) {
        setShowTooltip(false)
      }
    }
    const interval = setInterval(checkAndClose, 50)
    return () => clearInterval(interval)
  }, [markerId, showTooltip])
  
  const handleClick = () => {
    if (showTooltip) {
      setShowTooltip(false)
      globalActiveTooltip = null
    } else {
      // Close any other open tooltip
      globalActiveTooltip = markerId
      setShowTooltip(true)
    }
  }
  const IconComponent = MARKER_ICONS[icon] || Info
  
  const explanation = MARKER_EXPLANATIONS[type]?.(label, value) || `${label}`
  
  // Color marker - just a colored square with hex on hover
  if (type === 'color' && value.startsWith('#')) {
    return (
      <span className="relative inline-block mx-0.5 group">
        <span 
          className="inline-block w-4 h-4 rounded border border-white/40 shadow-sm cursor-pointer align-middle hover:scale-125 transition-transform"
          style={{ backgroundColor: value }}
          onClick={handleClick}
          title={`${label}: ${value}`}
        />
        {/* Tooltip */}
        <AnimatePresence>
          {showTooltip && (
            <motion.div
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 5 }}
              className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-charcoal-800 border border-white/20 rounded-lg shadow-xl text-sm whitespace-nowrap"
            >
              <div className="flex items-center gap-2">
                <span 
                  className="w-5 h-5 rounded border border-white/30" 
                  style={{ backgroundColor: value }}
                />
                <span className="text-white font-medium">{label}</span>
                <span className="text-gray-400 font-mono text-xs">{value}</span>
              </div>
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-charcoal-800" />
            </motion.div>
          )}
        </AnimatePresence>
      </span>
    )
  }
  
  // Style-based marker colors
  const markerStyles = {
    technique: 'bg-purple-500/20 border-purple-500/30 text-purple-200 hover:border-purple-400 hover:bg-purple-500/30',
    composition: 'bg-blue-500/20 border-blue-500/30 text-blue-200 hover:border-blue-400 hover:bg-blue-500/30',
    mood: 'bg-pink-500/20 border-pink-500/30 text-pink-200 hover:border-pink-400 hover:bg-pink-500/30',
    era: 'bg-amber-500/20 border-amber-500/30 text-amber-200 hover:border-amber-400 hover:bg-amber-500/30',
    artist: 'bg-green-500/20 border-green-500/30 text-green-200 hover:border-green-400 hover:bg-green-500/30',
  }
  
  const style = markerStyles[type] || 'bg-white/10 border-white/20 text-gray-200'
  
  return (
    <span className="relative inline-block">
      <span 
        className={`inline-flex items-center gap-1 px-2 py-0.5 mx-0.5 rounded-full text-sm border transition-all cursor-pointer ${style}`}
        onClick={handleClick}
      >
        <IconComponent size={12} className="opacity-70" />
        <span>{label}</span>
      </span>
      {/* Tooltip */}
      <AnimatePresence>
        {showTooltip && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 5 }}
            className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-charcoal-800 border border-white/20 rounded-lg shadow-xl text-sm max-w-xs"
          >
            <p className="text-gray-300">{explanation}</p>
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-charcoal-800" />
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  )
}

// Parse and render text with inline markers - supports {type|value|label} format
const RichTextWithMarkers = ({ text, markers = [] }) => {
  // If no markers provided, try to parse them from raw text
  const markerRegex = /\{(\w+)\|([^}|]+)(?:\|([^}]+))?\}/g
  
  // Parse markers from text if not provided
  const parseMarkers = (inputText) => {
    const parsed = []
    let match
    while ((match = markerRegex.exec(inputText)) !== null) {
      parsed.push({
        full: match[0],
        type: match[1],
        value: match[2],
        label: match[3] || match[2]
      })
    }
    return parsed
  }
  
  // Render text with inline markers replaced by React components
  const renderWithMarkers = (inputText) => {
    if (!inputText) return null
    
    const parts = []
    let lastIndex = 0
    let match
    const regex = /\{(\w+)\|([^}|]+)(?:\|([^}]+))?\}/g
    
    while ((match = regex.exec(inputText)) !== null) {
      // Add text before marker
      if (match.index > lastIndex) {
        parts.push({ type: 'text', content: inputText.slice(lastIndex, match.index) })
      }
      // Add marker
      parts.push({
        type: 'marker',
        markerType: match[1],
        value: match[2],
        label: match[3] || match[2]
      })
      lastIndex = match.index + match[0].length
    }
    // Add remaining text
    if (lastIndex < inputText.length) {
      parts.push({ type: 'text', content: inputText.slice(lastIndex) })
    }
    
    return parts.map((part, i) => {
      if (part.type === 'marker') {
        const markerId = `${part.markerType}-${part.value}-${i}`
        return <InlineMarker key={i} type={part.markerType} value={part.value} label={part.label} icon={getMarkerIcon(part.markerType)} markerId={markerId} />
      }
      return <span key={i}>{part.content}</span>
    })
  }
  
  // Get appropriate icon for marker type
  const getMarkerIcon = (type) => {
    const icons = {
      color: 'palette',
      technique: 'brush',
      composition: 'layers',
      mood: 'heart',
      era: 'clock',
      artist: 'user'
    }
    return icons[type] || 'info'
  }
  
  // Custom ReactMarkdown components that support inline markers
  return (
    <ReactMarkdown
      components={{
        h2: ({node, children, ...props}) => (
          <h2 className="text-2xl font-serif text-white mt-8 mb-4 pb-2 border-b border-white/10" {...props}>
            {typeof children === 'string' ? renderWithMarkers(children) : children}
          </h2>
        ),
        h3: ({node, children, ...props}) => (
          <h3 className="text-lg font-medium text-gold-400 mt-6 mb-3" {...props}>
            {typeof children === 'string' ? renderWithMarkers(children) : children}
          </h3>
        ),
        p: ({node, children, ...props}) => (
          <p className="text-gray-300 mb-4 leading-relaxed text-base" {...props}>
            {Array.isArray(children) 
              ? children.map((child, i) => typeof child === 'string' ? <span key={i}>{renderWithMarkers(child)}</span> : child)
              : typeof children === 'string' ? renderWithMarkers(children) : children
            }
          </p>
        ),
        strong: ({node, children, ...props}) => (
          <strong className="text-white font-semibold" {...props}>
            {typeof children === 'string' ? renderWithMarkers(children) : children}
          </strong>
        ),
        em: ({node, children, ...props}) => (
          <em className="text-gray-400 italic" {...props}>
            {typeof children === 'string' ? renderWithMarkers(children) : children}
          </em>
        ),
        li: ({node, children, ...props}) => (
          <li className="text-gray-300 mb-2" {...props}>
            {Array.isArray(children) 
              ? children.map((child, i) => typeof child === 'string' ? <span key={i}>{renderWithMarkers(child)}</span> : child)
              : typeof children === 'string' ? renderWithMarkers(children) : children
            }
          </li>
        ),
        ul: ({node, ...props}) => <ul className="list-disc list-inside mb-4 space-y-1" {...props} />,
      }}
    >
      {text}
    </ReactMarkdown>
  )
}

function Analyze() {
  const navigate = useNavigate()
  const { logout, user } = useAuth()
  const isGuest = user?.isGuest === true
  
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef(null)
  
  // Analysis phase: 'idle' | 'analyzing' | 'vision' | 'streaming' | 'done'
  const [analysisPhase, setAnalysisPhase] = useState('idle')
  const [streamingText, setStreamingText] = useState('')
  const [visionResult, setVisionResult] = useState(null)
  
  // UI State
  const [history, setHistory] = useState([])
  const [showHistory, setShowHistory] = useState(false)
  const [showDetails, setShowDetails] = useState(true)
  
  // Generation state
  const [generating, setGenerating] = useState(false)
  const [generationPrompt, setGenerationPrompt] = useState('')
  const [generatedImages, setGeneratedImages] = useState(null)
  const [generationError, setGenerationError] = useState('')
  
  // Deep Analysis State
  const [deepAnalysisActive, setDeepAnalysisActive] = useState(false)
  const [deepAnalysisStep, setDeepAnalysisStep] = useState(0)
  const [deepAnalysisResults, setDeepAnalysisResults] = useState(null)
  const [deepAnalysisError, setDeepAnalysisError] = useState('')
  
  // Current history item id (for saving deep analysis)
  const [currentHistoryItemId, setCurrentHistoryItemId] = useState(null)

  // Collaborative Session State
  const [collabSession, setCollabSession] = useState(null)
  const [collabLoading, setCollabLoading] = useState(false)
  const [collabError, setCollabError] = useState('')
  const [collabRemainingTime, setCollabRemainingTime] = useState(0)
  const [collabViewers, setCollabViewers] = useState(0)
  const [linkCopied, setLinkCopied] = useState(false)
  const collabTimerRef = useRef(null)
  const collabPollRef = useRef(null)

  // Deep Analysis Steps for progress indicator
  const DEEP_ANALYSIS_STEPS = [
    { key: 'features', label: 'Извлечение признаков', icon: Eye },
    { key: 'color', label: 'Психология цвета', icon: Palette },
    { key: 'composition', label: 'Анализ композиции', icon: Layers },
    { key: 'scene', label: 'Сюжетный анализ', icon: Search },
    { key: 'technique', label: 'Техника исполнения', icon: Brush },
    { key: 'historical', label: 'Исторический контекст', icon: BookOpen },
    { key: 'summary', label: 'Синтез результатов', icon: Sparkles },
  ]

  // Scroll parallax hooks
  const { scrollYProgress } = useScroll()
  const imageScale = useTransform(scrollYProgress, [0, 1], [1, 0.9])
  const imageOpacity = useTransform(scrollYProgress, [0, 0.6], [1, 0])
  const imageY = useTransform(scrollYProgress, [0, 1], [0, 150])

  // Ref to track streaming text for callback access
  const streamingTextRef = useRef('')
  
  // Keep ref in sync with state
  useEffect(() => {
    streamingTextRef.current = streamingText
  }, [streamingText])
  
  // When analysis phase becomes 'done', apply cleaned text to result
  useEffect(() => {
    if (analysisPhase === 'done' && streamingText) {
      const cleanedText = cleanThinkTags(streamingText)
      setResult(prev => prev ? {
        ...prev,
        explanation: { 
          text: cleanedText, 
          source: prev.explanation?.source || 'llm' 
        },
      } : prev)
    }
  }, [analysisPhase, streamingText])

  // Load history
  useEffect(() => {
    if (!isGuest) {
      loadHistory()
    }
  }, [isGuest])

  const loadHistory = () => {
    historyAPI.getAll().then(res => setHistory(res.data.items || [])).catch(console.error)
  }

  const handleHistoryItemClick = (item) => {
    setFile(null)
    setPreview(item.image_url)

    // Clean think tags from explanation if present
    const cleanedResult = {
      ...item.analysis_result,
      explanation: item.analysis_result?.explanation ? {
        ...item.analysis_result.explanation,
        text: cleanThinkTags(item.analysis_result.explanation.text || '')
      } : item.analysis_result?.explanation
    }
    setResult(cleanedResult)
    setCurrentHistoryItemId(item.id)

    // Reset all blocking states
    setAnalysisPhase('idle')
    setStreamingText('')
    setVisionResult(null)
    setLoading(false)
    setGeneratedImages(null)

    // Restore deep analysis if exists
    if (item.deep_analysis_result) {
      setDeepAnalysisResults(item.deep_analysis_result)
      setDeepAnalysisActive(false)
      setDeepAnalysisStep(DEEP_ANALYSIS_STEPS.length)
    } else {
      setDeepAnalysisResults(null)
      setDeepAnalysisActive(false)
      setDeepAnalysisStep(0)
    }

    // Reset collaborative session
    resetCollabSession()

    setShowHistory(false)
    setTimeout(() => {
      window.scrollTo({ top: window.innerHeight * 0.8, behavior: 'smooth' })
    }, 300)
  }

  const handleFileSelect = (selectedFile) => {
    if (!selectedFile) return
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('Размер файла должен быть меньше 10MB')
      return
    }
    setFile(selectedFile)
    setPreview(URL.createObjectURL(selectedFile))
    setError('')
    setResult(null)
    setGeneratedImages(null)
    setCurrentHistoryItemId(null)
    // Reset analysis streaming state
    setAnalysisPhase('idle')
    setStreamingText('')
    setVisionResult(null)
    // Reset deep analysis state
    setDeepAnalysisActive(false)
    setDeepAnalysisStep(0)
    setDeepAnalysisResults(null)
    setDeepAnalysisError('')
    // Reset collaborative session
    resetCollabSession()
  }

  // === Collaborative Session Functions ===
  
  const resetCollabSession = useCallback(() => {
    if (collabTimerRef.current) clearInterval(collabTimerRef.current)
    if (collabPollRef.current) clearInterval(collabPollRef.current)
    setCollabSession(null)
    setCollabRemainingTime(0)
    setCollabViewers(0)
    setCollabError('')
    setLinkCopied(false)
  }, [])

  const handleCreateCollabSession = async () => {
    if (!result || isGuest) return
    
    setCollabLoading(true)
    setCollabError('')
    
    try {
      const response = await collaborativeAPI.create({
        analysis_data: result,
        image_url: result.image_path
      })
      
      setCollabSession(response.data)
      setCollabRemainingTime(response.data.remaining_seconds)
      setCollabViewers(response.data.active_viewers)
      
      // Start countdown timer
      collabTimerRef.current = setInterval(() => {
        setCollabRemainingTime(prev => {
          if (prev <= 1) {
            resetCollabSession()
            return 0
          }
          return prev - 1
        })
      }, 1000)
      
      // Poll for viewer count every 10 seconds
      collabPollRef.current = setInterval(async () => {
        try {
          const viewersRes = await collaborativeAPI.getViewers(response.data.id)
          setCollabViewers(viewersRes.data.active_viewers)
          setCollabRemainingTime(viewersRes.data.remaining_seconds)
        } catch (e) {
          console.warn('Failed to fetch viewers:', e)
        }
      }, 10000)
      
    } catch (err) {
      console.error('Failed to create collab session:', err)
      setCollabError(err.response?.data?.detail || 'Не удалось создать сессию')
    } finally {
      setCollabLoading(false)
    }
  }

  const handleCloseCollabSession = async () => {
    if (!collabSession) return
    
    try {
      await collaborativeAPI.close(collabSession.id)
    } catch (err) {
      console.warn('Failed to close session:', err)
    }
    
    resetCollabSession()
  }

  const handleCopyCollabLink = async () => {
    if (!collabSession) return
    
    const link = `${window.location.origin}/collab/${collabSession.id}`
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(link)
      } else {
        // Fallback for HTTP or older browsers
        const textArea = document.createElement('textarea')
        textArea.value = link
        textArea.style.position = 'fixed'
        textArea.style.left = '-999999px'
        textArea.style.top = '-999999px'
        document.body.appendChild(textArea)
        textArea.focus()
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
      }
      setLinkCopied(true)
      setTimeout(() => setLinkCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
      // Last resort fallback
      try {
        const textArea = document.createElement('textarea')
        textArea.value = link
        textArea.style.position = 'fixed'
        textArea.style.left = '-999999px'
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        setLinkCopied(true)
        setTimeout(() => setLinkCopied(false), 2000)
      } catch (e) {
        console.error('Fallback copy failed:', e)
      }
    }
  }

  const formatCollabTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (collabTimerRef.current) clearInterval(collabTimerRef.current)
      if (collabPollRef.current) clearInterval(collabPollRef.current)
    }
  }, [])

  const handleAnalyze = async () => {
    if (!file || loading) return
    
    setLoading(true)
    setError('')
    setAnalysisPhase('analyzing')
    setStreamingText('')
    setVisionResult(null)
    setResult(null)
    
    try {
      let predictionsData = null // Store for vision callback
      
      await analysisAPI.analyzeStream(file, {
        onPredictions: (data) => {
          // ML predictions received
          predictionsData = data // Store for later use
          const needsVision = data.needs_vision
          
          if (needsVision) {
            // Unknown Artist - wait for vision, don't show results yet
            setAnalysisPhase('vision')
          } else {
            // Known Artist - show predictions immediately, start streaming
            setResult({
              success: true,
              image_path: data.image_path,
              top_artists: data.top_artists,
              top_genres: data.top_genres,
              top_styles: data.top_styles,
              explanation: { text: '', source: 'streaming' },
            })
            setAnalysisPhase('streaming')
            setLoading(false) // Stop image blur
            
            // Scroll to results
            setTimeout(() => {
              window.scrollTo({ top: window.innerHeight * 0.8, behavior: 'smooth' })
            }, 100)
          }
        },
        
        onVision: (data) => {
          // Vision analysis complete - now show results
          setVisionResult(data)
          
          // Determine artist name to display
          let artistSlug = 'unknown-artist'
          let artistDisplay = data.artist_name_ru || data.artist_name || 'Неизвестный художник'
          if (data.artist_name && data.confidence !== 'none') {
            artistSlug = data.artist_name.toLowerCase().replace(/\s+/g, '-')
          }
          
          // Build result with vision data
          const topArtists = data.artist_name && data.confidence !== 'none'
            ? [{ artist_slug: artistSlug, probability: 0, index: -1 }, ...(predictionsData?.top_artists?.slice(1) || [])]
            : predictionsData?.top_artists || []
          
          setResult({
            success: true,
            image_path: predictionsData?.image_path,
            top_artists: topArtists,
            top_genres: predictionsData?.top_genres || [],
            top_styles: predictionsData?.top_styles || [],
            explanation: { text: '', source: 'streaming' },
            vision_result: data,
          })
          
          setAnalysisPhase('streaming')
          setLoading(false) // Stop image blur
          
          // Scroll to results
          setTimeout(() => {
            window.scrollTo({ top: window.innerHeight * 0.8, behavior: 'smooth' })
          }, 100)
        },
        
        onText: (chunk) => {
          // Streaming text chunk
          setStreamingText(prev => prev + chunk)
        },
        
        onComplete: (data) => {
          // Analysis complete - useEffect will handle applying cleaned text
          setAnalysisPhase('done')
          setLoading(false)
          
          if (data.history_id) {
            setCurrentHistoryItemId(data.history_id)
          }
          
          // Store the explanation source for useEffect to use
          setResult(prev => prev ? {
            ...prev,
            explanation: { 
              ...prev.explanation,
              source: data.explanation_source || 'llm' 
            },
          } : prev)
          
          if (!isGuest) loadHistory()
        },
        
        onError: (errorMsg) => {
          setError(errorMsg || 'Ошибка анализа. Попробуйте снова.')
          setAnalysisPhase('idle')
          setLoading(false)
        },
      })
    } catch (err) {
      setError('Ошибка анализа. Попробуйте снова.')
      setAnalysisPhase('idle')
      setLoading(false)
    }
  }
  
  // Update result explanation when streaming text changes (only during streaming phase)
  // During streaming, show raw text; final cleanup happens when phase becomes 'done'
  useEffect(() => {
    if (analysisPhase === 'streaming' && streamingText && result) {
      // During streaming, show the cleaned text for display
      const displayText = cleanThinkTags(streamingText)
      setResult(prev => prev ? {
        ...prev,
        explanation: { 
          text: displayText, 
          source: prev.explanation?.source || 'streaming' 
        },
      } : prev)
    }
  }, [streamingText, analysisPhase])

  const handleDeepAnalysis = async () => {
    if (!result?.image_path) return

    setDeepAnalysisActive(true)
    setDeepAnalysisStep(0)
    setDeepAnalysisError('')
    setDeepAnalysisResults(null)

    let stepInterval = null

    try {
      // Simulate step progression for UX (actual API does all at once)
      stepInterval = setInterval(() => {
        setDeepAnalysisStep(prev => Math.min(prev + 1, DEEP_ANALYSIS_STEPS.length - 1))
      }, 2000)

      const response = await deepAnalysisAPI.analyzeFull(result.image_path)

      clearInterval(stepInterval)
      setDeepAnalysisStep(DEEP_ANALYSIS_STEPS.length)
      setDeepAnalysisResults(response.data)
      setDeepAnalysisActive(false)  // Analysis complete - unblock other sections
      
      // Save deep analysis to history for authenticated users
      if (!isGuest && currentHistoryItemId) {
        try {
          await historyAPI.updateDeepAnalysis(currentHistoryItemId, response.data)
          loadHistory() // Refresh history
        } catch (saveErr) {
          console.warn('Failed to save deep analysis to history:', saveErr)
        }
      } else if (!isGuest && !currentHistoryItemId) {
        // If no currentHistoryItemId, try to find it from the latest history item
        try {
          const historyRes = await historyAPI.getAll(1, 0)
          const latestItem = historyRes.data.items?.[0]
          if (latestItem && latestItem.image_url === result.image_path) {
            setCurrentHistoryItemId(latestItem.id)
            await historyAPI.updateDeepAnalysis(latestItem.id, response.data)
            loadHistory()
          }
        } catch (e) {
          console.warn('Could not save deep analysis to history:', e)
        }
      }
      
      // Sync deep analysis to active collaborative session
      if (collabSession && result) {
        try {
          const updatedAnalysisData = {
            ...result,
            deep_analysis_result: response.data
          }
          await collaborativeAPI.updateAnalysis(collabSession.id, updatedAnalysisData)
          console.log('Deep analysis synced to collaborative session')
        } catch (syncErr) {
          console.warn('Failed to sync deep analysis to collaborative session:', syncErr)
        }
      }
      
    } catch (err) {
      // ВАЖНО: очистить интервал при ошибке
      if (stepInterval) {
        clearInterval(stepInterval)
      }
      console.error('Deep analysis failed:', err)
      setDeepAnalysisError(err.response?.data?.detail || 'Ошибка глубокого анализа')
      setDeepAnalysisActive(false)
      setDeepAnalysisStep(0)  // Сбросить прогресс
    }
  }

  const resetDeepAnalysis = () => {
    setDeepAnalysisActive(false)
    setDeepAnalysisStep(0)
    setDeepAnalysisResults(null)
    setDeepAnalysisError('')
  }

  const handleGenerate = async () => {
    if (!result) return
    setGenerating(true)
    setGenerationError('')
    try {
      const response = await analysisAPI.generate({
        artist_slug: result.top_artists[0].artist_slug,
        style_name: result.top_styles?.[0]?.name,
        genre_name: result.top_genres?.[0]?.name,
        user_prompt: generationPrompt,
        count: 4
      })
      setGeneratedImages(response.data)
    } catch (err) {
      setGenerationError('Ошибка генерации.')
    } finally {
      setGenerating(false)
    }
  }

  const handleDownload = async (url, filename) => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename || 'generated-art.png';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (e) {
      console.error('Download failed', e);
      window.open(url, '_blank');
    }
  }

  const formatName = (slug) => slug?.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

  return (
    <div className="min-h-screen w-full bg-[#141413] text-alabaster-100 font-sans selection:bg-gold-500/30 relative overflow-x-hidden">
      <div className="fixed inset-0 bg-grain pointer-events-none z-50 opacity-50" />
      
      {/* Navigation Bar */}
      <nav className="fixed top-0 left-0 right-0 h-20 z-40 flex items-center justify-between px-8 bg-gradient-to-b from-black/80 to-transparent pointer-events-none">
        <div className="flex items-center gap-6 pointer-events-auto">
          <div className="flex items-center gap-3">
            <img src="/images/logo.svg" alt="Logo" className="w-8 h-8" />
            <span className="font-serif text-xl tracking-wide text-white drop-shadow-lg">Heritage Frame</span>
          </div>
        </div>
        
        <div className="pointer-events-auto flex items-center gap-4">
          {!isGuest && (
            <button 
              onClick={() => setShowHistory(true)}
              className="p-2 text-gray-300 hover:text-white hover:bg-white/10 rounded-full transition-all"
              title="История"
            >
              <History size={20} />
            </button>
          )}
          
          {isGuest ? (
            <button 
              onClick={() => { logout(); navigate('/login'); }} 
              className="px-6 py-2 bg-white text-black font-medium text-sm hover:bg-gray-200 transition-colors rounded-sm shadow-lg"
            >
              Войти
            </button>
          ) : (
            <button onClick={logout} className="p-2 text-gray-300 hover:text-white hover:bg-white/10 rounded-full transition-all">
              <LogOut size={20} />
            </button>
          )}
        </div>
      </nav>

      {/* History Sidebar */}
      <AnimatePresence>
        {showHistory && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowHistory(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            />
            <motion.div 
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className="fixed top-0 right-0 h-full w-80 bg-charcoal-900 border-l border-white/10 z-50 shadow-2xl overflow-y-auto custom-scrollbar"
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-8">
                  <h2 className="font-serif text-xl text-white">История коллекции</h2>
                  <button onClick={() => setShowHistory(false)} className="text-gray-400 hover:text-white">
                    <X size={20} />
                  </button>
                </div>
                
                <div className="space-y-4">
                  {history.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <Clock className="w-8 h-8 mx-auto mb-3 opacity-50" />
                      <p className="text-sm">История пуста</p>
                    </div>
                  ) : (
                    history.map((item) => (
                      <div 
                        key={item.id} 
                        onClick={() => handleHistoryItemClick(item)}
                        className="group relative aspect-video bg-black/40 border border-white/5 hover:border-gold-500/30 transition-all rounded overflow-hidden cursor-pointer"
                      >
                        <img src={item.image_url} alt="" className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-opacity" />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-transparent to-transparent p-4 flex flex-col justify-end">
                          <p className="text-white font-serif text-sm truncate">{formatName(item.top_artist_slug)}</p>
                          <p className="text-xs text-gold-500">{new Date(item.created_at).toLocaleDateString()}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Hero Section (Image) */}
      <div className="relative min-h-screen flex flex-col items-center justify-center p-8">
        {/* Background Ambient */}
        {preview && (
          <motion.div 
            style={{ opacity: imageOpacity }}
            className="fixed inset-0 z-0 overflow-hidden"
          >
            {/* Deep atmospheric background */}
            <div 
              className="absolute inset-0 bg-cover bg-center blur-[100px] opacity-50 scale-125 saturate-200"
              style={{ backgroundImage: `url(${preview})` }}
            />
            {/* Central focused glow */}
            <div 
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[70vw] h-[70vw] bg-cover bg-center blur-[80px] opacity-60 mix-blend-screen rounded-full animate-pulse"
              style={{ backgroundImage: `url(${preview})` }}
            />
            {/* Vignette to focus attention */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_10%,rgba(20,20,19,0.9)_100%)]" />
          </motion.div>
        )}

        <motion.div 
          style={{ scale: result ? imageScale : 1, y: result ? imageY : 0 }}
          className="relative z-10 w-full max-w-5xl mx-auto flex flex-col items-center"
        >
          <AnimatePresence mode="wait">
            {!preview ? (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="w-full max-w-xl"
              >
                <div 
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault()
                    setDragging(false)
                    handleFileSelect(e.dataTransfer.files[0])
                  }}
                  className={`
                    aspect-[4/3] border border-white/10 bg-white/5 backdrop-blur-sm flex flex-col items-center justify-center cursor-pointer transition-all duration-500 group relative overflow-hidden
                    ${dragging ? 'border-gold-500 bg-gold-500/10' : 'hover:border-white/20 hover:bg-white/10'}
                  `}
                >
                  {/* Decorative Frame Corners */}
                  <div className="absolute top-4 left-4 w-4 h-4 border-t border-l border-white/30" />
                  <div className="absolute top-4 right-4 w-4 h-4 border-t border-r border-white/30" />
                  <div className="absolute bottom-4 left-4 w-4 h-4 border-b border-l border-white/30" />
                  <div className="absolute bottom-4 right-4 w-4 h-4 border-b border-r border-white/30" />

                  <input type="file" ref={fileInputRef} onChange={(e) => handleFileSelect(e.target.files[0])} className="hidden" accept="image/*" />
                  
                  <div className="text-center p-8 relative z-10">
                    <div className="w-16 h-16 border border-white/20 rounded-full flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-500">
                      <Upload className="w-6 h-6 text-gray-400 group-hover:text-white transition-colors" />
                    </div>
                    <h2 className="font-serif text-3xl text-white mb-3">Загрузить изображение</h2>
                    <p className="text-gray-400 font-light tracking-wide text-sm">Перетащите или нажмите для выбора</p>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div 
                layoutId="preview-image"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.3 } }}
                className="relative w-full flex flex-col items-center"
              >
                <div className="relative shadow-2xl group w-fit mx-auto">
                  <img 
                    src={preview} 
                    alt="Preview" 
                    className={`
                      max-h-[70vh] w-auto object-contain shadow-[0_20px_50px_rgba(0,0,0,0.5)]
                      transition-all duration-[2000ms] ease-out
                      ${loading ? 'blur-md grayscale scale-95 opacity-80' : 'blur-0 grayscale-0 scale-100 opacity-100'}
                    `} 
                  />
                  
                  {/* Developing Overlay */}
                  {loading && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="w-full h-full bg-black/20 backdrop-blur-[2px] animate-pulse" />
                      <div className="absolute text-gold-500 font-serif tracking-widest text-2xl uppercase animate-bounce drop-shadow-lg">
                        {analysisPhase === 'vision' ? 'Нужно больше времени...' : 
                         analysisPhase === 'streaming' ? 'Генерация анализа...' : 
                         'Анализ...'}
                      </div>
                    </div>
                  )}
                </div>

                {/* Controls - centered below image */}
                <div className={`flex flex-col items-center mt-6 transition-opacity duration-300 ${loading ? 'opacity-0' : 'opacity-100'}`}>
                  <div className="flex items-center gap-4">
                    {!result && (
                      <button 
                        onClick={handleAnalyze}
                        disabled={loading || analysisPhase !== 'idle'}
                        className="px-8 py-3 bg-white text-black font-serif font-medium tracking-wide hover:bg-gray-200 transition-colors shadow-lg whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Анализировать
                      </button>
                    )}
                    <button 
                      onClick={() => { setFile(null); setPreview(null); setResult(null) }}
                      className="p-3 bg-black/50 backdrop-blur text-white border border-white/10 hover:bg-white hover:text-black transition-colors rounded-full"
                    >
                      <X size={20} />
                    </button>
                  </div>
                  
                  {/* Scroll Indicator - now part of the same centered column */}
                  {result && (
                    <motion.div 
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="mt-8 text-white/50 flex flex-col items-center gap-2 animate-bounce"
                    >
                      <span className="text-xs uppercase tracking-widest">Листайте вниз</span>
                      <ChevronRight className="rotate-90" />
                    </motion.div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
        
      </div>

      {/* Article Section (Parallax Overlay) */}
      <AnimatePresence>
        {result && (
          <motion.div 
            initial={{ opacity: 0, y: 100 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="relative z-20 bg-[#141413] min-h-screen border-t border-white/10 shadow-[0_-50px_100px_rgba(0,0,0,0.5)]"
          >
            <div className="max-w-4xl mx-auto px-8 py-24">
              
              {/* Header */}
              <div className="mb-20 text-center">
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  className="inline-block mb-6"
                >
                  <span className={`px-4 py-1.5 border rounded-full text-xs font-bold tracking-[0.2em] uppercase ${
                    result.vision_result?.is_photo 
                      ? 'border-blue-500/30 text-blue-400 bg-blue-500/5' 
                      : 'border-gold-500/30 text-gold-500 bg-gold-500/5'
                  }`}>
                    {result.vision_result?.is_photo ? 'Фотография' : 'Отчет об атрибуции'}
                  </span>
                </motion.div>
                
                <motion.h1 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.1 }}
                  className="font-serif text-6xl md:text-7xl text-white mb-8 leading-tight"
                >
                  {result.vision_result?.is_photo 
                    ? (result.vision_result?.artist_name_ru || 'Фотография')
                    : formatName(result.top_artists[0].artist_slug)}
                </motion.h1>
                
                <motion.div 
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.2 }}
                  className="flex flex-wrap items-center justify-center gap-6 text-sm text-gray-400"
                >
                  <span className="px-4 py-2 border border-white/10 rounded-full hover:border-white/30 transition-colors cursor-default">
                    {formatName(result.top_styles?.[0]?.name)}
                  </span>
                  <span className="w-1.5 h-1.5 bg-gold-500 rounded-full" />
                  <span className="px-4 py-2 border border-white/10 rounded-full hover:border-white/30 transition-colors cursor-default">
                    {formatName(result.top_genres?.[0]?.name)}
                  </span>
                </motion.div>
              </div>

              {/* Confidence Meter */}
              <div className="mb-24 grid grid-cols-3 gap-8 border-y border-white/10 py-12">
                <div className="text-center border-r border-white/10">
                  <span className="block text-4xl font-serif text-white mb-2">{Math.min(95, (result.top_artists[0].probability * 100 * 35)).toFixed(0)}%</span>
                  <span className="text-xs text-gray-500 uppercase tracking-wider">Уверенность</span>
                </div>
                <div className="text-center border-r border-white/10">
                  <span className="block text-4xl font-serif text-white mb-2">129</span>
                  <span className="text-xs text-gray-500 uppercase tracking-wider">Выборка</span>
                </div>
                <div className="text-center">
                  <span className="block text-4xl font-serif text-white mb-2">AI</span>
                  <span className="text-xs text-gray-500 uppercase tracking-wider">AI Модель</span>
                </div>
              </div>

              {/* Article Content */}
              <div className="prose prose-invert prose-lg max-w-none font-serif leading-relaxed text-gray-300 mb-24">
                {/* Thinking indicator during streaming - styled like CollaborativeView */}
                {analysisPhase === 'streaming' && hasThinkingInProgress(streamingText) && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-5 mb-8 p-6 rounded-2xl bg-gradient-to-br from-[#827DBD]/15 to-[#827DBD]/5 border border-[#827DBD]/30 shadow-lg shadow-[#827DBD]/10 backdrop-blur-sm"
                  >
                    <div className="w-14 h-14 rounded-full flex items-center justify-center flex-shrink-0 shadow-xl shadow-[#827DBD]/40 relative" style={{ backgroundColor: '#827DBD' }}>
                      <Brain size={26} className="text-white animate-pulse" />
                      <div className="absolute inset-0 rounded-full bg-white/20 animate-ping" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-bold mb-1.5 uppercase tracking-widest text-[#827DBD]">
                        OMNIA Engine думает...
                      </p>
                      <p className="text-base text-gray-300 font-light leading-relaxed">
                        Анализирую стилистические особенности произведения
                      </p>
                    </div>
                  </motion.div>
                )}
                <ReactMarkdown 
                  components={{
                    h2: ({node, ...props}) => <h2 className="text-3xl font-serif text-white mt-12 mb-6 border-b border-white/10 pb-4" {...props} />,
                    h3: ({node, ...props}) => <h3 className="text-xl font-sans font-medium text-gold-400 mt-8 mb-4 uppercase tracking-wide" {...props} />,
                    p: ({node, ...props}) => <p className="mb-6 font-light text-gray-300 text-xl leading-9" {...props} />,
                    strong: ({node, ...props}) => <strong className="font-medium text-white" {...props} />,
                    ul: ({node, ...props}) => <ul className="list-disc pl-4 space-y-3 my-6 text-gray-400" {...props} />,
                  }}
                >
                  {result.explanation.text}
                </ReactMarkdown>
              </div>

              {/* Deep Analysis Section - Hidden for guests, blocked during streaming */}
              {!isGuest && (
              <div className={`mb-24 bg-white/5 border border-white/10 rounded-2xl p-8 md:p-12 relative overflow-hidden ${result.vision_result?.is_photo ? 'opacity-60' : ''}`}>
                <div className="absolute top-0 right-0 p-4 opacity-10">
                  <Sparkles size={120} />
                </div>
                
                <BlockedOverlay show={analysisPhase === 'streaming' && !result.vision_result?.is_photo} accentColor="gold" />
                
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-8">
                    <h3 className="font-serif text-3xl text-white">Глубокий анализ</h3>
                    <span className="text-xs text-gold-500 border border-gold-500/30 px-3 py-1 rounded-full bg-gold-500/10 font-bold tracking-wider">AI PRO SUITE</span>
                  </div>
                  
                  {/* Unavailable for photos */}
                  {result.vision_result?.is_photo ? (
                    <div className="text-center py-8">
                      <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gray-800 flex items-center justify-center">
                        <ImageIcon size={32} className="text-gray-500" />
                      </div>
                      <p className="text-gray-400 mb-4 max-w-2xl mx-auto">
                        Глубокий анализ недоступен для фотографий
                      </p>
                      <p className="text-gray-500 text-sm max-w-xl mx-auto">
                        Этот инструмент предназначен для анализа произведений искусства — картин, рисунков и гравюр. 
                        Для фотографий доступно только базовое описание.
                      </p>
                    </div>
                  ) : (
                  <>
                  {/* Launch Button - show when no analysis running */}
                  {!deepAnalysisActive && !deepAnalysisResults && (
                    <div className="text-center py-8">
                      <p className="text-gray-400 mb-8 max-w-2xl mx-auto">
                        Получите развёрнутое искусствоведческое исследование с анализом цвета, композиции, 
                        техники и исторического контекста — всё в одном связном тексте музейного качества.
                      </p>
                      <button 
                        onClick={handleDeepAnalysis}
                        className="px-12 py-6 bg-gradient-to-r from-gold-600 to-gold-400 text-white font-bold text-lg tracking-wide hover:shadow-[0_0_30px_rgba(172,41,84,0.3)] transition-all relative overflow-hidden group rounded-xl"
                      >
                        <span className="relative z-10 flex items-center justify-center gap-3">
                          <Sparkles size={20} /> Запустить глубокий анализ
                        </span>
                        <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-500" />
                      </button>
                    </div>
                  )}
                  
                  {/* Error Display */}
                  {deepAnalysisError && (
                    <div className="mt-4 p-4 bg-red-900/30 border border-red-500/30 rounded-lg text-red-300 text-sm">
                      {deepAnalysisError}
                    </div>
                  )}
                  
                  {/* Analysis In Progress */}
                  {deepAnalysisActive && !deepAnalysisResults && (
                    <div className="border border-gold-500/30 bg-gold-500/5 p-8 rounded-xl">
                      {/* Progress Steps */}
                      <div className="mb-8">
                        <div className="flex justify-between mb-4">
                          {DEEP_ANALYSIS_STEPS.map((step, i) => (
                            <div key={step.key} className="flex flex-col items-center flex-1">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-500 ${
                                i < deepAnalysisStep ? 'bg-gold-500 text-black' :
                                i === deepAnalysisStep ? 'bg-gold-500/50 text-white animate-pulse' :
                                'bg-white/10 text-gray-500'
                              }`}>
                                {i < deepAnalysisStep ? '✓' : <step.icon size={14} />}
                              </div>
                              <span className={`text-xs mt-2 text-center hidden md:block ${
                                i <= deepAnalysisStep ? 'text-gold-400' : 'text-gray-600'
                              }`}>
                                {step.label}
                              </span>
                            </div>
                          ))}
                        </div>
                        <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                          <motion.div 
                            className="h-full bg-gradient-to-r from-gold-600 to-gold-400"
                            initial={{ width: 0 }}
                            animate={{ width: `${(deepAnalysisStep / DEEP_ANALYSIS_STEPS.length) * 100}%` }}
                            transition={{ duration: 0.5 }}
                          />
                        </div>
                      </div>
                      
                      <div className="text-center py-8">
                        <Loader2 className="w-10 h-10 text-gold-500 animate-spin mx-auto mb-6" />
                        <p className="text-gold-200 font-serif text-2xl animate-pulse">
                          {DEEP_ANALYSIS_STEPS[Math.min(deepAnalysisStep, DEEP_ANALYSIS_STEPS.length - 1)]?.label}...
                        </p>
                        <p className="text-gray-500 text-sm mt-2">
                          Выполняется многоэтапный анализ с использованием ИИ
                        </p>
                      </div>
                    </div>
                  )}
                  
                  {/* Analysis Complete - Show ONLY Summary */}
                  {deepAnalysisResults && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                    >
                      {/* Color Palette Moodboard */}
                      {deepAnalysisResults.color_features?.dominant_colors && (
                        <div className="mb-8">
                          <div className="flex items-center gap-3 mb-4">
                            <Palette className="w-5 h-5 text-gold-400" />
                            <span className="text-sm text-gray-400 uppercase tracking-wider">Цветовая палитра</span>
                          </div>
                          <div className="flex h-16 rounded-xl overflow-hidden shadow-lg border border-white/10">
                            {deepAnalysisResults.color_features.dominant_colors.map((color, i) => (
                              <div 
                                key={i}
                                className="flex-1 relative group cursor-pointer transition-all hover:flex-[1.5]"
                                style={{ backgroundColor: color.hex }}
                                title={`${color.name}: ${color.hex} (${(color.percentage * 100).toFixed(1)}%)`}
                              >
                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                                  <span className="text-white text-xs font-mono">{color.hex}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Unified Summary - THE MAIN CONTENT */}
                      {deepAnalysisResults.summary && (
                        <div className="prose prose-invert prose-lg max-w-none">
                          {/* Compact legend */}
                          <div className="flex flex-wrap items-center gap-4 mb-6 text-xs text-gray-500 not-prose">
                            <span>Нажмите на метку для пояснения:</span>
                            <span className="inline-flex items-center gap-1">
                              <span className="w-3 h-3 rounded bg-gradient-to-br from-blue-400 to-purple-500"></span> цвета
                            </span>
                            <span className="inline-flex items-center gap-1 text-purple-400">
                              <Brush size={10} /> техника
                            </span>
                            <span className="inline-flex items-center gap-1 text-blue-400">
                              <Layers size={10} /> композиция
                            </span>
                            <span className="inline-flex items-center gap-1 text-pink-400">
                              <Heart size={10} /> настроение
                            </span>
                            <span className="inline-flex items-center gap-1 text-amber-400">
                              <Clock size={10} /> эпоха
                            </span>
                            <span className="inline-flex items-center gap-1 text-green-400">
                              <User size={10} /> художник
                            </span>
                          </div>
                          
                          {/* Render summary with inline markers */}
                          <RichTextWithMarkers 
                            text={
                              typeof deepAnalysisResults.summary === 'object' 
                                ? (deepAnalysisResults.summary.raw_text || deepAnalysisResults.summary.cleaned_text)
                                : deepAnalysisResults.summary
                            }
                            markers={deepAnalysisResults.summary?.markers || []}
                          />
                        </div>
                      )}
                    </motion.div>
                  )}
                  </>
                  )}
                </div>
              </div>
              )}

              {/* Generation Studio - Hidden for guests, blocked during analysis */}
              {!isGuest && (
              <div className={`mb-24 bg-white/5 border border-white/10 rounded-2xl p-8 md:p-12 relative overflow-hidden ${result.vision_result?.is_photo ? 'opacity-60' : ''}`}>
                <div className="absolute top-0 right-0 p-4 opacity-10">
                  <Brush size={120} />
                </div>
                
                <BlockedOverlay show={(deepAnalysisActive || analysisPhase === 'streaming') && !result.vision_result?.is_photo} accentColor="purple" />
                
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-8">
                    <h3 className="font-serif text-3xl text-white">AI Переосмысление</h3>
                    <span className="text-xs text-purple-400 border border-purple-500/30 px-3 py-1 rounded-full bg-purple-500/10 font-bold tracking-wider">ГЕНЕРАЦИЯ</span>
                  </div>
                  
                  {/* Unavailable for photos */}
                  {result.vision_result?.is_photo ? (
                    <div className="text-center py-8">
                      <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gray-800 flex items-center justify-center">
                        <Brush size={32} className="text-gray-500" />
                      </div>
                      <p className="text-gray-400 mb-4 max-w-2xl mx-auto">
                        AI Переосмысление недоступно для фотографий
                      </p>
                      <p className="text-gray-500 text-sm max-w-xl mx-auto">
                        Генерация вариаций в стиле художника работает только с произведениями искусства.
                        Загрузите картину или рисунок для использования этой функции.
                      </p>
                    </div>
                  ) : (
                  <>
                  <p className="text-gray-400 mb-8 max-w-2xl">
                    Визуализируйте это произведение в разных контекстах или вариациях, используя нашу генеративную модель.
                  </p>
                  
                  {/* Input inside the card */}
                  <div className="flex gap-4 mb-8">
                    <input 
                      type="text" 
                      value={generationPrompt}
                      onChange={(e) => setGenerationPrompt(e.target.value)}
                      placeholder="Опишите вариацию (например, 'в штормовую погоду')"
                      className="flex-1 bg-white/5 border border-white/10 rounded-xl px-6 py-4 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none transition-colors"
                    />
                    <button 
                      onClick={handleGenerate}
                      disabled={generating}
                      className="px-8 py-4 bg-gradient-to-r from-purple-600 to-purple-400 text-white font-bold rounded-xl hover:shadow-[0_0_30px_rgba(168,85,247,0.3)] transition-all relative overflow-hidden group disabled:opacity-50 whitespace-nowrap"
                    >
                      <span className="relative z-10 flex items-center gap-2">
                        <Brush size={18} />
                        {generating ? 'Генерация...' : 'Создать'}
                      </span>
                      <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-500" />
                    </button>
                  </div>

                  {generationError && (
                    <div className="mb-8 p-4 bg-red-900/30 border border-red-500/30 rounded-lg text-red-300 text-sm">
                      {generationError}
                    </div>
                  )}

                  {generatedImages?.images && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                      {generatedImages.images.map((img, i) => (
                        <div key={i} className="aspect-square bg-white/5 relative group overflow-hidden rounded-xl border border-white/10">
                          <img src={img.url} alt="" className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" />
                          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-4">
                            <button 
                              onClick={() => handleDownload(img.url, `generated-${i}.png`)}
                              className="p-4 bg-white text-black rounded-full hover:scale-110 transition-transform shadow-xl"
                              title="Скачать"
                            >
                              <Download size={24} />
                            </button>
                            <button 
                              onClick={() => window.open(img.url, '_blank')}
                              className="p-4 bg-white/10 text-white backdrop-blur rounded-full hover:bg-white hover:text-black transition-all shadow-xl"
                              title="Открыть оригинал"
                            >
                              <Maximize2 size={24} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  </>
                  )}
                </div>
              </div>
              )}

              {/* Share Analysis Section - Hidden for guests, blocked during analysis */}
              {!isGuest && (
              <div className="mb-24 bg-white/5 border border-white/10 rounded-2xl p-8 md:p-12 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10">
                  <Share2 size={120} />
                </div>
                
                <BlockedOverlay show={deepAnalysisActive || analysisPhase === 'streaming'} accentColor="emerald" />
                
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-8">
                    <h3 className="font-serif text-3xl text-white">Поделиться анализом</h3>
                    <span className="text-xs text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded-full bg-emerald-500/10 font-bold tracking-wider">
                      {collabSession ? 'АКТИВНО' : 'СОВМЕСТНЫЙ ДОСТУП'}
                    </span>
                  </div>
                  
                  {/* Before session created */}
                  {!collabSession && (
                    <div className="text-center py-8">
                      <p className="text-gray-400 mb-8 max-w-2xl mx-auto">
                        Создайте ссылку для совместного обсуждения этого анализа. 
                        Гости смогут задавать вопросы об атрибуции и получать ответы от AI.
                      </p>
                      
                      {collabError && (
                        <div className="mb-6 p-4 bg-red-900/30 border border-red-500/30 rounded-lg text-red-300 text-sm max-w-md mx-auto">
                          {collabError}
                        </div>
                      )}
                      
                      <button 
                        onClick={handleCreateCollabSession}
                        disabled={collabLoading}
                        className="px-12 py-6 bg-gradient-to-r from-emerald-600 to-emerald-400 text-white font-bold text-lg tracking-wide hover:shadow-[0_0_30px_rgba(16,185,129,0.3)] transition-all relative overflow-hidden group rounded-xl disabled:opacity-50"
                      >
                        <span className="relative z-10 flex items-center justify-center gap-3">
                          {collabLoading ? (
                            <Loader2 size={20} className="animate-spin" />
                          ) : (
                            <Link2 size={20} />
                          )}
                          {collabLoading ? 'Создание...' : 'Создать ссылку'}
                        </span>
                        <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-500" />
                      </button>
                    </div>
                  )}
                  
                  {/* After session created - show QR and link */}
                  {collabSession && (
                    <div className="flex flex-col items-center">
                      {/* QR Code */}
                      <div className="p-4 bg-white rounded-xl mb-6">
                        <QRCodeSVG 
                          value={`${window.location.origin}/collab/${collabSession.id}`}
                          size={180}
                          level="M"
                          includeMargin={false}
                        />
                      </div>
                      
                      {/* Copy link button */}
                      <button
                        onClick={handleCopyCollabLink}
                        className={`px-6 py-3 rounded-xl transition-all flex items-center gap-2 mb-6 ${
                          linkCopied 
                            ? 'bg-emerald-500/20 border border-emerald-500/30 text-emerald-400' 
                            : 'bg-white/10 hover:bg-white/20 border border-white/20 text-gray-300'
                        }`}
                      >
                        {linkCopied ? (
                          <>
                            <Check size={18} />
                            <span>Ссылка скопирована!</span>
                          </>
                        ) : (
                          <>
                            <Copy size={18} />
                            <span>Скопировать ссылку</span>
                          </>
                        )}
                      </button>
                      
                      {/* Status badges */}
                      <div className="flex flex-wrap items-center justify-center gap-3 mb-6">
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-emerald-400 text-sm">
                          <Users size={14} />
                          <span>{collabViewers} активных</span>
                        </div>
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded-full text-amber-400 text-sm">
                          <Clock size={14} />
                          <span className="font-mono">{formatCollabTime(collabRemainingTime)}</span>
                        </div>
                        {/* Deep analysis indicator */}
                        {deepAnalysisResults && (
                          <div 
                            className="flex items-center gap-2 px-3 py-1.5 bg-[#827DBD]/15 border border-[#827DBD]/30 rounded-full cursor-help group relative"
                            title="Контекст обогащён результатами глубокого исследования"
                          >
                            <Brain size={14} className="text-[#827DBD]" />
                            <span className="text-[#827DBD] text-xs font-medium">Глубокое исследование</span>
                          </div>
                        )}
                      </div>
                      
                      {/* Close button */}
                      <button
                        onClick={handleCloseCollabSession}
                        className="text-red-400 hover:text-red-300 text-sm flex items-center gap-1.5 transition-colors"
                      >
                        <X size={16} />
                        Закрыть доступ
                      </button>
                    </div>
                  )}
                </div>
              </div>
              )}

            </div>
            
            {/* Footer */}
            <div className="border-t border-white/10 py-12 text-center text-gray-600 text-sm uppercase tracking-widest">
              Heritage Frame &copy; 2025
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  )
}

export default Analyze
