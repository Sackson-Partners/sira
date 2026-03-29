import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import AuthLogin from './pages/auth/Login'
import Dashboard from './pages/Dashboard'
import Alerts from './pages/Alerts'
import Cases from './pages/Cases'
import Movements from './pages/Movements'
import Users from './pages/Users'
import Settings from './pages/Settings'
import ControlTower from './pages/ControlTower'
import FleetManagement from './pages/FleetManagement'
import PortOperations from './pages/PortOperations'
import MarketIntelligence from './pages/MarketIntelligence'
import ShipmentWorkspace from './pages/ShipmentWorkspace'
import ProtectedRoute from './components/ProtectedRoute'
import Unauthorized from './pages/Unauthorized'
import RoleDashboard from './pages/dashboards/RoleDashboard'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/auth/login" element={<AuthLogin />} />
        <Route path="/unauthorized" element={<Unauthorized />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <RoleDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/*"
          element={
            <PrivateRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/control-tower" element={<ControlTower />} />
                  <Route path="/shipments" element={<ShipmentWorkspace />} />
                  <Route path="/fleet" element={<FleetManagement />} />
                  <Route path="/ports" element={<PortOperations />} />
                  <Route path="/market" element={<MarketIntelligence />} />
                  <Route path="/alerts" element={<Alerts />} />
                  <Route path="/cases" element={<Cases />} />
                  <Route path="/movements" element={<Movements />} />
                  <Route path="/users" element={<Users />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </Layout>
            </PrivateRoute>
          }
        />
      </Routes>
    </AuthProvider>
  )
}

export default App
