import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchMe,
  fetchMyHistory,
  fetchSpace,
  deleteMyHistory,
  type Job,
  type Me,
  type SpaceDetail,
} from '../api/api'

function badgeForStatus(status: string) {
  if (status === 'EXPIRED') return <span style={{ color: 'white', background: 'crimson', padding: '2px 6px', borderRadius: 4 }}>Expired</span>
  return <span style={{ color: 'white', background: '#666', padding: '2px 6px', borderRadius: 4 }}>{status}</span>
}

function formatTs(ts: string | null) {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleString()
  } catch {
    return ts
  }
}

function History() {
  const [me, setMe] = useState<Me | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [spaces, setSpaces] = useState<Map<string, SpaceDetail>>(new Map())
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const [profile, history] = await Promise.all([fetchMe(), fetchMyHistory()])
        if (!mounted) return
        // sort reverse chronological by created_at
        const sorted = history.slice().sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        setMe(profile)
        setJobs(sorted)

        // fetch distinct spaces
        const ids = Array.from(new Set(sorted.map((j) => j.space_id).filter(Boolean)))
        const map = new Map<string, SpaceDetail>()
        await Promise.all(
          ids.map(async (id) => {
            try {
              const s = await fetchSpace(id)
              map.set(id, s)
            } catch {
              // ignore individual failures
            }
          }),
        )
        if (!mounted) return
        setSpaces(map)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load')
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  if (error) return <p style={{ color: 'crimson' }}>{error}</p>

  return (
    <div>
      <h1>History</h1>
      {me && (
        <p>
          Signed in as <strong>{me.email}</strong> (role: {me.role})
        </p>
      )}

      {jobs.length === 0 ? (
        <p>No jobs yet.</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {jobs.map((job) => {
            const space = spaces.get(job.space_id)
            const spaceName = space ? space.name : job.space_id
            const isExpired = job.status === 'EXPIRED'
            return (
              <li key={job.id} style={{ padding: '8px 0', borderBottom: '1px solid #eee' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div>
                      <strong>{spaceName}</strong>
                      {' '}
                      {badgeForStatus(job.status)}
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>
                      Created: {formatTs(job.created_at)} — Expires: {formatTs(job.expires_at)}
                    </div>
                  </div>

                  <div>
                    {job.status === 'SUCCEEDED' && !isExpired ? (
                      <Link to={`/jobs/${job.id}`} style={{ marginRight: 12 }}>View</Link>
                    ) : (
                      <span style={{ marginRight: 12 }}>{job.id}</span>
                    )}

                    <button
                      type="button"
                      onClick={async () => {
                        if (!confirm('Delete this history entry?')) return
                        try {
                          await deleteMyHistory(job.id)
                          setJobs((prev) => prev.filter((j) => j.id !== job.id))
                        } catch (e: unknown) {
                          alert(e instanceof Error ? e.message : 'Failed to delete')
                        }
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

export default History
