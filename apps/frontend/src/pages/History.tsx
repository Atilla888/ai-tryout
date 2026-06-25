import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteMyHistory, fetchMyHistory, type Job, type JobStatus } from '../api/api'
import './History.css'

const PAGE_SIZE = 10

const STATUS_LABELS: Record<JobStatus, string> = {
  QUEUED: 'Queued',
  STARTING: 'Starting',
  RUNNING: 'Running',
  SUCCEEDED: 'Succeeded',
  FAILED: 'Failed',
  CANCELLING: 'Cancelling',
  CANCELLED: 'Cancelled',
  EXPIRED: 'Expired',
}

const STATUS_CLASSES: Record<JobStatus, string> = {
  QUEUED: 'status-pill status-pending',
  STARTING: 'status-pill status-active',
  RUNNING: 'status-pill status-active',
  SUCCEEDED: 'status-pill status-success',
  FAILED: 'status-pill status-error',
  CANCELLING: 'status-pill status-warning',
  CANCELLED: 'status-pill status-muted',
  EXPIRED: 'status-pill status-muted',
}

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

function History() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)

  useEffect(() => {
    fetchMyHistory()
      .then((history) => {
        const sorted = history
          .slice()
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        setJobs(sorted)
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  const pageCount = Math.max(1, Math.ceil(jobs.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)

  const visibleJobs = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE
    return jobs.slice(start, start + PAGE_SIZE)
  }, [jobs, currentPage])

  async function handleDelete(jobId: string) {
    if (!window.confirm('Delete this history entry?')) return
    try {
      await deleteMyHistory(jobId)
      setJobs((prev) => prev.filter((j) => j.id !== jobId))
    } catch (e: unknown) {
      window.alert(e instanceof Error ? e.message : 'Failed to delete history entry')
    }
  }

  return (
    <div className="history-card">
      <div className="history-header">
        <span className="history-title">History</span>
      </div>
      <div className="history-intro">
        <p>Review your past jobs and jump back into their results.</p>
      </div>

      {loading && <div className="history-status-label">Loading history...</div>}

      {!loading && error && (
        <div className="history-status-label">Failed to load history: {error}</div>
      )}

      {!loading && !error && jobs.length === 0 && (
        <div className="history-empty">
          <p>You haven&apos;t run any jobs yet.</p>
          <Link className="btn-reset" to="/">
            Browse spaces
          </Link>
        </div>
      )}

      {!loading && !error && jobs.length > 0 && (
        <>
          <div className="history-status-label">
            {jobs.length} job{jobs.length !== 1 ? 's' : ''}
          </div>

          <ul className="history-list">
            {visibleJobs.map((job) => (
              <li key={job.id} className="history-row">
                <Link to={`/jobs/${job.id}`} className="history-link">
                  <div className="history-main">
                    <span className="history-space">{job.space_name ?? 'Unknown space'}</span>
                    <span className="history-date">{formatDate(job.created_at)}</span>
                  </div>
                  <span className={STATUS_CLASSES[job.status]}>{STATUS_LABELS[job.status]}</span>
                </Link>
                <button
                  type="button"
                  className="history-delete"
                  onClick={() => handleDelete(job.id)}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>

          {pageCount > 1 && (
            <div className="history-pagination">
              <button
                className="btn-secondary"
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                Previous
              </button>
              <span className="history-page-label">
                Page {currentPage} of {pageCount}
              </span>
              <button
                className="btn-secondary"
                type="button"
                onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                disabled={currentPage === pageCount}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default History
