import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from 'react-oidc-context'
import {
  artifactDownloadUrl,
  fetchJobArtifacts,
  fetchMyHistory,
  fetchSpace,
  submitJob,
} from '../api/api'
import type { Artifact, InputFieldConfig, Job, JobStatus, SpaceDetail } from '../api/api'
import './Spaces.css'

type FormValues = Record<string, string | File | null>
type FormErrors = Record<string, string>

const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
const AUDIO_TYPES = ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/webm']

const ACTIVE_JOB_STATUSES: JobStatus[] = ['QUEUED', 'STARTING', 'RUNNING', 'CANCELLING']
const RECENT_RUNS_LIMIT = 5
const HISTORY_POLL_MS = 3000
const SECONDS_PER_QUEUE_POSITION = 15

function formatEta(queuePosition: number): string {
  const seconds = queuePosition * SECONDS_PER_QUEUE_POSITION
  if (seconds < 60) return `~${seconds}s`
  return `~${Math.round(seconds / 60)}m`
}

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

function validateForm(inputs: InputFieldConfig[], values: FormValues): FormErrors {
  const errors: FormErrors = {}
  for (const field of inputs) {
    const val = values[field.name]
    const empty = val === null || val === undefined || val === ''
    if (field.required && empty) {
      errors[field.name] = `${field.label} is required`
      continue
    }
    if (!empty) {
      if (typeof val === 'string') {
        if (field.maxLength && val.length > field.maxLength)
          errors[field.name] = `Max ${field.maxLength} characters`
        if (field.type === 'number') {
          const n = parseFloat(val)
          if (!isNaN(n)) {
            if (field.min !== undefined && n < field.min) errors[field.name] = `Minimum is ${field.min}`
            if (field.max !== undefined && n > field.max) errors[field.name] = `Maximum is ${field.max}`
          }
        }
      }
      if (val instanceof File) {
        const allowed = field.type === 'image_upload' ? IMAGE_TYPES : AUDIO_TYPES
        if (!allowed.includes(val.type)) {
          errors[field.name] = `Invalid file type`
        } else if (field.max_size_mb && val.size > field.max_size_mb * 1024 * 1024) {
          errors[field.name] = `File too large. Max ${field.max_size_mb} MB`
        }
      }
    }
  }
  return errors
}

// --- DropZone ---

interface DropZoneProps {
  field: InputFieldConfig
  value: File | null
  hasError: boolean
  onChange: (file: File | null) => void
}

function DropZone({ field, value, hasError, onChange }: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const accept = field.type === 'image_upload' ? 'image/*' : 'audio/*'
  const allowed = field.type === 'image_upload' ? IMAGE_TYPES : AUDIO_TYPES

  const handleFile = (file: File | undefined) => {
    if (!file) return
    onChange(allowed.includes(file.type) ? file : null)
  }

  return (
    <div
      className={'drop-zone' + (dragging ? ' dragover' : '') + (hasError ? ' input-error' : '')}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <strong>{value ? value.name : 'Drop file or click to upload'}</strong>
      <span className="drop-note">
        Accepted: {field.mime_types?.join(', ') || accept} · Max {field.max_size_mb ?? 10} MB
      </span>
    </div>
  )
}

// --- Field ---

interface FieldProps {
  config: InputFieldConfig
  value: string | File | null
  error?: string
  onChange: (name: string, val: string | File | null) => void
}

function Field({ config, value, error, onChange }: FieldProps) {
  const { name, type, label, description, required, placeholder, maxLength, min, max, options } = config
  const hasError = !!error

  const renderControl = () => {
    switch (type) {
      case 'text':
        return (
          <input
            type="text"
            id={name}
            className={hasError ? 'input-error' : ''}
            placeholder={placeholder}
            maxLength={maxLength}
            value={(value as string) ?? ''}
            onChange={(e) => onChange(name, e.target.value)}
          />
        )
      case 'textarea':
        return (
          <textarea
            id={name}
            className={hasError ? 'input-error' : ''}
            placeholder={placeholder}
            maxLength={maxLength}
            value={(value as string) ?? ''}
            onChange={(e) => onChange(name, e.target.value)}
          />
        )
      case 'number':
        return (
          <input
            type="number"
            id={name}
            className={hasError ? 'input-error' : ''}
            placeholder={placeholder}
            min={min}
            max={max}
            value={(value as string) ?? ''}
            onChange={(e) => onChange(name, e.target.value)}
          />
        )
      case 'select':
        return (
          <select
            id={name}
            className={hasError ? 'input-error' : ''}
            value={(value as string) ?? ''}
            onChange={(e) => onChange(name, e.target.value)}
          >
            <option value="">{placeholder ?? 'Select an option'}</option>
            {(options ?? []).map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        )
      case 'image_upload':
      case 'audio_upload':
        return (
          <DropZone
            field={config}
            value={value as File | null}
            hasError={hasError}
            onChange={(file) => onChange(name, file)}
          />
        )
      default:
        console.warn(`Unsupported input type: "${type}". Rendering fallback text input.`)
        return (
          <input
            type="text"
            id={name}
            placeholder={placeholder}
            value={(value as string) ?? ''}
            onChange={(e) => onChange(name, e.target.value)}
          />
        )
    }
  }

  return (
    <div className="form-row">
      <label htmlFor={name}>
        {label}
        {required && <span className="required-indicator">*</span>}
      </label>
      {description && <div className="form-description">{description}</div>}
      {renderControl()}
      {error && <div className="field-error">{error}</div>}
    </div>
  )
}

// --- Main page ---

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
              <Field
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

        <aside>
          {auth.isAuthenticated && (
            <div className="sidebar-card sidebar-actions">
              <button
                type="button"
                className="action-download"
                onClick={() => canDownload && window.open(artifactDownloadUrl(downloadArtifact.id), '_blank')}
                disabled={!canDownload}
              >
                Download
              </button>
              <button type="button" className="action-retry" onClick={handleRunAgain}>
                Run again
              </button>
              <Link className="action-link" to="/history">
                View in My History
              </Link>
              <button type="button" className="action-link" onClick={handleCopyShareLink}>
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
              {space.description ??
                'This space runs the selected AI model and returns output based on your chosen inputs.'}
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

export default Spaces
