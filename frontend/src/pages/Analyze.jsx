import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { analysisAPI, historyAPI } from '../api'
import { 
  Upload, 
  X, 
  Search, 
  Zap, 
  LogOut,
  LogIn,
  Palette,
  Brush,
  BookOpen,
  Sparkles,
  Loader2,
  Download,
  History,
  ChevronLeft,
  ChevronRight,
  Moon,
  Sun,
  Menu,
  Maximize2,
  PanelRightClose,
  PanelRightOpen,
  Image as ImageIcon
} from 'lucide-react'

function Analyze() {
  const navigate = useNavigate()
  const { logout, user } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const isGuest = user?.isGuest === true
  
  const handleLogin = () => {
    logout()
    navigate('/login')
  }
  
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef(null)
  
  // UI State
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [showSidebar, setShowSidebar] = useState(false)
  const [showPanel, setShowPanel] = useState(true)
  
  // Generation state
  const [generating, setGenerating] = useState(false)
  const [generationPrompt, setGenerationPrompt] = useState('')
  const [generatedImages, setGeneratedImages] = useState(null)
  const [generationError, setGenerationError] = useState('')
  const [generationStep, setGenerationStep] = useState(0)

  useEffect(() => {
    let interval
    if (generating) {
      setGenerationStep(0)
      const steps = [
        "Анализ композиции...",
        "Извлечение стиля...",
        "Синтез палитры...",
        "Генерация вариаций...",
        "Финальная обработка..."
      ]
      interval = setInterval(() => {
        setGenerationStep(prev => (prev + 1) % steps.length)
      }, 1500)
    }
    return () => clearInterval(interval)
  }, [generating])

  // Load history from server
  useEffect(() => {
    const loadHistory = async () => {
      try {
        setHistoryLoading(true)
        const response = await historyAPI.getAll()
        setHistory(response.data.items || [])
      } catch (err) {
        console.error('Failed to load history:', err)
        setHistory([])
      } finally {
        setHistoryLoading(false)
      }
    }
    loadHistory()
  }, [])

  const loadFromHistory = (item) => {
    setFile(null)
    setPreview(item.image_url)
    setResult(item.analysis_result)
    setGeneratedImages(null)
    setGenerationPrompt('')
    setError('')
    setShowPanel(true)
    setShowSidebar(false)
  }

  const handleFileSelect = (selectedFile) => {
    if (!selectedFile) return

    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp']
    if (!validTypes.includes(selectedFile.type)) {
      setError('Пожалуйста, выберите изображение (JPEG, PNG, WebP, BMP)')
      return
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('Размер файла должен быть меньше 10MB')
      return
    }

    setFile(selectedFile)
    setPreview(URL.createObjectURL(selectedFile))
    setError('')
    setResult(null)
    setGeneratedImages(null)
    setShowPanel(true)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const droppedFile = e.dataTransfer.files[0]
    handleFileSelect(droppedFile)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragging(true)
  }

  const handleDragLeave = () => {
    setDragging(false)
  }

  const handleAnalyze = async () => {
    if (!file) return

    setLoading(true)
    setError('')
    
    try {
      const response = await analysisAPI.analyze(file)
      setResult(response.data)
      // Backend auto-saves to history, refresh the list
      const historyResponse = await historyAPI.getAll()
      setHistory(historyResponse.data.items || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка анализа. Попробуйте снова.')
    } finally {
      setLoading(false)
    }
  }

  const deleteFromHistory = async (id, e) => {
    e.stopPropagation()
    try {
      await historyAPI.delete(id)
      setHistory(prev => prev.filter(item => item.id !== id))
    } catch (err) {
      console.error('Failed to delete history item:', err)
    }
  }

  const handleReset = () => {
    setFile(null)
    setPreview(null)
    setResult(null)
    setError('')
    setGeneratedImages(null)
    setGenerationPrompt('')
    setGenerationError('')
  }

  const handleGenerate = async () => {
    if (!result || !result.top_artists.length) return
    
    setGenerating(true)
    setGenerationError('')
    setGeneratedImages(null)
    
    try {
      const topArtist = result.top_artists[0]
      const topStyle = result.top_styles?.[0]
      const topGenre = result.top_genres?.[0]
      
      const response = await analysisAPI.generate({
        artist_slug: topArtist.artist_slug,
        style_name: topStyle?.name || null,
        genre_name: topGenre?.name || null,
        user_prompt: generationPrompt || null,
        count: 4
      })
      
      setGeneratedImages(response.data)
    } catch (err) {
      setGenerationError(err.response?.data?.detail || 'Ошибка генерации. Попробуйте снова.')
    } finally {
      setGenerating(false)
    }
  }

  const formatArtistName = (slug) => {
    return slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }

  const formatName = (name) => {
    return name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }

  return (
    <div className="h-screen w-full bg-gray-950 text-white overflow-hidden flex font-sans selection:bg-purple-500/30">
      
      {/* Sidebar (History) - Floating Drawer - Hidden for guests */}
      {!isGuest && (
        <div 
          className={`
            fixed inset-y-0 left-0 z-50 w-80 bg-gray-900/95 backdrop-blur-xl border-r border-white/10 transform transition-transform duration-300 ease-in-out shadow-2xl
            ${showSidebar ? 'translate-x-0' : '-translate-x-full'}
          `}
        >
        <div className="h-16 flex items-center justify-between px-4 border-b border-white/10">
          <span className="font-bold text-lg tracking-tight text-white/90">История</span>
          <button 
            onClick={() => setShowSidebar(false)}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <ChevronLeft size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 custom-scrollbar h-[calc(100%-8rem)]">
          {historyLoading ? (
            <div className="text-center py-12 text-gray-500 text-sm">
              <Loader2 size={24} className="mx-auto mb-3 animate-spin opacity-50" />
              <p>Загрузка...</p>
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-12 text-gray-500 text-sm">
              <History size={24} className="mx-auto mb-3 opacity-30" />
              <p>Нет сохраненных работ</p>
            </div>
          ) : (
            <div className="space-y-2">
              {history.map((item) => (
                <div
                  key={item.id}
                  className="w-full flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 transition-all group text-left border border-transparent hover:border-white/10 relative"
                >
                  <button
                    onClick={() => loadFromHistory(item)}
                    className="flex items-center gap-3 flex-1 min-w-0"
                  >
                    <div className="w-12 h-12 rounded-lg overflow-hidden bg-gray-800 flex-shrink-0 border border-white/10">
                      <img src={item.image_url} alt="" className="w-full h-full object-cover" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate text-gray-200 group-hover:text-white transition-colors">
                        {formatArtistName(item.top_artist_slug)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date(item.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </button>
                  <button
                    onClick={(e) => deleteFromHistory(item.id, e)}
                    className="p-1.5 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 hover:text-red-400 text-gray-500 rounded-lg transition-all"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-white/10 bg-gray-900/95">
          <button 
            onClick={logout}
            className="flex items-center gap-3 w-full p-3 rounded-xl hover:bg-red-500/10 text-gray-400 hover:text-red-400 transition-colors"
          >
            <LogOut size={20} />
            <span className="font-medium">Выйти</span>
          </button>
        </div>
      </div>
      )}

      {/* Main Workspace */}
      <div className="flex-1 relative h-full flex flex-col min-w-0">
        
        {/* Top Bar */}
        <header className="absolute top-0 left-0 right-0 h-16 z-40 flex items-center justify-between px-6 pointer-events-none">
          <div className="flex items-center gap-4 pointer-events-auto">
            {!isGuest && (
              <button 
                onClick={() => setShowSidebar(true)}
                className="group flex items-center gap-2 px-3 py-2 bg-black/50 backdrop-blur-md border border-white/10 rounded-lg text-gray-300 hover:text-white hover:bg-white/10 transition-all"
              >
                <History size={18} />
                <span className="text-sm font-medium max-w-0 overflow-hidden group-hover:max-w-xs transition-all duration-300 ease-in-out whitespace-nowrap">История</span>
              </button>
            )}
            
            <div className="flex items-center gap-3 px-4 py-2 rounded-full">
              <img src="/images/logo.png" alt="Logo" className="w-8 h-8 object-contain" />
              <span className="font-bold text-sm tracking-tight">Heritage Frame</span>
            </div>
          </div>

          <div className="flex items-center gap-3 pointer-events-auto">
            {preview && (
              <button 
                onClick={() => setShowPanel(!showPanel)}
                className={`p-2.5 rounded-full backdrop-blur-md border transition-all ${showPanel ? 'bg-white text-black border-white' : 'bg-black/50 border-white/10 text-white'}`}
              >
                {showPanel ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
              </button>
            )}
            
            {isGuest && (
              <button 
                onClick={handleLogin}
                className="group flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 backdrop-blur-md border border-purple-500/50 rounded-lg text-white transition-all shadow-lg shadow-purple-500/20"
              >
                <LogIn size={18} />
                <span className="text-sm font-medium">Войти</span>
              </button>
            )}
          </div>
        </header>

        {/* Canvas Area */}
        <div className="relative flex-1 w-full h-full overflow-hidden bg-[#0a0a0a]">
          {/* Ambient Background */}
          {preview && (
            <div className="absolute inset-0 z-0 overflow-hidden">
              <div 
                className="absolute inset-0 bg-cover bg-center blur-3xl opacity-20 scale-110 transition-all duration-1000"
                style={{ backgroundImage: `url(${preview})` }}
              />
              <div className="absolute inset-0 bg-black/40" />
            </div>
          )}

          {/* Main Content */}
          <div className="absolute inset-0 z-10 flex items-center justify-center p-4 lg:p-12">
            {!preview ? (
              /* Empty State / Upload */
              <div className="w-full max-w-2xl animate-fade-in">
                <div 
                  className={`
                    relative group w-full aspect-[16/9] rounded-3xl border-2 border-dashed transition-all duration-500 ease-out
                    flex flex-col items-center justify-center cursor-pointer overflow-hidden bg-white/5 backdrop-blur-sm
                    ${dragging 
                      ? 'border-purple-500 bg-purple-500/10 scale-105 shadow-[0_0_50px_rgba(168,85,247,0.2)]' 
                      : 'border-white/10 hover:border-purple-500/50 hover:bg-white/10'
                    }
                  `}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={(e) => handleFileSelect(e.target.files[0])}
                    accept="image/jpeg,image/png,image/webp,image/bmp"
                    className="hidden"
                  />
                  
                  <div className="relative z-10 flex flex-col items-center p-8 text-center">
                    <div className="w-24 h-24 bg-gradient-to-br from-gray-800 to-black rounded-3xl shadow-2xl border border-white/10 flex items-center justify-center mb-8 group-hover:scale-110 transition-transform duration-500">
                      <Upload className="w-10 h-10 text-purple-400" />
                    </div>
                    <h2 className="text-3xl font-bold text-white mb-4">Загрузите изображение</h2>
                    <p className="text-gray-400 max-w-md mb-8 text-lg">
                      Перетащите файл сюда или нажмите для выбора. <br/>
                      <span className="text-sm opacity-60">Поддерживаются JPEG, PNG, WEBP до 10MB</span>
                    </p>
                  </div>
                </div>
                {error && (
                  <div className="mt-6 p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl flex items-center gap-3 animate-slide-up">
                    <X size={20} />
                    {error}
                  </div>
                )}
              </div>
            ) : (
              /* Image Preview */
              <div className={`relative w-full h-full flex items-center justify-center transition-all duration-500 ${showPanel ? 'lg:pr-[400px]' : ''}`}>
                <div className="relative max-w-full max-h-full shadow-2xl rounded-lg group flex items-center justify-center min-w-[320px] min-h-[320px]">
                  <img 
                    src={preview} 
                    alt="Analysis target" 
                    className="max-w-full max-h-[85vh] object-contain shadow-2xl"
                  />
                  
                  {/* Scanning Effect */}
                  {loading && (
                    <div className="absolute inset-0 z-20 pointer-events-none overflow-hidden rounded-lg">
                      <div className="absolute left-0 right-0 h-1 bg-purple-500 shadow-[0_0_20px_rgba(168,85,247,0.8)] animate-scan" />
                      <div className="absolute inset-0 bg-purple-500/10 animate-pulse" />
                    </div>
                  )}

                  {/* Reset Button */}
                  <button 
                    onClick={handleReset}
                    className="absolute top-4 right-4 p-2 bg-black/60 backdrop-blur-md border border-white/20 rounded-lg text-white opacity-0 group-hover:opacity-100 transition-all hover:bg-red-500/80 hover:border-red-500 z-30"
                  >
                    <X size={20} />
                  </button>

                  {/* Analyze Button (Floating - Centered on Image) */}
                  {!result && !loading && (
                    <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-30">
                      <button
                        onClick={handleAnalyze}
                        className="group relative px-8 py-4 bg-white text-black rounded-full font-bold shadow-[0_0_40px_rgba(255,255,255,0.3)] hover:shadow-[0_0_60px_rgba(255,255,255,0.5)] hover:-translate-y-1 transition-all duration-300 overflow-hidden whitespace-nowrap"
                      >
                        <span className="relative z-10 flex items-center gap-2 text-lg">
                          <Sparkles size={20} className="text-purple-600" />
                          Анализировать
                        </span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Floating Right Panel */}
          <div 
            className={`
              absolute top-20 bottom-4 right-4 w-[400px] bg-black/80 backdrop-blur-2xl border border-white/10 rounded-3xl shadow-2xl z-40 flex flex-col overflow-hidden transition-transform duration-500 cubic-bezier(0.4, 0, 0.2, 1)
              ${showPanel && preview ? 'translate-x-0' : 'translate-x-[120%]'}
            `}
          >
            {!result ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-gray-400">
                <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4 animate-pulse">
                  <Search size={32} className="opacity-50" />
                </div>
                <p>Ожидание анализа...</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto custom-scrollbar">
                {/* Header Image (Blurred crop) */}
                <div className="relative h-48 overflow-hidden">
                  <div 
                    className="absolute inset-0 bg-cover bg-center blur-sm opacity-50"
                    style={{ backgroundImage: `url(${preview})` }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/90" />
                  <div className="absolute bottom-0 left-0 right-0 p-6">
                    <div className="flex items-center gap-2 text-purple-400 font-medium mb-1 text-xs uppercase tracking-wider">
                      <Brush size={12} />
                      Вероятный автор
                    </div>
                    <h2 className="text-3xl font-bold text-white leading-tight">
                      {formatArtistName(result.top_artists[0].artist_slug)}
                    </h2>
                  </div>
                </div>

                <div className="p-6 space-y-6">
                  {/* Probability Bar */}
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-gray-400">Уверенность</span>
                      <span className="text-white font-mono">{(result.top_artists[0].probability * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full"
                        style={{ width: `${result.top_artists[0].probability * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Other possible artists */}
                  {result.top_artists.length > 1 && (
                    <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                      <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
                        Другие возможные авторы
                      </h4>
                      <div className="space-y-2">
                        {result.top_artists.slice(1, 3).map((artist, index) => (
                          <div key={index} className="flex items-center justify-between">
                            <span className="text-sm text-gray-300">
                              {formatArtistName(artist.artist_slug)}
                            </span>
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-1 bg-white/10 rounded-full overflow-hidden">
                                <div 
                                  className="h-full bg-gradient-to-r from-indigo-500/50 to-purple-500/50 rounded-full"
                                  style={{ width: `${artist.probability * 100}%` }}
                                />
                              </div>
                              <span className="text-xs text-gray-500 font-mono w-12 text-right">
                                {(artist.probability * 100).toFixed(1)}%
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Tags */}
                  <div className="flex flex-wrap gap-2">
                    {result.top_styles?.[0] && (
                      <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs font-medium text-gray-300 flex items-center gap-2">
                        <Palette size={12} />
                        {formatName(result.top_styles[0].name)}
                      </span>
                    )}
                    {result.top_genres?.[0] && (
                      <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs font-medium text-gray-300 flex items-center gap-2">
                        <BookOpen size={12} />
                        {formatName(result.top_genres[0].name)}
                      </span>
                    )}
                  </div>

                  {/* Description */}
                  <div className="bg-white/5 rounded-2xl p-5 border border-white/5">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <BookOpen size={16} className="text-orange-400" />
                        Анализ стиля
                      </h3>
                      {result.explanation.source === 'stub' && (
                        <span className="text-[10px] px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded-full border border-yellow-500/30">
                          Базовый анализ
                        </span>
                      )}
                      {result.explanation.source !== 'stub' && (
                        <span className="text-[10px] px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full border border-green-500/30">
                          AI анализ
                        </span>
                      )}
                    </div>
                    <div className="prose prose-sm prose-invert max-w-none text-gray-300 leading-relaxed
                      prose-headings:text-white prose-headings:font-bold prose-headings:mt-4 prose-headings:mb-2
                      prose-h2:text-base prose-h2:border-b prose-h2:border-white/10 prose-h2:pb-2
                      prose-h3:text-sm prose-h3:text-purple-300
                      prose-p:text-gray-400 prose-p:my-2
                      prose-strong:text-white prose-strong:font-semibold
                      prose-ul:my-2 prose-li:my-0.5 prose-li:text-gray-400
                      prose-hr:border-white/10">
                      <ReactMarkdown>
                        {result.explanation.text}
                      </ReactMarkdown>
                    </div>
                    {result.explanation.source === 'stub' && (
                      <p className="mt-3 text-[11px] text-gray-600 italic">
                        💡 Для расширенного AI-анализа настройте LLM провайдер в .env файле
                      </p>
                    )}
                  </div>

                  {/* Generation Studio */}
                  <div className="pt-6 border-t border-white/10">
                    <div className="flex items-center gap-2 mb-4">
                      <Zap size={18} className="text-yellow-400" />
                      <h3 className="font-bold text-white">AI Ремикс</h3>
                    </div>
                    
                    <div className="space-y-3">
                      {!generating ? (
                        <>
                          <textarea
                            value={generationPrompt}
                            onChange={(e) => setGenerationPrompt(e.target.value)}
                            placeholder={`Создать вариацию в стиле ${formatArtistName(result.top_artists[0].artist_slug)}...`}
                            className="w-full bg-black/30 border border-white/10 rounded-xl p-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-purple-500 transition-all resize-none h-20"
                          />
                          
                          <button
                            onClick={handleGenerate}
                            className="w-full py-3 bg-white text-black rounded-xl font-bold hover:bg-gray-200 transition-colors flex items-center justify-center gap-2"
                          >
                            <Sparkles size={16} />
                            Генерировать
                          </button>
                        </>
                      ) : (
                        <div className="relative h-48 rounded-xl overflow-hidden border border-white/10 bg-black/50">
                          {/* Alchemical Process Animation */}
                          <div className="absolute inset-0 bg-gradient-to-r from-purple-900/20 via-indigo-900/20 to-purple-900/20 animate-shimmer-fast" style={{ backgroundSize: '200% 100%' }} />
                          
                          <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center">
                            <div className="relative w-16 h-16 mb-4">
                              <div className="absolute inset-0 rounded-full border-2 border-purple-500/30 animate-ping" />
                              <div className="absolute inset-0 rounded-full border-2 border-t-purple-500 animate-spin" />
                              <div className="absolute inset-2 rounded-full bg-purple-500/20 backdrop-blur-sm flex items-center justify-center">
                                <Sparkles size={20} className="text-purple-400 animate-pulse" />
                              </div>
                            </div>
                            
                            <div className="space-y-1">
                              <p className="text-sm font-medium text-white animate-pulse">
                                {[
                                  "Анализ композиции...",
                                  "Извлечение стиля...",
                                  "Синтез палитры...",
                                  "Генерация вариаций...",
                                  "Финальная обработка..."
                                ][generationStep]}
                              </p>
                              <p className="text-xs text-gray-500">AI трансмутация</p>
                            </div>
                          </div>

                          {/* Digital Noise Overlay */}
                          <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 200 200\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noiseFilter\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.65\' numOctaves=\'3\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noiseFilter)\'/%3E%3C/svg%3E")' }} />
                        </div>
                      )}
                    </div>

                    {/* Generated Images Grid */}
                    {generatedImages && !generating && (
                      <div className="mt-6 space-y-3">
                        {/* Show prompt used */}
                        {generatedImages.prompt && (
                          <div className="p-3 bg-purple-500/10 border border-purple-500/20 rounded-xl">
                            <p className="text-[10px] text-purple-400 uppercase tracking-wider mb-1 font-medium">Использованный промпт</p>
                            <p className="text-xs text-gray-300 italic leading-relaxed">"{generatedImages.prompt}"</p>
                          </div>
                        )}
                        <div className="grid grid-cols-2 gap-2">
                          {generatedImages.images.map((img, index) => (
                            <div 
                              key={index} 
                              className="group relative aspect-square rounded-lg overflow-hidden bg-gray-800 animate-blur-in"
                              style={{ animationDelay: `${index * 150}ms` }}
                            >
                              <img src={img.url} alt="" className="w-full h-full object-cover" />
                              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                <button className="p-2 bg-white/20 backdrop-blur rounded-full text-white hover:bg-white/40">
                                  <Download size={16} />
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {generationError && (
                      <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0">
                            <X size={16} className="text-red-400" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-red-400 mb-1">Ошибка генерации</p>
                            <p className="text-xs text-gray-400">{generationError}</p>
                            <p className="text-[11px] text-gray-600 mt-2">Убедитесь, что ComfyUI запущен и доступен</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}

export default Analyze
