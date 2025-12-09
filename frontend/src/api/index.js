import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle auth errors and rate limiting
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    
    // Enhance 429 errors with retry info
    if (error.response?.status === 429) {
      const retryAfter = error.response.headers['retry-after']
      if (retryAfter) {
        error.retryAfter = parseInt(retryAfter, 10)
        // Add human-readable message
        const detail = error.response.data?.detail || ''
        error.message = detail || `Слишком много запросов. Подождите ${retryAfter} секунд.`
      }
    }
    
    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  guest: () => api.post('/auth/guest'),
}

// Analysis API
export const analysisAPI = {
  analyze: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/analyze', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
  
  /**
   * Analyze image with SSE streaming for real-time updates
   * @param {File} file - Image file to analyze
   * @param {Object} callbacks - Event callbacks
   * @param {Function} callbacks.onPredictions - Called with ML predictions (artists, genres, styles)
   * @param {Function} callbacks.onVision - Called with Vision AI analysis (for Unknown Artist)
   * @param {Function} callbacks.onText - Called with each text chunk from LLM
   * @param {Function} callbacks.onComplete - Called when analysis is complete
   * @param {Function} callbacks.onError - Called on error
   * @returns {Promise<void>}
   */
  analyzeStream: async (file, { onPredictions, onVision, onText, onComplete, onError }) => {
    const formData = new FormData()
    formData.append('file', file)
    
    const token = localStorage.getItem('token')
    let receivedComplete = false
    let receivedError = false
    let receivedPredictions = false
    
    try {
      const response = await fetch('/api/analyze/stream', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        // Try to extract error message from JSON
        let errorMsg = `HTTP ${response.status}`
        try {
          const errorJson = JSON.parse(errorText)
          errorMsg = errorJson.detail || errorJson.error || errorMsg
        } catch {
          errorMsg = errorText || errorMsg
        }
        throw new Error(errorMsg)
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        
        // Parse SSE events
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer
        
        let currentEvent = null
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6)
            try {
              const parsed = JSON.parse(data)
              
              switch (currentEvent) {
                case 'predictions':
                  receivedPredictions = true
                  onPredictions?.(parsed)
                  break
                case 'vision':
                  onVision?.(parsed)
                  break
                case 'text':
                  onText?.(parsed.chunk || '')
                  break
                case 'complete':
                  receivedComplete = true
                  onComplete?.(parsed)
                  break
                case 'error':
                  receivedError = true
                  onError?.(parsed.error || 'Unknown error')
                  break
              }
            } catch (e) {
              // Ignore JSON parse errors for incomplete data
            }
            currentEvent = null
          }
        }
      }
      
      // If stream ended without complete or error event, handle gracefully
      if (!receivedComplete && !receivedError) {
        if (receivedPredictions) {
          // We got predictions but stream died - consider it complete with what we have
          onComplete?.({ success: true, explanation_source: 'interrupted' })
        } else {
          // Stream ended with nothing - report error
          onError?.('Stream connection closed unexpectedly')
        }
      }
    } catch (error) {
      onError?.(error.message || 'Connection error')
    }
  },
  
  generate: (data) => {
    // data: { artist_slug, style_name?, genre_name?, user_prompt?, count? }
    return api.post('/generate', data)
  },
}

// History API
export const historyAPI = {
  getAll: (limit = 50, offset = 0) => api.get(`/history?limit=${limit}&offset=${offset}`),
  delete: (id) => api.delete(`/history/${id}`),
  clear: () => api.delete('/history'),
  updateDeepAnalysis: (id, deepAnalysisResult) => 
    api.patch(`/history/${id}/deep-analysis`, { deep_analysis_result: deepAnalysisResult }),
}

// Deep Analysis API
export const deepAnalysisAPI = {
  /**
   * Run a single analysis module
   * @param {string} module - One of: color, composition, scene, technique, historical
   * @param {string} imagePath - Path to image (e.g., /api/uploads/filename.jpg)
   */
  analyzeModule: (module, imagePath) => 
    api.get(`/deep-analysis/module/${module}`, { params: { image_path: imagePath } }),
  
  /**
   * Run full deep analysis with all modules
   * @param {string} imagePath - Path to image (e.g., /api/uploads/filename.jpg)
   * Note: Extended timeout for heavy LLM operations
   */
  analyzeFull: (imagePath) => 
    api.get('/deep-analysis/full', { 
      params: { image_path: imagePath },
      timeout: 300000
    }),
  
  /**
   * Get raw color features without LLM interpretation
   * @param {string} imagePath - Path to image
   */
  getColorFeatures: (imagePath) => 
    api.get('/deep-analysis/features/color', { params: { image_path: imagePath } }),
  
  /**
   * Get raw composition features without LLM interpretation
   * @param {string} imagePath - Path to image
   */
  getCompositionFeatures: (imagePath) => 
    api.get('/deep-analysis/features/composition', { params: { image_path: imagePath } }),
}

// Collaborative Session API
export const collaborativeAPI = {
  /**
   * Create a new collaborative session
   * @param {object} data - { analysis_data, image_url }
   */
  create: (data) => api.post('/collaborative', data),
  
  /**
   * Get public session info (for guests)
   * @param {string} sessionId - Session UUID
   */
  getSession: (sessionId) => api.get(`/collaborative/${sessionId}`),
  
  /**
   * Get full session info (for owner)
   * @param {string} sessionId - Session UUID
   */
  getSessionFull: (sessionId) => api.get(`/collaborative/${sessionId}/full`),
  
  /**
   * Ask a question (non-streaming)
   * @param {string} sessionId - Session UUID
   * @param {string} question - The question to ask
   */
  askQuestion: (sessionId, question) => 
    api.post(`/collaborative/${sessionId}/ask`, { question }),
  
  /**
   * Ask a question with streaming response
   * Returns the URL for SSE connection
   * @param {string} sessionId - Session UUID
   * @param {string} question - The question to ask
   */
  askQuestionStreamUrl: (sessionId) => 
    `${API_BASE_URL}/collaborative/${sessionId}/ask/stream`,
  
  /**
   * Send heartbeat to register presence
   * @param {string} sessionId - Session UUID
   * @param {string} viewerId - Unique viewer ID (optional)
   */
  heartbeat: (sessionId, viewerId = null) => {
    const params = viewerId ? `?viewer_id=${viewerId}` : ''
    return api.post(`/collaborative/${sessionId}/heartbeat${params}`)
  },
  
  /**
   * Get viewer count (for owner)
   * @param {string} sessionId - Session UUID
   */
  getViewers: (sessionId) => api.get(`/collaborative/${sessionId}/viewers`),
  
  /**
   * Close a session (owner only)
   * @param {string} sessionId - Session UUID
   */
  close: (sessionId) => api.delete(`/collaborative/${sessionId}`),
  
  /**
   * Update session analysis data (owner only)
   * Used to sync deep analysis results to active session
   * @param {string} sessionId - Session UUID
   * @param {object} analysisData - Updated analysis data
   */
  updateAnalysis: (sessionId, analysisData) => 
    api.patch(`/collaborative/${sessionId}`, { analysis_data: analysisData }),
}

export default api
