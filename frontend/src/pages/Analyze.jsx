import { useState, useRef, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { analysisAPI, historyAPI, deepAnalysisAPI } from '../api'
import { motion, AnimatePresence, useScroll, useTransform } from 'framer-motion'
import { 
  Upload, X, Search, Zap, LogOut, LogIn, Palette, Brush, BookOpen, 
  Sparkles, Loader2, Download, History, ChevronLeft, ChevronRight, 
  Maximize2, PanelRightClose, PanelRightOpen, Image as ImageIcon,
  Share2, Info, Layers, Eye, Menu, Clock, Sun, Compass, Heart, User
} from 'lucide-react'

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

// Inline marker component for rendering citation badges in text
const InlineMarker = ({ type, value, label, icon }) => {
  const IconComponent = MARKER_ICONS[icon] || Info
  
  // Color marker with swatch
  if (type === 'color' && value.startsWith('#')) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 mx-0.5 bg-white/10 rounded-full text-sm border border-white/20 hover:border-gold-400/50 transition-colors cursor-default group">
        <span 
          className="w-3 h-3 rounded-full border border-white/30 shadow-sm" 
          style={{ backgroundColor: value }}
        />
        <span className="text-gray-200 group-hover:text-white transition-colors">{label}</span>
      </span>
    )
  }
  
  // Style-based marker colors
  const markerStyles = {
    technique: 'bg-purple-500/20 border-purple-500/30 text-purple-200 hover:border-purple-400',
    composition: 'bg-blue-500/20 border-blue-500/30 text-blue-200 hover:border-blue-400',
    mood: 'bg-pink-500/20 border-pink-500/30 text-pink-200 hover:border-pink-400',
    era: 'bg-amber-500/20 border-amber-500/30 text-amber-200 hover:border-amber-400',
    artist: 'bg-green-500/20 border-green-500/30 text-green-200 hover:border-green-400',
  }
  
  const style = markerStyles[type] || 'bg-white/10 border-white/20 text-gray-200'
  
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 mx-0.5 rounded-full text-sm border transition-colors cursor-default ${style}`}>
      <IconComponent size={12} className="opacity-70" />
      <span>{label}</span>
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
        return <InlineMarker key={i} type={part.markerType} value={part.value} label={part.label} icon={getMarkerIcon(part.markerType)} />
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
    setResult(item.analysis_result)
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
    // Reset deep analysis state
    setDeepAnalysisActive(false)
    setDeepAnalysisStep(0)
    setDeepAnalysisResults(null)
    setDeepAnalysisError('')
  }

  const handleAnalyze = async () => {
    if (!file) return
    setLoading(true)
    try {
      const response = await analysisAPI.analyze(file)
      setResult(response.data)
      if (!isGuest) loadHistory()
      
      // Smooth scroll to results after a short delay
      setTimeout(() => {
        window.scrollTo({ top: window.innerHeight * 0.8, behavior: 'smooth' })
      }, 100)
    } catch (err) {
      setError('Ошибка анализа. Попробуйте снова.')
    } finally {
      setLoading(false)
    }
  }

  const handleDeepAnalysis = async () => {
    if (!result?.image_path) return
    
    setDeepAnalysisActive(true)
    setDeepAnalysisStep(0)
    setDeepAnalysisError('')
    setDeepAnalysisResults(null)
    
    try {
      // Simulate step progression for UX (actual API does all at once)
      const stepInterval = setInterval(() => {
        setDeepAnalysisStep(prev => Math.min(prev + 1, DEEP_ANALYSIS_STEPS.length - 1))
      }, 2000)
      
      const response = await deepAnalysisAPI.analyzeFull(result.image_path)
      
      clearInterval(stepInterval)
      setDeepAnalysisStep(DEEP_ANALYSIS_STEPS.length)
      setDeepAnalysisResults(response.data)
      
    } catch (err) {
      console.error('Deep analysis failed:', err)
      setDeepAnalysisError(err.response?.data?.detail || 'Ошибка глубокого анализа')
      setDeepAnalysisActive(false)
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
    <div className="min-h-screen w-full bg-charcoal-950 text-alabaster-100 font-sans selection:bg-gold-500/30 relative overflow-x-hidden">
      <div className="fixed inset-0 bg-grain pointer-events-none z-50 opacity-50" />
      
      {/* Navigation Bar */}
      <nav className="fixed top-0 left-0 right-0 h-20 z-40 flex items-center justify-between px-8 bg-gradient-to-b from-black/80 to-transparent pointer-events-none">
        <div className="flex items-center gap-6 pointer-events-auto">
          <div className="flex items-center gap-3">
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
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_10%,rgba(5,5,5,0.9)_100%)]" />
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
                        Анализ...
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
                        className="px-8 py-3 bg-white text-black font-serif font-medium tracking-wide hover:bg-gray-200 transition-colors shadow-lg whitespace-nowrap"
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
            className="relative z-20 bg-charcoal-950 min-h-screen border-t border-white/10 shadow-[0_-50px_100px_rgba(0,0,0,0.5)]"
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
                  <span className="px-4 py-1.5 border border-gold-500/30 rounded-full text-gold-500 text-xs font-bold tracking-[0.2em] uppercase bg-gold-500/5">
                    Отчет об атрибуции
                  </span>
                </motion.div>
                
                <motion.h1 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.1 }}
                  className="font-serif text-6xl md:text-7xl text-white mb-8 leading-tight"
                >
                  {formatName(result.top_artists[0].artist_slug)}
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
                  <span className="block text-4xl font-serif text-white mb-2">{(result.top_artists[0].probability * 100).toFixed(1)}%</span>
                  <span className="text-xs text-gray-500 uppercase tracking-wider">Уверенность</span>
                </div>
                <div className="text-center border-r border-white/10">
                  <span className="block text-4xl font-serif text-white mb-2">#{result.top_artists[0].index}</span>
                  <span className="text-xs text-gray-500 uppercase tracking-wider">Ранг в базе</span>
                </div>
                <div className="text-center">
                  <span className="block text-4xl font-serif text-white mb-2">AI</span>
                  <span className="text-xs text-gray-500 uppercase tracking-wider">AI Модель</span>
                </div>
              </div>

              {/* Article Content */}
              <div className="prose prose-invert prose-lg max-w-none font-serif leading-relaxed text-gray-300 mb-24">
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

              {/* Deep Analysis Section */}
              <div className="mb-24 bg-white/5 border border-white/10 rounded-2xl p-8 md:p-12 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10">
                  <Sparkles size={120} />
                </div>
                
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-8">
                    <h3 className="font-serif text-3xl text-white">Глубокий анализ</h3>
                    <span className="text-xs text-gold-500 border border-gold-500/30 px-3 py-1 rounded-full bg-gold-500/10 font-bold tracking-wider">AI PRO SUITE</span>
                  </div>
                  
                  {/* Launch Button - show when no analysis running */}
                  {!deepAnalysisActive && !deepAnalysisResults && (
                    <div className="text-center py-8">
                      <p className="text-gray-400 mb-8 max-w-2xl mx-auto">
                        Получите развёрнутое искусствоведческое исследование с анализом цвета, композиции, 
                        техники и исторического контекста — всё в одном связном тексте музейного качества.
                      </p>
                      <button 
                        onClick={handleDeepAnalysis}
                        className="px-12 py-6 bg-gradient-to-r from-gold-600 to-gold-400 text-black font-bold text-lg tracking-wide hover:shadow-[0_0_30px_rgba(212,175,55,0.3)] transition-all relative overflow-hidden group rounded-xl"
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
                      {/* Reset Button */}
                      <div className="flex justify-end mb-6">
                        <button 
                          onClick={resetDeepAnalysis}
                          className="text-sm text-gray-400 hover:text-white flex items-center gap-2"
                        >
                          <X size={16} /> Закрыть
                        </button>
                      </div>
                      
                      {/* Color Palette Preview - compact visualization */}
                      {deepAnalysisResults.color_features?.dominant_colors && (
                        <div className="flex h-3 w-full rounded-full overflow-hidden shadow-lg mb-8">
                          {deepAnalysisResults.color_features.dominant_colors.slice(0, 7).map((c, i) => (
                            <div 
                              key={i} 
                              className="flex-1 first:rounded-l-full last:rounded-r-full" 
                              style={{ backgroundColor: c.hex }}
                              title={`${c.hex} (${(c.percentage * 100).toFixed(0)}%)`}
                            />
                          ))}
                        </div>
                      )}
                      
                      {/* Unified Summary - THE MAIN CONTENT */}
                      {deepAnalysisResults.summary && (
                        <div className="prose prose-invert prose-lg max-w-none">
                          {/* Legend for inline markers */}
                          <div className="flex flex-wrap gap-3 mb-8 p-4 bg-black/20 rounded-lg border border-white/5 not-prose">
                            <span className="text-xs text-gray-500">Интерактивные метки:</span>
                            <span className="inline-flex items-center gap-1.5 text-xs text-gray-400">
                              <span className="w-3 h-3 rounded-full bg-gradient-to-br from-pink-400 to-purple-500"></span> Цвет
                            </span>
                            <span className="inline-flex items-center gap-1.5 text-xs text-purple-400">
                              <Brush size={12} /> Техника
                            </span>
                            <span className="inline-flex items-center gap-1.5 text-xs text-blue-400">
                              <Layers size={12} /> Композиция
                            </span>
                            <span className="inline-flex items-center gap-1.5 text-xs text-pink-400">
                              <Heart size={12} /> Настроение
                            </span>
                            <span className="inline-flex items-center gap-1.5 text-xs text-amber-400">
                              <Clock size={12} /> Эпоха
                            </span>
                            <span className="inline-flex items-center gap-1.5 text-xs text-green-400">
                              <User size={12} /> Художник
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
                </div>
              </div>

              {/* Generation Studio */}
              <div className="border-t border-white/10 pt-24">
                <h3 className="font-serif text-4xl text-white mb-8 text-center">AI Переосмысление</h3>
                <p className="text-center text-gray-400 mb-12 max-w-2xl mx-auto">
                  Визуализируйте это произведение в разных контекстах или вариациях, используя нашу генеративную модель.
                </p>
                
                <div className="flex gap-4 mb-12 max-w-2xl mx-auto">
                  <input 
                    type="text" 
                    value={generationPrompt}
                    onChange={(e) => setGenerationPrompt(e.target.value)}
                    placeholder="Опишите вариацию (например, 'в штормовую погоду')"
                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-6 py-4 text-white placeholder-gray-500 focus:border-gold-500 focus:outline-none transition-colors"
                  />
                  <button 
                    onClick={handleGenerate}
                    disabled={generating}
                    className="px-8 py-4 bg-white text-black font-bold rounded-lg hover:bg-gray-200 transition-colors text-sm uppercase tracking-wider disabled:opacity-50 whitespace-nowrap"
                  >
                    {generating ? 'Генерация...' : 'Создать'}
                  </button>
                </div>

                {generationError && (
                  <div className="mb-8 text-red-400 text-center bg-red-500/10 p-4 rounded-lg border border-red-500/20">{generationError}</div>
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
              </div>

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
