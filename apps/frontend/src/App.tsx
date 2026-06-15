import { useEffect, type ReactNode } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useAuth } from 'react-oidc-context'
import Layout from './components/Layout'
import Home from './pages/Home'
import Spaces from './pages/Spaces'
import JobDetail from './pages/JobDetail'
import History from './pages/History'
import CreatorDashboard from './pages/CreatorDashboard'
import SpaceEditor from './pages/SpaceEditor'
import AdminDashboard from './pages/AdminDashboard'
import { setAccessToken } from './api/api'

/** Keeps the module-level API token in sync with the OIDC session.
 * Renders nothing — exists only for its side-effect via useEffect. */
function TokenSync() {
  const auth = useAuth()
  useEffect(() => {
    setAccessToken(auth.isAuthenticated ? (auth.user?.access_token ?? null) : null)
  }, [auth.isAuthenticated, auth.user])
  return null
}

/** Wraps protected routes — redirects to the OIDC login page if not authenticated. */
function RequireAuth({ children }: { children: ReactNode }) {
  const auth = useAuth()
  useEffect(() => {
    if (!auth.isLoading && !auth.isAuthenticated) {
      void auth.signinRedirect()
    }
  }, [auth.isLoading, auth.isAuthenticated, auth])

  if (auth.isLoading) return <p style={{ padding: 24 }}>Loading…</p>
  if (!auth.isAuthenticated) return <p style={{ padding: 24 }}>Redirecting to sign in…</p>
  return <>{children}</>
}

function App() {
  return (
    <BrowserRouter>
      <TokenSync />
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="spaces/:spaceId" element={<Spaces />} />
          <Route path="jobs/:jobId" element={<JobDetail />} />
          <Route
            path="history"
            element={
              <RequireAuth>
                <History />
              </RequireAuth>
            }
          />
          <Route
            path="creator"
            element={
              <RequireAuth>
                <CreatorDashboard />
              </RequireAuth>
            }
          />
          <Route
            path="creator/spaces/new"
            element={
              <RequireAuth>
                <SpaceEditor />
              </RequireAuth>
            }
          />
          <Route
            path="creator/spaces/:spaceId/edit"
            element={
              <RequireAuth>
                <SpaceEditor />
              </RequireAuth>
            }
          />
          <Route
            path="admin"
            element={
              <RequireAuth>
                <AdminDashboard />
              </RequireAuth>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App