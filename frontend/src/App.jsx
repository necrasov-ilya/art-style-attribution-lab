import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Login from './pages/Login'
import Register from './pages/Register'
import Analyze from './pages/Analyze'
import CollaborativeView from './pages/CollaborativeView'
import { AuthProvider, useAuth } from './context/AuthContext'

function PrivateRoute({ children }) {
  const { token } = useAuth()
  return token ? children : <Navigate to="/login" />
}

function PublicRoute({ children }) {
  const { token } = useAuth()
  return !token ? children : <Navigate to="/" />
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <Register />
          </PublicRoute>
        }
      />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Analyze />
          </PrivateRoute>
        }
      />
      {/* Public collaborative session route - no auth required */}
      <Route
        path="/collab/:sessionId"
        element={<CollaborativeView />}
      />
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <div className="app">
        <AppRoutes />
      </div>
    </AuthProvider>
  )
}

export default App
