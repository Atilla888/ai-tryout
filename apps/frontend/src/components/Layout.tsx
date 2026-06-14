import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from 'react-oidc-context'
import './Layout.css'

function AuthControls() {
  const auth = useAuth()

  if (auth.isLoading) return <span className="sara-nav-link">…</span>

  if (auth.isAuthenticated) {
    const name = auth.user?.profile.preferred_username ?? auth.user?.profile.email ?? 'account'
    return (
      <>
        <span className="sara-nav-link">{name}</span>
        <button
          className="sara-nav-link"
          onClick={() => void auth.signoutRedirect()}
        >
          Sign out
        </button>
      </>
    )
  }

  return (
    <button className="sara-nav-link" onClick={() => void auth.signinRedirect()}>
      Sign in
    </button>
  )
}

function Layout() {
  return (
    <>
      <nav className="sara-nav">
        <NavLink to="/" className="sara-brand">
          <div className="sara-brand-text">
            <span className="sara-brand-name">SARA</span>
            <span className="sara-brand-sub">System for AI-Research &amp; Assessment</span>
          </div>
        </NavLink>

        <div className="sara-nav-links">
          <NavLink to="/" end className={({ isActive }) => 'sara-nav-link' + (isActive ? ' active' : '')}>
            Spaces
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => 'sara-nav-link' + (isActive ? ' active' : '')}>
            History
          </NavLink>
          <NavLink to="/creator" className={({ isActive }) => 'sara-nav-link' + (isActive ? ' active' : '')}>
            Creator
          </NavLink>
          <AuthControls />
        </div>
      </nav>

      <main className="sara-content">
        <Outlet />
      </main>
    </>
  )
}

export default Layout
