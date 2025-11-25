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
}

export default api
