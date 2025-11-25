import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authAPI } from '../api'
import { useAuth } from '../context/AuthContext'
import { 
  Mail,
  Lock,
  LogIn,
  UserCircle
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
      setError(err.response?.data?.detail || 'Ошибка входа. Проверьте данные и попробуйте снова.')
    } finally {
      setLoading(false)
    }
  }

  const handleGuestLogin = async () => {
    setError('')
    setGuestLoading(true)
    
    try {
      const response = await authAPI.guest()
      login(response.data.access_token)
      navigate('/')
    } catch (err) {
      setError('Не удалось войти как гость. Попробуйте снова.')
    } finally {
      setGuestLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card-centered">
        <div className="auth-header-centered">
          <img 
            src="/images/logo.png" 
            alt="Heritage Frame Logo" 
            className="auth-logo-centered"
          />
          <h1 className="auth-app-name">Heritage Frame</h1>
          <p className="auth-title-centered">Вход в систему</p>
        </div>

        {error && <div className="alert alert-error" style={{width: '100%'}}>{error}</div>}

        <form onSubmit={handleSubmit} style={{width: '100%'}}>
          <div className="form-group">
            <label className="form-label" htmlFor="email">
              <Mail size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              Email
            </label>
            <input
              type="email"
              id="email"
              name="email"
              className="form-input"
              placeholder="your@email.com"
              value={formData.email}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">
              <Lock size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              Пароль
            </label>
            <input
              type="password"
              id="password"
              name="password"
              className="form-input"
              placeholder="••••••••"
              value={formData.password}
              onChange={handleChange}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={loading || guestLoading}
          >
            {loading ? (
              <>
                <span className="loading-spinner" />
                &nbsp;Вход...
              </>
            ) : (
              <>
                <LogIn size={18} style={{ marginRight: 8 }} />
                Войти
              </>
            )}
          </button>
        </form>

        <div className="auth-divider">
          <div className="auth-divider-line" />
          <span className="auth-divider-text">или</span>
          <div className="auth-divider-line" />
        </div>

        <button
          type="button"
          className="btn btn-guest btn-full"
          onClick={handleGuestLogin}
          disabled={loading || guestLoading}
        >
          {guestLoading ? (
            <>
              <span className="loading-spinner" style={{ borderColor: 'rgba(55, 65, 81, 0.3)', borderTopColor: 'var(--gray-700)' }} />
              &nbsp;Вход...
            </>
          ) : (
            <>
              <UserCircle size={18} />
              Войти как гость
            </>
          )}
        </button>

        <p className="auth-link">
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </p>
      </div>
    </div>
  )
}

export default Login
