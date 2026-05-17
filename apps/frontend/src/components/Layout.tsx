import { Outlet, NavLink } from 'react-router-dom'
import './Layout.css'

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
        </div>
      </nav>

      <main className="sara-content">
        <Outlet />
      </main>
    </>
  )
}

export default Layout
