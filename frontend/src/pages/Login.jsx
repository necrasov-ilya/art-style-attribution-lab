import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authAPI } from '../api'
import { useAuth } from '../context/AuthContext'
import { 
  ArrowRight,
  UserCircle,
  Loader2
} from 'lucide-react'

function Login() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [guestLoading, setGuestLoading] = useState(false)
  const navigate = useNavigate()
  const { login } = useAuth()

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await authAPI.login(formData)
      login(response.data.access_token)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed. Please verify your credentials.')
    } finally {
      setLoading(false)
    }
  }

  const handleGuestLogin = async () => {
    setError('')
    setGuestLoading(true)
    
    try {
      const response = await authAPI.guest()
      login(response.data.access_token, { isGuest: true })
      navigate('/')
    } catch (err) {
      setError('Guest access unavailable. Please try again.')
    } finally {
      setGuestLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-full bg-charcoal-950 text-alabaster-100 flex items-center justify-center relative overflow-hidden font-sans selection:bg-gold-500/30">
      <div className="bg-grain" />
      
      {/* Ambient Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-gold-500/5 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-charcoal-800/50 blur-[120px] rounded-full" />
      </div>

      {/* Card */}
      <div className="relative z-10 w-full max-w-md p-12">
        <div className="text-center mb-12">
          <h2 className="font-serif text-4xl text-white mb-3 tracking-tight">Heritage Frame</h2>
          <p className="text-gray-400 font-light tracking-wide text-sm uppercase">
            Digital Art Attribution Laboratory
          </p>
        </div>

        {error && (
          <div className="mb-8 p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <label className="text-xs font-bold text-gold-500 uppercase tracking-widest ml-1">Email</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="block w-full px-4 py-3 bg-white/5 border border-white/10 text-white placeholder-gray-600 focus:outline-none focus:border-gold-500/50 focus:bg-white/10 transition-all font-light"
              placeholder="curator@museum.org"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold text-gold-500 uppercase tracking-widest ml-1">Password</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className="block w-full px-4 py-3 bg-white/5 border border-white/10 text-white placeholder-gray-600 focus:outline-none focus:border-gold-500/50 focus:bg-white/10 transition-all font-light"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading || guestLoading}
            className="w-full py-4 bg-white text-black font-serif font-bold text-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-8 flex items-center justify-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                Enter Gallery
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className="relative my-8">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/10" />
          </div>
          <div className="relative flex justify-center text-xs uppercase tracking-widest">
            <span className="px-4 bg-charcoal-950 text-gray-600">Or continue as</span>
          </div>
        </div>

        <button
          onClick={handleGuestLogin}
          disabled={loading || guestLoading}
          className="w-full py-3 border border-white/10 text-gray-400 hover:text-white hover:border-white/30 transition-all font-medium text-sm uppercase tracking-wider flex items-center justify-center gap-2"
        >
          {guestLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <UserCircle size={18} />
              Guest Visitor
            </>
          )}
        </button>

        <p className="text-center text-xs text-gray-600 mt-12 uppercase tracking-widest">
          New to the collection?{' '}
          <Link to="/register" className="text-gold-500 hover:text-gold-400 transition-colors border-b border-gold-500/30 pb-0.5">
            Register Access
          </Link>
        </p>
      </div>
    </div>
  )
}

export default Login
