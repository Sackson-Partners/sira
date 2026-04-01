import React, { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth, AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import AuthLogin from './pages/auth/Login'
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

const Welcome = lazy(() => import('./pages/Welcome'))

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

// Shows the welcome map to unauthenticated visitors; sends logged-in users to /dashboard
function WelcomeOrDashboard() {
  const { isAuthenticated } = useAuth()
  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  return (
    <Suspense fallback={null}>
      <Welcome />
    </Suspense>
  )
}

function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public welcome map */}
        <Route path="/" element={<WelcomeOrDashboard />} />

        <Route path="/login" element={<AuthLogin />} />
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
