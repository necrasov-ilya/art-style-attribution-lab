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

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
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
   */
  analyzeFull: (imagePath) => 
    api.get('/deep-analysis/full', { params: { image_path: imagePath } }),
  
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
}

export default api
