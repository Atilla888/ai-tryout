import { Link } from 'react-router-dom'
import { artifactDownloadUrl } from '../api/api'
import type { Artifact, Job } from '../api/api'

const RECENT_RUNS_LIMIT = 5
const SECONDS_PER_QUEUE_POSITION = 15

/** Converts a queue position to a rough human-readable time estimate. */
function formatEta(queuePosition: number): string {
  const seconds = queuePosition * SECONDS_PER_QUEUE_POSITION
  if (seconds < 60) return `~${seconds}s`
  return `~${Math.round(seconds / 60)}m`
}

/** Returns a status line and progress value for the sidebar queue-status card. */
function queueStatus(job: Job): { line: string; progress: number } {
  switch (job.status) {
    case 'QUEUED':
      return {
        line:
          job.queue_position != null
            ? `Position ${job.queue_position} in queue · ${formatEta(job.queue_position)} remaining`
            : 'Waiting in queue',
        progress: 0,
      }
    case 'STARTING':
      return { line: 'Starting your job...', progress: 0 }
    case 'RUNNING':
      return {
        line: job.progress_message || `Running · ${job.progress_percent}%`,
        progress: job.progress_percent,
      }
    case 'CANCELLING':
      return { line: 'Cancelling...', progress: job.progress_percent }
    default:
      return { line: job.status, progress: 0 }
  }
}

interface SpaceSidebarProps {
  isAuthenticated: boolean
  recentJobs: Job[]
  activeJob: Job | null
  canDownload: boolean
  downloadArtifact: Artifact | null
  linkCopied: boolean
  description: string | null
  onRunAgain: () => void
  onCopyShareLink: () => void
}

/** Right-hand sidebar of the space detail page: download/run-again actions,
 * live queue status, recent runs, and an "about" blurb. */
function SpaceSidebar({
  isAuthenticated,
  recentJobs,
  activeJob,
  canDownload,
  downloadArtifact,
  linkCopied,
  description,
  onRunAgain,
  onCopyShareLink,
}: SpaceSidebarProps) {
  return (
    <aside>
      {isAuthenticated && (
        <div className="sidebar-card sidebar-actions">
          <button
            type="button"
            className="action-download"
            onClick={() => canDownload && downloadArtifact && window.open(artifactDownloadUrl(downloadArtifact.id), '_blank')}
            disabled={!canDownload}
          >
            Download
          </button>
          <button type="button" className="action-retry" onClick={onRunAgain}>
            Run again
          </button>
          <Link className="action-link" to="/history">
            View in My History
          </Link>
          <button type="button" className="action-link" onClick={onCopyShareLink}>
            {linkCopied ? 'Link copied!' : 'Copy share link'}
          </button>
        </div>
      )}

      {activeJob && (
        <div className="sidebar-card status-card">
          <strong>Queue status</strong>
          <div className="status-line">{queueStatus(activeJob).line}</div>
          <div className="progress-bar">
            <span style={{ width: `${queueStatus(activeJob).progress}%` }} />
          </div>
        </div>
      )}

      {recentJobs.length > 0 && (
        <div className="sidebar-card sidebar-block">
          <h2>Recent runs</h2>
          <ul className="list-compact">
            {recentJobs.slice(0, RECENT_RUNS_LIMIT).map((job) => (
              <li key={job.id}>
                <Link to={`/jobs/${job.id}`} className="list-compact-link">
                  <span className="job-id">{job.id.slice(0, 8)}</span>
                  <span>{job.status.toLowerCase()}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="sidebar-card sidebar-block">
        <h2>About this space</h2>
        <div className="about-copy">
          {description ??
            'This space runs the selected AI model and returns output based on your chosen inputs.'}
        </div>
      </div>
    </aside>
  )
}

export default SpaceSidebar
