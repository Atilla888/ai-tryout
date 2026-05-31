import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchMe, fetchMyHistory, type Job, type Me } from '../api/api'

function History() {
  const [me, setMe] = useState<Me | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchMe(), fetchMyHistory()])
      .then(([profile, history]) => {
        setMe(profile)
        setJobs(history)
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load'))
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
        <ul>
          {jobs.map((job) => (
            <li key={job.id}>
              <Link to={`/jobs/${job.id}`}>{job.id}</Link> — {job.status}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default History
