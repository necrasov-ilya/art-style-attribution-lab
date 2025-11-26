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
      setError(err.response?.data?.detail || 'Ошибка входа. Проверьте данные.')
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
      setError('Гостевой доступ недоступен.')
    } finally {
      setGuestLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center relative overflow-hidden font-sans">
      {/* Background */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-[url('/images/backgrounds/auth-bg.png')] bg-cover bg-center" />
      </div>

      {/* Card */}
      <div className="relative z-10 w-full max-w-md bg-black/100 shadow-2xl border border-white/10 p-8 md:p-10 animate-scale-in">
        <div className="text-center mb-8">
          <h2 className="font-serif text-4xl text-white mb-3 tracking-tight">Heritage Frame</h2>
          <p className="text-gray-400 font-light tracking-wide text-sm uppercase">
            Лаборатория атрибуции цифрового искусства
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-300 uppercase tracking-widest ml-1">Email</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="block w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-white/20 transition-all"
              placeholder="curator@museum.org"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-300 uppercase tracking-widest ml-1">Пароль</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className="block w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-white/20 transition-all"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading || guestLoading}
            className="w-full py-3.5 bg-white text-black font-bold rounded-xl hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-6 flex items-center justify-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                Войти в галерею
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
            <span className="px-4 bg-black/40 backdrop-blur-xl text-gray-500 rounded-full">Или продолжить как</span>
          </div>
        </div>

        <button
          onClick={handleGuestLogin}
          disabled={loading || guestLoading}
          className="w-full py-3.5 border border-white/10 text-gray-300 hover:text-white hover:bg-white/5 rounded-xl transition-all font-medium text-sm uppercase tracking-wider flex items-center justify-center gap-2"
        >
          {guestLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <UserCircle size={18} />
              Гость
            </>
          )}
        </button>

        <p className="text-center text-xs text-gray-500 mt-8 uppercase tracking-widest">
          Впервые здесь?{' '}
          <Link to="/register" className="text-white hover:text-gray-300 transition-colors border-b border-white/30 pb-0.5">
            Регистрация
          </Link>
        </p>
      </div>
    </div>
  )
}

export default Login
