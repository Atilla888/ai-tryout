import { Outlet, NavLink } from 'react-router-dom'
import './Layout.css'

function Layout() {
  return (
    <>
      <nav className="app-nav">
        <NavLink to="/" className="app-brand">
          <div className="app-brand-text">
            <span className="app-brand-name">SARA</span>
            <span className="app-brand-sub">System for AI-Research &amp; Assessment</span>
          </div>
        </NavLink>

        <div className="app-nav-links">
          <NavLink to="/" end className={({ isActive }) => 'app-nav-link' + (isActive ? ' active' : '')}>
            Spaces
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => 'app-nav-link' + (isActive ? ' active' : '')}>
            History
          </NavLink>
        </div>
      </nav>

      <main className="app-content">
        <Outlet />
      </main>
    </>
  )
}

export default Layout
