import { useState, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import { analysisAPI } from '../api'

function Analyze() {
  const { logout } = useAuth()
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef(null)
  
  // Generation state
  const [generating, setGenerating] = useState(false)
  const [generationPrompt, setGenerationPrompt] = useState('')
  const [generatedImages, setGeneratedImages] = useState(null)
  const [generationError, setGenerationError] = useState('')

  const handleFileSelect = (selectedFile) => {
    if (!selectedFile) return

    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp']
    if (!validTypes.includes(selectedFile.type)) {
      setError('Please select a valid image file (JPEG, PNG, WebP, BMP)')
      return
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File size must be less than 10MB')
      return
    }

    setFile(selectedFile)
    setPreview(URL.createObjectURL(selectedFile))
    setError('')
    setResult(null)
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
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed. Please try again.')
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
      setGenerationError(err.response?.data?.detail || 'Generation failed. Please try again.')
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
    <div className="page">
      <header className="header">
        <div className="container header-content">
          <h1 className="logo">🎨 Art Style Attribution Lab</h1>
          <button className="btn btn-secondary" onClick={logout}>
            Sign Out
          </button>
        </div>
      </header>

      <main className="main">
        <div className="container">
          {/* Upload Section */}
          <div className="upload-section">
            <h2 style={{ marginBottom: '16px' }}>Analyze Artwork</h2>

            {error && <div className="alert alert-error">{error}</div>}

            <div
              className={`upload-area ${dragging ? 'dragging' : ''}`}
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
                style={{ display: 'none' }}
              />

              {preview ? (
                <div>
                  <img src={preview} alt="Preview" className="preview-image" />
                  <p style={{ color: 'var(--text-muted)', marginTop: '8px' }}>
                    {file?.name}
                  </p>
                </div>
              ) : (
                <>
                  <div className="upload-icon">📤</div>
                  <p className="upload-text">
                    Drop an image here or click to upload
                  </p>
                  <p className="upload-hint">
                    Supports JPEG, PNG, WebP, BMP up to 10MB
                  </p>
                </>
              )}
            </div>

            <div style={{ marginTop: '24px', display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                className="btn btn-primary"
                onClick={handleAnalyze}
                disabled={!file || loading}
              >
                {loading ? (
                  <>
                    <span className="loading-spinner" />
                    &nbsp;Analyzing...
                  </>
                ) : (
                  '🔍 Analyze'
                )}
              </button>
              {file && (
                <button className="btn btn-secondary" onClick={handleReset}>
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="loading-overlay">
              <span className="loading-spinner" />
              <span>Analyzing artwork style... This may take a moment.</span>
            </div>
          )}

          {/* Results Section */}
          {result && !loading && (
            <div className="results-section">
              {/* Top Artists */}
              <div className="result-card">
                <h3 className="result-title">🎭 Top Artists</h3>
                <ul className="artists-list">
                  {result.top_artists.map((artist, index) => (
                    <li key={artist.artist_slug} className="artist-item">
                      <span className="artist-rank">#{index + 1}</span>
                      <span className="artist-name">
                        {formatArtistName(artist.artist_slug)}
                      </span>
                      <span className="artist-probability">
                        {(artist.probability * 100).toFixed(1)}%
                      </span>
                      <div className="probability-bar">
                        <div
                          className="probability-fill"
                          style={{ width: `${artist.probability * 100}%` }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Styles & Genres */}
              <div className="result-card">
                <h3 className="result-title">🎨 Style & Genre</h3>
                
                {result.top_styles && result.top_styles.length > 0 && (
                  <div style={{ marginBottom: '16px' }}>
                    <h4 style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                      Art Styles
                    </h4>
                    <ul className="artists-list">
                      {result.top_styles.map((style, index) => (
                        <li key={style.name} className="artist-item">
                          <span className="artist-rank">#{index + 1}</span>
                          <span className="artist-name">{formatName(style.name)}</span>
                          <span className="artist-probability">
                            {(style.probability * 100).toFixed(1)}%
                          </span>
                          <div className="probability-bar">
                            <div
                              className="probability-fill"
                              style={{ width: `${style.probability * 100}%`, background: '#10b981' }}
                            />
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {result.top_genres && result.top_genres.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                      Genres
                    </h4>
                    <ul className="artists-list">
                      {result.top_genres.map((genre, index) => (
                        <li key={genre.name} className="artist-item">
                          <span className="artist-rank">#{index + 1}</span>
                          <span className="artist-name">{formatName(genre.name)}</span>
                          <span className="artist-probability">
                            {(genre.probability * 100).toFixed(1)}%
                          </span>
                          <div className="probability-bar">
                            <div
                              className="probability-fill"
                              style={{ width: `${genre.probability * 100}%`, background: '#f59e0b' }}
                            />
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Explanation */}
              <div className="result-card" style={{ gridColumn: 'span 2' }}>
                <h3 className="result-title">📝 Analysis</h3>
                <p className="explanation-text">{result.explanation.text}</p>
                {result.explanation.source === 'stub' && (
                  <p style={{ marginTop: '12px', fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    Note: This is a placeholder explanation. LLM integration coming soon.
                  </p>
                )}
              </div>

              {/* Image Generation Section */}
              <div className="result-card" style={{ gridColumn: 'span 2' }}>
                <h3 className="result-title">🎨 Generate in This Style</h3>
                <p style={{ color: 'var(--text-muted)', marginBottom: '16px', fontSize: '0.875rem' }}>
                  Generate new images in the style of {formatArtistName(result.top_artists[0]?.artist_slug || 'artist')}
                </p>
                
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Describe what you want to generate (optional):
                  </label>
                  <textarea
                    value={generationPrompt}
                    onChange={(e) => setGenerationPrompt(e.target.value)}
                    placeholder="e.g., a sunset over the ocean, a portrait of a cat, a mystical forest..."
                    style={{
                      width: '100%',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)',
                      fontSize: '0.875rem',
                      minHeight: '80px',
                      resize: 'vertical',
                      fontFamily: 'inherit'
                    }}
                  />
                </div>
                
                {generationError && (
                  <div className="alert alert-error" style={{ marginBottom: '16px' }}>
                    {generationError}
                  </div>
                )}
                
                <button
                  className="btn btn-primary"
                  onClick={handleGenerate}
                  disabled={generating}
                  style={{ marginBottom: '16px' }}
                >
                  {generating ? (
                    <>
                      <span className="loading-spinner" />
                      &nbsp;Generating...
                    </>
                  ) : (
                    '🖼️ Generate Images'
                  )}
                </button>
                
                {/* Generated Images */}
                {generatedImages && (
                  <div style={{ marginTop: '16px' }}>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '12px' }}>
                      <strong>Prompt used:</strong> {generatedImages.prompt}
                    </p>
                    <div className="thumbnails-grid">
                      {generatedImages.images.map((img, index) => (
                        <div key={index} className="thumbnail-card">
                          <img
                            src={img.url}
                            alt={`Generated ${index + 1}`}
                            className="thumbnail-image"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default Analyze
