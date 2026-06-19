import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import PublicHeader from './components/Layout/PublicHeader'
import Sidebar from './components/Layout/Sidebar'

import HomePage from './pages/public/HomePage'
import VerifyPage from './pages/public/VerifyPage'
import FactsPage from './pages/public/FactsPage'
import FactDetailPage from './pages/public/FactDetailPage'
import ThreadsPage from './pages/public/ThreadsPage'
import ThreadDetailPage from './pages/public/ThreadDetailPage'
import EntitiesPage from './pages/public/EntitiesPage'
import EntityDetailPage from './pages/public/EntityDetailPage'
import ObservatoireAdmin from './pages/admin/ObservatoireAdmin'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import VerifyTokenPage from './pages/auth/VerifyTokenPage'
import DashboardPage from './pages/citizen/DashboardPage'
import ProfilePage from './pages/citizen/ProfilePage'
import AlertsPage from './pages/citizen/AlertsPage'
import ConsultationsPage from './pages/citizen/ConsultationsPage'
import AmbassadorApplyPage from './pages/citizen/AmbassadorApplyPage'
import AmbassadorLandingPage from './pages/citizen/AmbassadorLandingPage'
import ConsultationDetailPage from './pages/citizen/ConsultationDetailPage'
import CollectePage from './pages/citizen/CollectePage'
import AdminDashboard from './pages/admin/AdminDashboard'
import UsersAdmin from './pages/admin/UsersAdmin'
import ConsultationsAdmin from './pages/admin/ConsultationsAdmin'
import AlertsAdmin from './pages/admin/AlertsAdmin'
import AIAdmin from './pages/admin/AIAdmin'
import AmbassadorsAdmin from './pages/admin/AmbassadorsAdmin'
import SettingsAdmin from './pages/admin/SettingsAdmin'
import AlertesPage from './pages/public/AlertesPage'
import PrivacyPage from './pages/public/PrivacyPage'
import LegalPage from './pages/public/LegalPage'
import CookieBanner from './components/shared/CookieBanner'
import { usePageTracking } from './hooks/usePageTracking'

function PrivateRoute({ children, roles }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" />
  if (roles && !roles.includes(user.role)) return <Navigate to="/dashboard" />
  return children
}

function PublicLayout({ children }) {
  return (
    <>
      <PublicHeader />
      {children}
    </>
  )
}

function AppLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-gov-bg">
      <Sidebar />
      {children}
    </div>
  )
}

function AppRoutes() {
  const { user } = useAuth()
  const location = useLocation()
  usePageTracking()

  const isAppRoute = location.pathname.startsWith('/dashboard') || location.pathname.startsWith('/admin')

  return (
    <Routes>
      {/* Pages publiques */}
      <Route path="/" element={<PublicLayout><HomePage /></PublicLayout>} />
      <Route path="/civitech" element={<PublicLayout><HomePage /></PublicLayout>} />
      <Route path="/verifier" element={<PublicLayout><VerifyPage /></PublicLayout>} />
      <Route path="/faits" element={<PublicLayout><FactsPage /></PublicLayout>} />
      <Route path="/faits/:slug" element={<PublicLayout><FactDetailPage /></PublicLayout>} />
      <Route path="/threads" element={<PublicLayout><ThreadsPage /></PublicLayout>} />
      <Route path="/threads/:slug" element={<PublicLayout><ThreadDetailPage /></PublicLayout>} />
      <Route path="/entites" element={<PublicLayout><EntitiesPage /></PublicLayout>} />
      <Route path="/entites/:slug" element={<PublicLayout><EntityDetailPage /></PublicLayout>} />
      <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <LoginPage />} />
      <Route path="/register" element={user ? <Navigate to="/dashboard" /> : <RegisterPage />} />
      <Route path="/auth/verify" element={<VerifyTokenPage />} />
      <Route path="/alertes" element={<PublicLayout><AlertesPage /></PublicLayout>} />
      <Route path="/confidentialite" element={<PublicLayout><PrivacyPage /></PublicLayout>} />
      <Route path="/mentions-legales" element={<PublicLayout><LegalPage /></PublicLayout>} />

      {/* Dashboard citoyen */}
      <Route path="/dashboard" element={
        <PrivateRoute>
          <AppLayout><DashboardPage /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/dashboard/profil" element={
        <PrivateRoute>
          <AppLayout><ProfilePage /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/dashboard/consultations" element={
        <PrivateRoute>
          <AppLayout><ConsultationsPage /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/dashboard/alertes" element={
        <PrivateRoute>
          <AppLayout><AlertsPage /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/dashboard/ambassador" element={
        <PrivateRoute>
          <AppLayout><AmbassadorLandingPage /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/dashboard/ambassador/postuler" element={
        <PrivateRoute>
          <AppLayout><AmbassadorApplyPage /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/dashboard/consultations/:id" element={
        <PrivateRoute>
          <AppLayout><ConsultationDetailPage /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/dashboard/collecte" element={
        <PrivateRoute roles={['superadmin', 'admin', 'moderator', 'z_ambassador']}>
          <AppLayout><CollectePage /></AppLayout>
        </PrivateRoute>
      } />

      {/* Admin / Moderator */}
      <Route path="/admin" element={
        <PrivateRoute roles={['superadmin', 'admin', 'moderator']}>
          <AppLayout><AdminDashboard /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/admin/utilisateurs" element={
        <PrivateRoute roles={['superadmin', 'admin', 'moderator']}>
          <AppLayout><UsersAdmin /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/admin/consultations" element={
        <PrivateRoute roles={['superadmin', 'admin', 'moderator']}>
          <AppLayout><ConsultationsAdmin /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/admin/alertes" element={
        <PrivateRoute roles={['superadmin', 'admin', 'moderator']}>
          <AppLayout><AlertsAdmin /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/admin/observatoire" element={
        <PrivateRoute roles={['superadmin', 'admin', 'moderator']}>
          <AppLayout><ObservatoireAdmin /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/admin/ambassadors" element={
        <PrivateRoute roles={['superadmin', 'admin', 'moderator']}>
          <AppLayout><AmbassadorsAdmin /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/admin/ia" element={
        <PrivateRoute roles={['superadmin', 'admin']}>
          <AppLayout><AIAdmin /></AppLayout>
        </PrivateRoute>
      } />
      <Route path="/admin/parametres" element={
        <PrivateRoute roles={['superadmin', 'admin']}>
          <AppLayout><SettingsAdmin /></AppLayout>
        </PrivateRoute>
      } />

      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <CookieBanner />
      </AuthProvider>
    </BrowserRouter>
  )
}
