import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authAPI } from '../api'
import { useAuth } from '../context/AuthContext'
import { 
  ArrowRight,
  Loader2
} from 'lucide-react'

function Register() {
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
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

    if (formData.password !== formData.confirmPassword) {
      setError('Пароли не совпадают')
      return
    }

    setLoading(true)

    try {
      await authAPI.register({
        email: formData.email,
        username: formData.username,
        password: formData.password,
      })
      // Auto login after registration
      const loginResponse = await authAPI.login({
        email: formData.email,
        password: formData.password,
      })
      login(loginResponse.data.access_token)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка регистрации. Попробуйте снова.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center relative p-4 overflow-hidden font-sans">
      {/* Background */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-[url('/images/backgrounds/auth-bg.png')] bg-cover bg-center" />
      </div>

      {/* Card */}
      <div className="relative z-10 w-full max-w-md bg-black/100 shadow-2xl border border-white/10 p-8 md:p-10 animate-scale-in">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-3">
            <img src="/images/logo.svg" alt="Logo" className="w-10 h-10" />
            <h2 className="font-serif text-4xl text-white tracking-tight">Heritage Frame</h2>
          </div>
          <p className="text-gray-400 font-light tracking-wide text-sm uppercase">
            Создание аккаунта
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-3 animate-shake">
            <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-300 uppercase tracking-widest ml-1">Имя пользователя</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className="block w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-white/20 transition-all"
              placeholder="username"
              required
              minLength={3}
            />
          </div>

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
              minLength={6}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-300 uppercase tracking-widest ml-1">Подтвердите пароль</label>
            <input
              type="password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              className="block w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-white/20 transition-all"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 bg-white text-black font-bold rounded-xl hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-6 flex items-center justify-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                Создать аккаунт
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <p className="text-center text-xs text-gray-500 mt-8 uppercase tracking-widest">
          Уже есть аккаунт?{' '}
          <Link to="/login" className="text-white hover:text-gray-300 transition-colors border-b border-white/30 pb-0.5">
            Войти
          </Link>
        </p>
      </div>
    </div>
  )
}

export default Register
