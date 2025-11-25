import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authAPI } from '../api'
import { 
  Mail,
  Lock,
  User,
  UserPlus
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

    if (formData.password.length < 6) {
      setError('Пароль должен содержать минимум 6 символов')
      return
    }

    setLoading(true)

    try {
      await authAPI.register({
        email: formData.email,
        username: formData.username,
        password: formData.password,
      })
      navigate('/login', { 
        state: { message: 'Регистрация успешна! Войдите в свой аккаунт.' } 
      })
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка регистрации. Попробуйте снова.')
    } finally {
      setLoading(false)
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
          <p className="auth-title-centered">Создать аккаунт</p>
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
            <label className="form-label" htmlFor="username">
              <User size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              Имя пользователя
            </label>
            <input
              type="text"
              id="username"
              name="username"
              className="form-input"
              placeholder="username"
              value={formData.username}
              onChange={handleChange}
              required
              minLength={3}
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
              minLength={6}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="confirmPassword">
              <Lock size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              Подтвердите пароль
            </label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              className="form-input"
              placeholder="••••••••"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="loading-spinner" />
                &nbsp;Создание аккаунта...
              </>
            ) : (
              <>
                <UserPlus size={18} style={{ marginRight: 8 }} />
                Зарегистрироваться
              </>
            )}
          </button>
        </form>

        <p className="auth-link">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </div>
    </div>
  )
}

export default Register
