import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from 'react-oidc-context'
import { fetchJobArtifacts, fetchMyHistory, fetchSpace, submitJob } from '../api/api'
import type { Artifact, Job, JobStatus, SpaceDetail } from '../api/api'
import SpaceInputField from '../components/SpaceInputField'
import SpaceSidebar from '../components/SpaceSidebar'
import { validateForm, type FormErrors, type FormValues } from '../components/spaceForm'
import './Spaces.css'

const ACTIVE_JOB_STATUSES: JobStatus[] = ['QUEUED', 'STARTING', 'RUNNING', 'CANCELLING']
const HISTORY_POLL_MS = 3000

/** Space detail page — shows the submission form and a sidebar with queue status and recent runs.
 * Recent jobs are polled while any of them is in an active state. */
function Spaces() {
  const { spaceId } = useParams<{ spaceId: string }>()
  const navigate = useNavigate()
  const auth = useAuth()

  const [space, setSpace] = useState<SpaceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState(false)
  const [values, setValues] = useState<FormValues>({})
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [recentJobs, setRecentJobs] = useState<Job[]>([])
  const [downloadArtifact, setDownloadArtifact] = useState<Artifact | null>(null)
  const [linkCopied, setLinkCopied] = useState(false)

  useEffect(() => {
    if (!spaceId) return
    fetchSpace(spaceId)
      .then((data) => {
        setSpace(data)
        const initial: FormValues = {}
        for (const input of data.ui_config?.inputs ?? []) initial[input.name] = null
        setValues(initial)
      })
      .catch(() => setFetchError(true))
      .finally(() => setLoading(false))
  }, [spaceId])

  useEffect(() => {
    if (!space || !auth.isAuthenticated) return

    let cancelled = false
    let timer: ReturnType<typeof setInterval> | undefined

    const loadRecentJobs = async () => {
      try {
        const history = await fetchMyHistory()
        if (cancelled) return
        const forSpace = history
          .filter((job) => job.space_id === space.id)
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        setRecentJobs(forSpace)

        const isActive = ACTIVE_JOB_STATUSES.includes(forSpace[0]?.status)
        if (isActive && !timer) {
          timer = setInterval(loadRecentJobs, HISTORY_POLL_MS)
        } else if (!isActive && timer) {
          clearInterval(timer)
          timer = undefined
        }
      } catch {
        // Recent runs / queue status are best-effort sidebar content.
      }
    }

    loadRecentJobs()

    return () => {
      cancelled = true
      if (timer) clearInterval(timer)
    }
  }, [space, auth.isAuthenticated])

  useEffect(() => {
    const latest = recentJobs[0]
    if (!latest || latest.status !== 'SUCCEEDED') return

    let cancelled = false
    fetchJobArtifacts(latest.id)
      .then((artifacts) => {
        if (!cancelled) setDownloadArtifact(artifacts.find((a) => a.artifact_type !== 'INPUT') ?? null)
      })
      .catch(() => {
        if (!cancelled) setDownloadArtifact(null)
      })

    return () => {
      cancelled = true
    }
  }, [recentJobs])

  const handleChange = (name: string, val: string | File | null) => {
    setValues((prev) => ({ ...prev, [name]: val }))
    setErrors((prev) => ({ ...prev, [name]: '' }))
  }

  const handleSubmit = async () => {
    if (!space) return
    const inputs = space.ui_config?.inputs ?? []
    const validationErrors = validateForm(inputs, values)
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }
    setSubmitting(true)
    try {
      const payload = new FormData()
      for (const input of inputs) {
        const val = values[input.name]
        if (val instanceof File) {
          payload.append(input.name, val)
        } else if (val !== null && val !== undefined && val !== '') {
          payload.append(input.name, val as string)
        }
      }
      const result = await submitJob(space.id, payload)
      navigate(`/jobs/${result.id}`)
    } catch {
      alert('Failed to submit job. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="detail-state">Loading...</div>
  if (fetchError || !space) return <div className="detail-state">Failed to load space.</div>

  const inputs = space.ui_config?.inputs ?? []

  const handleRunAgain = () => {
    const initial: FormValues = {}
    for (const input of inputs) initial[input.name] = null
    setValues(initial)
    setErrors({})
  }

  const handleCopyShareLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setLinkCopied(true)
      setTimeout(() => setLinkCopied(false), 2000)
    } catch {
      alert('Could not copy link')
    }
  }

  const latestJob = recentJobs[0]
  const activeJob = latestJob && ACTIVE_JOB_STATUSES.includes(latestJob.status) ? latestJob : null
  const canDownload =
    latestJob?.status === 'SUCCEEDED' && downloadArtifact != null && downloadArtifact.job_id === latestJob.id

  return (
    <div>
      <div className="breadcrumbs">
        <Link to="/">Spaces</Link>
        <span>{space.name}</span>
      </div>

      <div className="space-top">
        <div className="space-header">
          <div className="space-heading">{space.name}</div>
          <div className="space-owner">{space.task_type.toLowerCase()} generation</div>
          {space.description && <div className="space-subtle">{space.description}</div>}
          <div className="space-meta">
            <span className="meta-pill">{space.task_type}</span>
            {(space.input_types as string[]).map((t) => (
              <span key={`in-${t}`} className="meta-pill">{t} in</span>
            ))}
            {(space.output_types as string[]).map((t) => (
              <span key={`out-${t}`} className="meta-pill">{t} out</span>
            ))}
          </div>
        </div>
      </div>

      <div className="page-grid">
        <div className="panel">
          <h2>Inputs</h2>
          {inputs.length === 0 ? (
            <p className="no-inputs">No input fields configured.</p>
          ) : (
            inputs.map((input) => (
              <SpaceInputField
                key={input.name}
                config={input}
                value={values[input.name] ?? null}
                error={errors[input.name]}
                onChange={handleChange}
              />
            ))
          )}
          <div className="button-row">
            <button className="btn-secondary" onClick={() => navigate('/')}>
              Cancel
            </button>
            <button className="btn-primary" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Submitting…' : 'Submit'}
            </button>
          </div>
        </div>

        <SpaceSidebar
          isAuthenticated={auth.isAuthenticated}
          recentJobs={recentJobs}
          activeJob={activeJob}
          canDownload={canDownload}
          downloadArtifact={downloadArtifact}
          linkCopied={linkCopied}
          description={space.description}
          onRunAgain={handleRunAgain}
          onCopyShareLink={handleCopyShareLink}
        />
      </div>
    </div>
  )
}

export default Spaces
