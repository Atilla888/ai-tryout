import { Outlet, Link } from 'react-router-dom'

function Layout() {
  return (
    <>
      <nav>
        <Link to="/">Home</Link>
        <Link to="/history">History</Link>
      </nav>
      <main>
        <Outlet />
      </main>
    </>
  )
}

export default Layout