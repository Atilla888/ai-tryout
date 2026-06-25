import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchMySpaces, type CreatorSpace } from '../api/api'
import './CreatorDashboard.css'

function StatusBadge({ status }: { status: string }) {
  return <span className={`creator-status-badge creator-status-${status.toLowerCase()}`}>{status}</span>
}

function CreatorDashboard() {
  const [spaces, setSpaces] = useState<CreatorSpace[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchMySpaces()
      .then(setSpaces)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load spaces'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="creator-page">
      <div className="creator-dash-header">
        <div>
          <h1 className="creator-dash-title">My Spaces</h1>
          <p className="creator-dash-sub">Create and manage your AI spaces</p>
        </div>
        <button className="btn-creator-primary" onClick={() => navigate('/creator/spaces/new')}>
          + New Space
        </button>
      </div>

      {loading && <p className="creator-loading">Loading…</p>}

      {!loading && error && (
        <div className="creator-error-box">
          <strong>Could not load spaces.</strong> {error}
        </div>
      )}

      {!loading && !error && spaces.length === 0 && (
        <div className="creator-empty">
          <p>You haven't created any spaces yet.</p>
          <button className="btn-creator-primary" onClick={() => navigate('/creator/spaces/new')}>
            Create your first space
          </button>
        </div>
      )}

      {!loading && !error && spaces.length > 0 && (
        <div className="creator-space-list">
          {spaces.map((space) => (
            <div key={space.id} className="creator-space-row">
              <div className="creator-space-info">
                <span className="creator-space-name">{space.name}</span>
                <span className="creator-space-slug">/{space.slug}</span>
                {space.description && (
                  <p className="creator-space-desc">{space.description}</p>
                )}
              </div>
              <div className="creator-space-badges">
                <StatusBadge status={space.status} />
                <span className={`creator-vis-badge creator-vis-${space.visibility.toLowerCase()}`}>
                  {space.visibility}
                </span>
              </div>
              <Link to={`/creator/spaces/${space.id}/edit`} className="btn-creator-secondary">
                Edit
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default CreatorDashboard
