import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { analysisAPI, historyAPI } from '../api'
import { motion, AnimatePresence, useScroll, useTransform } from 'framer-motion'
import { 
  Upload, X, Search, Zap, LogOut, LogIn, Palette, Brush, BookOpen, 
  Sparkles, Loader2, Download, History, ChevronLeft, ChevronRight, 
  Maximize2, PanelRightClose, PanelRightOpen, Image as ImageIcon,
  Share2, Info, Layers, Eye, Menu, Clock
} from 'lucide-react'

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

  // Scroll parallax hooks
  const { scrollYProgress } = useScroll()
  const imageScale = useTransform(scrollYProgress, [0, 1], [1, 0.8])
  const imageOpacity = useTransform(scrollYProgress, [0, 0.5], [1, 0])

  // Load history
  useEffect(() => {
    if (!isGuest) {
      loadHistory()
    }
  }, [isGuest])

  const loadHistory = () => {
    historyAPI.getAll().then(res => setHistory(res.data.items || [])).catch(console.error)
  }

  const handleFileSelect = (selectedFile) => {
    if (!selectedFile) return
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File size must be under 10MB')
      return
    }
    setFile(selectedFile)
    setPreview(URL.createObjectURL(selectedFile))
    setError('')
    setResult(null)
    setGeneratedImages(null)
    setDeepAnalysisActive(false)
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
      setError('Analysis failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleDeepAnalysis = () => {
    setDeepAnalysisActive(true)
    setDeepAnalysisStep(0)
    // Simulate deep analysis pipeline
    let step = 0
    const interval = setInterval(() => {
      step++
      setDeepAnalysisStep(step)
      if (step >= 4) clearInterval(interval)
    }, 1500)
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
      setGenerationError('Generation failed.')
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
              title="History"
            >
              <History size={20} />
            </button>
          )}
          
          {isGuest ? (
            <button 
              onClick={() => { logout(); navigate('/login'); }} 
              className="px-6 py-2 bg-white text-black font-medium text-sm hover:bg-gray-200 transition-colors rounded-sm shadow-lg"
            >
              Sign In
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
                  <h2 className="font-serif text-xl text-white">Collection History</h2>
                  <button onClick={() => setShowHistory(false)} className="text-gray-400 hover:text-white">
                    <X size={20} />
                  </button>
                </div>
                
                <div className="space-y-4">
                  {history.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <Clock className="w-8 h-8 mx-auto mb-3 opacity-50" />
                      <p className="text-sm">No analysis history yet</p>
                    </div>
                  ) : (
                    history.map((item) => (
                      <div key={item.id} className="group relative aspect-video bg-black/40 border border-white/5 hover:border-gold-500/30 transition-all rounded overflow-hidden cursor-pointer">
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
      <div className="relative min-h-screen flex flex-col items-center justify-center p-8 pb-32">
        {/* Background Ambient */}
        {preview && (
          <motion.div 
            style={{ opacity: imageOpacity }}
            className="fixed inset-0 z-0"
          >
            <div 
              className="absolute inset-0 bg-cover bg-center blur-[100px] opacity-20 scale-110"
              style={{ backgroundImage: `url(${preview})` }}
            />
          </motion.div>
        )}

        <motion.div 
          style={{ scale: result ? imageScale : 1 }}
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
                    <h2 className="font-serif text-3xl text-white mb-3">Upload Artwork</h2>
                    <p className="text-gray-400 font-light tracking-wide text-sm">Drag & drop or click to select</p>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div 
                layoutId="preview-image"
                className="relative w-full flex flex-col items-center"
              >
                <div className="relative shadow-2xl group">
                  <img 
                    src={preview} 
                    alt="Preview" 
                    className={`
                      max-h-[85vh] w-auto object-contain shadow-[0_20px_50px_rgba(0,0,0,0.5)]
                      transition-all duration-[2000ms] ease-out
                      ${loading ? 'blur-md grayscale scale-95 opacity-80' : 'blur-0 grayscale-0 scale-100 opacity-100'}
                    `} 
                  />
                  
                  {/* Developing Overlay */}
                  {loading && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="w-full h-full bg-black/20 backdrop-blur-[2px] animate-pulse" />
                      <div className="absolute text-gold-500 font-serif tracking-widest text-sm uppercase animate-bounce">
                        Analyzing...
                      </div>
                    </div>
                  )}

                  {/* Controls */}
                  <div className={`absolute -bottom-16 left-1/2 -translate-x-1/2 flex items-center gap-4 transition-opacity duration-300 ${loading ? 'opacity-0' : 'opacity-100'}`}>
                    {!result && (
                      <button 
                        onClick={handleAnalyze}
                        className="px-8 py-3 bg-white text-black font-serif font-medium tracking-wide hover:bg-gray-200 transition-colors shadow-lg whitespace-nowrap"
                      >
                        Analyze Artwork
                      </button>
                    )}
                    <button 
                      onClick={() => { setFile(null); setPreview(null); setResult(null) }}
                      className="p-3 bg-black/50 backdrop-blur text-white border border-white/10 hover:bg-white hover:text-black transition-colors rounded-full"
                    >
                      <X size={20} />
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
        
        {/* Scroll Indicator */}
        {result && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute bottom-8 left-1/2 -translate-x-1/2 text-white/50 flex flex-col items-center gap-2 animate-bounce"
          >
            <span className="text-xs uppercase tracking-widest">Scroll to Discover</span>
            <ChevronRight className="rotate-90" />
          </motion.div>
        )}
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
                    Attribution Report
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
                  <span className="text-xs text-gray-500 uppercase tracking-wider">Match Confidence</span>
                </div>
                <div className="text-center border-r border-white/10">
                  <span className="block text-4xl font-serif text-white mb-2">#{result.top_artists[0].index}</span>
                  <span className="text-xs text-gray-500 uppercase tracking-wider">Database Rank</span>
                </div>
                <div className="text-center">
                  <span className="block text-4xl font-serif text-white mb-2">AI</span>
                  <span className="text-xs text-gray-500 uppercase tracking-wider">Analysis Model</span>
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
                    <h3 className="font-serif text-3xl text-white">Deep Analysis</h3>
                    <span className="text-xs text-gold-500 border border-gold-500/30 px-3 py-1 rounded-full bg-gold-500/10 font-bold tracking-wider">AI PRO SUITE</span>
                  </div>

                  {!deepAnalysisActive ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {[
                        { icon: Palette, label: "Color Psychology", desc: "Emotional impact of palette" },
                        { icon: Layers, label: "Composition", desc: "Golden ratio & balance" },
                        { icon: BookOpen, label: "Historical Context", desc: "Era & influences" },
                        { icon: Brush, label: "Technique", desc: "Brushwork analysis" }
                      ].map((item, i) => (
                        <button 
                          key={i}
                          className="p-6 border border-white/10 hover:border-gold-500/50 bg-black/20 hover:bg-white/5 transition-all text-left group rounded-xl"
                        >
                          <item.icon className="w-8 h-8 text-gray-500 group-hover:text-gold-400 mb-4 transition-colors" />
                          <div className="font-medium text-xl text-white mb-1">{item.label}</div>
                          <div className="text-sm text-gray-500">{item.desc}</div>
                        </button>
                      ))}
                      
                      <button 
                        onClick={handleDeepAnalysis}
                        className="col-span-1 md:col-span-2 mt-4 py-6 bg-gradient-to-r from-gold-600 to-gold-400 text-black font-bold text-lg tracking-wide hover:shadow-[0_0_30px_rgba(212,175,55,0.3)] transition-all relative overflow-hidden group rounded-xl"
                      >
                        <span className="relative z-10 flex items-center justify-center gap-3">
                          <Sparkles size={20} /> Run Full Deep Analysis Pipeline
                        </span>
                        <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-500" />
                      </button>
                    </div>
                  ) : (
                    <div className="border border-gold-500/30 bg-gold-500/5 p-8 rounded-xl relative overflow-hidden min-h-[300px] flex flex-col justify-center">
                      <div className="absolute inset-0 bg-grain opacity-10" />
                      
                      {deepAnalysisStep < 4 ? (
                        <div className="py-8 text-center">
                          <Loader2 className="w-10 h-10 text-gold-500 animate-spin mx-auto mb-6" />
                          <p className="text-gold-200 font-serif text-2xl animate-pulse">
                            {[
                              "Extracting color palette...",
                              "Analyzing compositional structure...",
                              "Querying historical database...",
                              "Synthesizing final report..."
                            ][deepAnalysisStep]}
                          </p>
                        </div>
                      ) : (
                        <div className="text-left animate-fade-in">
                          <div className="mb-8">
                            <h4 className="text-gold-400 text-sm uppercase tracking-wider mb-4 font-bold">Dominant Palette</h4>
                            <div className="flex h-16 w-full rounded-lg overflow-hidden shadow-lg">
                              {['#2A1B15', '#8B4513', '#CD853F', '#DEB887', '#F5DEB3'].map(c => (
                                <div key={c} className="flex-1 hover:flex-[1.5] transition-all duration-300" style={{ backgroundColor: c }} title={c} />
                              ))}
                            </div>
                          </div>
                          
                          <div className="space-y-6 text-gray-300 leading-relaxed text-lg">
                            <p><strong className="text-white block mb-1">Color Psychology</strong> The dominance of earth tones (Sienna, Ochre) suggests a grounding, organic atmosphere typical of the period.</p>
                            <p><strong className="text-white block mb-1">Composition</strong> The subject is placed according to the rule of thirds, creating a dynamic yet balanced visual weight.</p>
                            <p><strong className="text-white block mb-1">Technique</strong> Visible impasto strokes indicate a rapid, expressive application of paint, characteristic of the artist's later years.</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Generation Studio */}
              <div className="border-t border-white/10 pt-24">
                <h3 className="font-serif text-4xl text-white mb-8 text-center">AI Re-Imagination</h3>
                <p className="text-center text-gray-400 mb-12 max-w-2xl mx-auto">
                  Visualize this artwork in different contexts or variations using our generative model.
                </p>
                
                <div className="flex gap-4 mb-12 max-w-2xl mx-auto">
                  <input 
                    type="text" 
                    value={generationPrompt}
                    onChange={(e) => setGenerationPrompt(e.target.value)}
                    placeholder="Describe a variation (e.g. 'in a stormy weather')"
                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-6 py-4 text-white placeholder-gray-500 focus:border-gold-500 focus:outline-none transition-colors"
                  />
                  <button 
                    onClick={handleGenerate}
                    disabled={generating}
                    className="px-8 py-4 bg-white text-black font-bold rounded-lg hover:bg-gray-200 transition-colors text-sm uppercase tracking-wider disabled:opacity-50 whitespace-nowrap"
                  >
                    {generating ? 'Dreaming...' : 'Generate'}
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
                            title="Download"
                          >
                            <Download size={24} />
                          </button>
                          <button 
                            onClick={() => window.open(img.url, '_blank')}
                            className="p-4 bg-white/10 text-white backdrop-blur rounded-full hover:bg-white hover:text-black transition-all shadow-xl"
                            title="View Full Size"
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
