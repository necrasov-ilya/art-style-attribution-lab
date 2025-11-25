import { useState, useRef, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { analysisAPI } from '../api'
import { 
  Upload, 
  X, 
  Search, 
  Zap, 
  LogOut, 
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
  const { logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef(null)
  
  // UI State
  const [history, setHistory] = useState([])
  const [showSidebar, setShowSidebar] = useState(false)
  const [showPanel, setShowPanel] = useState(true)
  
  // Generation state
  const [generating, setGenerating] = useState(false)
  const [generationPrompt, setGenerationPrompt] = useState('')
  const [generatedImages, setGeneratedImages] = useState(null)
  const [generationError, setGenerationError] = useState('')

  useEffect(() => {
    const savedHistory = localStorage.getItem('analysis_history')
    if (savedHistory) {
      setHistory(JSON.parse(savedHistory))
    }
  }, [])

  // Auto-open sidebar if history exists, but only on large screens
  useEffect(() => {
    if (history.length > 0 && window.innerWidth >= 1024) {
      setShowSidebar(true)
    }
  }, [history.length])

  const addToHistory = (analysisResult, imagePreview) => {
    const newItem = {
      id: Date.now(),
      date: new Date().toISOString(),
      preview: imagePreview,
      artist: analysisResult.top_artists[0].artist_slug,
      result: analysisResult
    }
    const newHistory = [newItem, ...history]
    setHistory(newHistory)
    localStorage.setItem('analysis_history', JSON.stringify(newHistory))
  }

  const loadFromHistory = (item) => {
    setFile(null)
    setPreview(item.preview)
    setResult(item.result)
    setGeneratedImages(null)
    setGenerationPrompt('')
    setError('')
    setShowPanel(true)
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
      addToHistory(response.data, preview)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка анализа. Попробуйте снова.')
    } finally {
      setLoading(false)
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
      
      {/* Sidebar (History) */}
      <aside 
        className={`
          fixed lg:static inset-y-0 left-0 z-50 w-72 bg-gray-900/95 backdrop-blur-xl border-r border-white/10 transform transition-all duration-300 ease-in-out flex flex-col
          ${showSidebar ? 'translate-x-0' : '-translate-x-full lg:w-0 lg:border-none lg:overflow-hidden'}
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

        <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
          {history.length === 0 ? (
            <div className="text-center py-12 text-gray-500 text-sm">
              <History size={24} className="mx-auto mb-3 opacity-30" />
              <p>Нет сохраненных работ</p>
            </div>
          ) : (
            <div className="space-y-2">
              {history.map((item) => (
                <button
                  key={item.id}
                  onClick={() => loadFromHistory(item)}
                  className="w-full flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 transition-all group text-left border border-transparent hover:border-white/10"
                >
                  <div className="w-12 h-12 rounded-lg overflow-hidden bg-gray-800 flex-shrink-0 border border-white/10">
                    <img src={item.preview} alt="" className="w-full h-full object-cover" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate text-gray-200 group-hover:text-white transition-colors">
                      {formatArtistName(item.artist)}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(item.date).toLocaleDateString()}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-white/10">
          <button 
            onClick={logout}
            className="flex items-center gap-3 w-full p-3 rounded-xl hover:bg-red-500/10 text-gray-400 hover:text-red-400 transition-colors"
          >
            <LogOut size={20} />
            <span className="font-medium">Выйти</span>
          </button>
        </div>
      </aside>

      {/* Main Workspace */}
      <div className="flex-1 relative h-full flex flex-col min-w-0">
        
        {/* Top Bar */}
        <header className="absolute top-0 left-0 right-0 h-16 z-40 flex items-center justify-between px-6 pointer-events-none">
          <div className="flex items-center gap-4 pointer-events-auto">
            {!showSidebar && (
              <button 
                onClick={() => setShowSidebar(true)}
                className="p-2 bg-black/50 backdrop-blur-md border border-white/10 rounded-lg text-gray-300 hover:text-white hover:bg-white/10 transition-all"
              >
                <Menu size={20} />
              </button>
            )}
            <div className="flex items-center gap-3 bg-black/50 backdrop-blur-md border border-white/10 px-4 py-2 rounded-full">
              <div className="w-6 h-6 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-full flex items-center justify-center text-white text-[10px]">
                <Palette size={14} />
              </div>
              <span className="font-bold text-sm tracking-tight">Heritage Frame</span>
            </div>
          </div>

          <div className="flex items-center gap-3 pointer-events-auto">
            <button 
              onClick={toggleTheme}
              className="p-2.5 rounded-full bg-black/50 backdrop-blur-md border border-white/10 text-gray-300 hover:text-white hover:bg-white/10 transition-all"
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            {preview && (
              <button 
                onClick={() => setShowPanel(!showPanel)}
                className={`p-2.5 rounded-full backdrop-blur-md border transition-all ${showPanel ? 'bg-white text-black border-white' : 'bg-black/50 border-white/10 text-white'}`}
              >
                {showPanel ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
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
                <div className="relative max-w-full max-h-full shadow-2xl rounded-lg overflow-hidden group">
                  <img 
                    src={preview} 
                    alt="Analysis target" 
                    className="max-w-full max-h-[85vh] object-contain shadow-2xl"
                  />
                  
                  {/* Scanning Effect */}
                  {loading && (
                    <div className="absolute inset-0 z-20 pointer-events-none">
                      <div className="absolute left-0 right-0 h-1 bg-purple-500 shadow-[0_0_20px_rgba(168,85,247,0.8)] animate-scan" />
                      <div className="absolute inset-0 bg-purple-500/10 animate-pulse" />
                    </div>
                  )}

                  {/* Reset Button */}
                  <button 
                    onClick={handleReset}
                    className="absolute top-4 right-4 p-2 bg-black/60 backdrop-blur-md border border-white/20 rounded-lg text-white opacity-0 group-hover:opacity-100 transition-all hover:bg-red-500/80 hover:border-red-500"
                  >
                    <X size={20} />
                  </button>
                </div>

                {/* Analyze Button (Floating) */}
                {!result && !loading && (
                  <div className="absolute bottom-12 left-1/2 -translate-x-1/2 z-30">
                    <button
                      onClick={handleAnalyze}
                      className="group relative px-8 py-4 bg-white text-black rounded-full font-bold shadow-[0_0_40px_rgba(255,255,255,0.3)] hover:shadow-[0_0_60px_rgba(255,255,255,0.5)] hover:-translate-y-1 transition-all duration-300 overflow-hidden"
                    >
                      <span className="relative z-10 flex items-center gap-2 text-lg">
                        <Sparkles size={20} className="text-purple-600" />
                        Анализировать
                      </span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Floating Right Panel */}
          <div 
            className={`
              absolute top-4 bottom-4 right-4 w-[400px] bg-black/80 backdrop-blur-2xl border border-white/10 rounded-3xl shadow-2xl z-40 flex flex-col overflow-hidden transition-transform duration-500 cubic-bezier(0.4, 0, 0.2, 1)
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

                <div className="p-6 space-y-8">
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
                    <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                      <BookOpen size={16} className="text-orange-400" />
                      Анализ стиля
                    </h3>
                    <p className="text-sm text-gray-400 leading-relaxed">
                      {result.explanation.text}
                    </p>
                  </div>

                  {/* Generation Studio */}
                  <div className="pt-6 border-t border-white/10">
                    <div className="flex items-center gap-2 mb-4">
                      <Zap size={18} className="text-yellow-400" />
                      <h3 className="font-bold text-white">AI Ремикс</h3>
                    </div>
                    
                    <div className="space-y-3">
                      <textarea
                        value={generationPrompt}
                        onChange={(e) => setGenerationPrompt(e.target.value)}
                        placeholder={`Создать вариацию в стиле ${formatArtistName(result.top_artists[0].artist_slug)}...`}
                        className="w-full bg-black/30 border border-white/10 rounded-xl p-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-purple-500 transition-all resize-none h-20"
                      />
                      
                      <button
                        onClick={handleGenerate}
                        disabled={generating}
                        className="w-full py-3 bg-white text-black rounded-xl font-bold hover:bg-gray-200 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        {generating ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                        {generating ? 'Создание...' : 'Генерировать'}
                      </button>
                    </div>

                    {/* Generated Images Grid */}
                    {generatedImages && (
                      <div className="mt-6 grid grid-cols-2 gap-2 animate-fade-in">
                        {generatedImages.images.map((img, index) => (
                          <div key={index} className="group relative aspect-square rounded-lg overflow-hidden bg-gray-800">
                            <img src={img.url} alt="" className="w-full h-full object-cover" />
                            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                              <button className="p-2 bg-white/20 backdrop-blur rounded-full text-white hover:bg-white/40">
                                <Download size={16} />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {generationError && (
                      <p className="mt-3 text-xs text-red-400">{generationError}</p>
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
