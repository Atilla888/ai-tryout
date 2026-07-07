import { useEffect, useState } from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from 'react-oidc-context'
import { fetchMe, type Me } from '../api/api'
import './Layout.css'

function AuthControls() {
  const auth = useAuth()
  const [me, setMe] = useState<Me | null>(null)

  // Load the backend profile so we can show the user's own running number.
  useEffect(() => {
    if (!auth.isAuthenticated) return
    let cancelled = false
    fetchMe()
      .then((data) => { if (!cancelled) setMe(data) })
      .catch(() => { if (!cancelled) setMe(null) })
    return () => { cancelled = true }
  }, [auth.isAuthenticated])

  if (auth.isLoading) return <span className="sara-user">…</span>

  if (auth.isAuthenticated) {
    const name = auth.user?.profile.preferred_username ?? auth.user?.profile.email ?? 'account'
    return (
      <>
        <span className="sara-user">
          {name}
          {me && <span className="sara-user-id"> · User #{me.user_number}</span>}
        </span>
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
    <button className="sara-cta" onClick={() => void auth.signinRedirect()}>
      Sign in
    </button>
  )
}

function Layout() {
  return (
    <>
      <nav className="sara-nav">
        <NavLink to="/" className="sara-brand">
          <span className="sara-logo" aria-hidden="true">S</span>
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
          <NavLink to="/admin" className={({ isActive }) => 'sara-nav-link' + (isActive ? ' active' : '')}>
            Admin
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
