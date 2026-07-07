import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  cancelJob,
  fetchJob,
  fetchJobArtifacts,
  type Artifact,
  type Job,
} from '../api/api'
import ArtifactViewer from '../components/ArtifactViewer'
import './JobDetail.css'

const POLL_MS = 2000

/** Returns true for terminal job states so the polling interval can be cleared. */
function jobIsFinished(status: string) {
  return (
    status === 'SUCCEEDED' ||
    status === 'FAILED' ||
    status === 'CANCELLED' ||
    status === 'EXPIRED'
  )
}

function getMessage(job: Job) {
  if (job.status === 'QUEUED' && job.queue_position != null) {
    return `Position ${job.queue_position} in queue`
  }
  if (job.status === 'STARTING') {
    return 'Starting your job...'
  }
  if (job.status === 'RUNNING') {
    return job.progress_message || 'Processing...'
  }
  if (job.status === 'SUCCEEDED') {
    return 'Your result is ready'
  }
  if (job.status === 'FAILED') {
    return job.error_message || 'Job failed'
  }
  if (job.status === 'CANCELLED') {
    return 'Job was cancelled'
  }
  if (job.status === 'CANCELLING') {
    return 'Cancelling...'
  }
  if (job.status === 'EXPIRED') {
    return 'Job expired'
  }
  return job.status
}

/** Polls the job status every 2 s until it reaches a terminal state, then loads artifacts.
 * Sends a browser notification when the job transitions to SUCCEEDED or FAILED. */
function JobDetail() {
  const { jobId } = useParams()
  const [job, setJob] = useState<Job | null>(null)
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const prevStatusRef = useRef('')
  const timerRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined)

  useEffect(() => {
    if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }, [])

  useEffect(() => {
    if (!jobId) return

    async function update() {
      if (!jobId) return
      try {
        const data = await fetchJob(jobId)
        setJob(data)
        setError('')

        if (prevStatusRef.current && prevStatusRef.current !== data.status) {
          if (data.status === 'SUCCEEDED' && Notification.permission === 'granted') {
            new Notification('Job complete', { body: 'Your result is ready.' })
          }
          if (data.status === 'FAILED' && Notification.permission === 'granted') {
            new Notification('Job failed', { body: data.error_message || 'Job failed' })
          }
        }
        prevStatusRef.current = data.status

        if (data.status === 'SUCCEEDED') {
          const list = await fetchJobArtifacts(jobId)
          const outputs = list.filter(
            (a) => a.artifact_type !== 'INPUT',
          )
          setArtifacts(outputs)
        }

        if (jobIsFinished(data.status) && timerRef.current) {
          clearInterval(timerRef.current)
        }
      } catch {
        setError('Failed to load job')
      } finally {
        setLoading(false)
      }
    }

    update()
    timerRef.current = setInterval(update, POLL_MS)

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [jobId])

  async function handleCancel() {
    if (!jobId) return
    try {
      const updated = await cancelJob(jobId)
      setJob(updated)
    } catch {
      alert('Could not cancel job')
    }
  }

  if (!jobId) {
    return <p>Missing job id</p>
  }

  if (loading && !job) {
    return <p>Loading...</p>
  }

  if (error && !job) {
    return <p>{error}</p>
  }

  if (!job) {
    return <p>Job not found</p>
  }

  const canCancel = job.status === 'QUEUED' || job.status === 'RUNNING'

  return (
    <div className="job-page">
      <p>
        <Link to="/">Back to spaces</Link>
      </p>

      <h1>Job status</h1>
      <p>
        <strong>Status:</strong> {job.status}
      </p>
      <p>{getMessage(job)}</p>

      {job.status === 'QUEUED' && job.queue_position != null && (
        <p>Queue position: {job.queue_position}</p>
      )}

      {job.status === 'RUNNING' && (
        <div>
          <p>Progress: {job.progress_percent}%</p>
          <progress value={job.progress_percent} max={100} />
          {job.progress_message && <p>{job.progress_message}</p>}
        </div>
      )}

      {job.status === 'FAILED' && (
        <p className="error-text">
          {job.error_message}
          {job.error_code && ` (${job.error_code})`}
        </p>
      )}

      {canCancel && (
        <button type="button" onClick={handleCancel}>
          Cancel job
        </button>
      )}

      <p className="small-text">Job id: {job.id}</p>
      <p className="small-text">Submitted by: User #{job.user_number}</p>

      {job.status === 'SUCCEEDED' && (
        <div className="results">
          <h2>Results</h2>
          {artifacts.length === 0 && <p>No files to show yet.</p>}
          {artifacts.map((artifact) => (
            <ArtifactViewer key={artifact.id} artifact={artifact} />
          ))}
        </div>
      )}
    </div>
  )
}

export default JobDetail
