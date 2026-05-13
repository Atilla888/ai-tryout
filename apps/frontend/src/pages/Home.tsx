import { useEffect, useMemo, useState } from 'react'
import { fetchSpaces, type Space } from '../api/api'
import SpaceCard from '../components/SpaceCard'
import './Home.css'

const FILTERS = ['All', 'Audio', 'Video', '3D', 'Image', 'Text']

function SkeletonCard() {
  return (
    <div className="skeleton-card" aria-hidden="true">
      <div className="skeleton-line short" />
      <div className="skeleton-line" />
      <div className="skeleton-line" />
      <div className="skeleton-line short" />
    </div>
  )
}

function Home() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [query, setQuery] = useState('')
  const [activeFilter, setActiveFilter] = useState('All')

  useEffect(() => {
    fetchSpaces()
      .then(setSpaces)
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    return spaces.filter((s) => {
      const matchesFilter = activeFilter === 'All' || s.task_type === activeFilter
      const q = query.toLowerCase()
      const matchesQuery =
        !q ||
        s.name.toLowerCase().includes(q) ||
        (s.description ?? '').toLowerCase().includes(q) ||
        s.task_type.toLowerCase().includes(q)
      return matchesFilter && matchesQuery
    })
  }, [spaces, query, activeFilter])

  return (
    <div className="sara-section-card">
      <div className="sara-section-header">
        <span className="sara-section-title">Spaces</span>
      </div>
      <div className="sara-hero">
        <p>
          Browse the available AI spaces. Select a space to open the job interface, review input
          options and monitor queue status.
        </p>
      </div>

      <div className="search-filter-bar">
        <input
          className="sara-search"
          type="text"
          placeholder="Search spaces..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="chips">
          {FILTERS.map((f) => (
            <span
              key={f}
              className={'chip' + (f === activeFilter ? ' on' : '')}
              onClick={() => setActiveFilter(f)}
            >
              {f}
            </span>
          ))}
        </div>
      </div>

      {loading && (
        <>
          <div className="count-label">Loading spaces...</div>
          <div className="spaces-grid">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        </>
      )}

      {!loading && error && (
        <>
          <div className="count-label">Unable to load spaces.</div>
          <div className="spaces-grid">
            <div className="empty-state">
              <p>API nicht erreichbar. Stelle sicher, dass der Backend-Server läuft.</p>
              <button className="btn-reset" onClick={() => window.location.reload()}>
                Retry
              </button>
            </div>
          </div>
        </>
      )}

      {!loading && !error && (
        <>
          <div className="count-label">
            {filtered.length} space{filtered.length !== 1 ? 's' : ''} available
          </div>
          <div className="spaces-grid">
            {filtered.length === 0 ? (
              <div className="empty-state">
                <p>No spaces match the current filter or search.</p>
                <button
                  className="btn-reset"
                  onClick={() => {
                    setQuery('')
                    setActiveFilter('All')
                  }}
                >
                  Clear filters
                </button>
              </div>
            ) : (
              filtered.map((space) => <SpaceCard key={space.id} space={space} />)
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default Home
