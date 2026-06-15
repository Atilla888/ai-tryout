const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/** Module-level token store — updated by App.tsx whenever the OIDC session changes. */
let accessToken: string | null = null

/** Stores the current access token so it can be injected into API requests. */
export function setAccessToken(token: string | null) {
  accessToken = token
}

/** Returns Authorization header if logged in, or an empty object for public endpoints. */
function authHeaders(): Record<string, string> {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {}
}

export type SpaceVisibility = 'public' | 'private'
export type SpaceStatus = 'draft' | 'published' | 'disabled'

export type JobStatus =
  | 'QUEUED'
  | 'STARTING'
  | 'RUNNING'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'CANCELLING'
  | 'CANCELLED'
  | 'EXPIRED'

export interface Space {
  id: string
  name: string
  slug: string
  description: string | null
  task_type: string
  input_types: unknown[]
  output_types: unknown[]
  status: SpaceStatus
  visibility: SpaceVisibility
}

export interface InputOption {
  value: string
  label: string
}

export interface InputFieldConfig {
  name: string
  type: string
  label: string
  description?: string
  required?: boolean
  placeholder?: string
  maxLength?: number
  min?: number
  max?: number
  options?: InputOption[]
  mime_types?: string[]
  max_size_mb?: number
}

export interface SpaceDetail extends Space {
  owner_id: string | null
  container_image: string | null
  resource_requirements: Record<string, unknown>
  ui_config: { inputs: InputFieldConfig[] }
  runner_config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface Job {
  id: string
  space_id: string
  space_name: string | null
  user_id: string
  status: JobStatus
  queue_position: number | null
  progress_percent: number
  progress_message: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  cancelled_at: string | null
  expires_at: string | null
  error_code: string | null
  error_message: string | null
}

export interface JobSubmitResponse {
  id: string
  status: JobStatus
  queue_position: number | null
}

export interface Artifact {
  id: string
  artifact_type: string
  file_name: string
  content_type: string
  size_bytes: number
  storage_path: string
  preview_supported: boolean
  created_at: string
  expires_at: string | null
  job_id: string
}

export interface Me {
  id: string
  subject_id: string
  idp: string
  email: string
  display_name: string | null
  role: string
  created_at: string
}

/** Returns the URL for inline preview of an artifact (image/audio/text). */
export function artifactPreviewUrl(artifactId: string): string {
  return `${BASE_URL}/artifacts/${artifactId}/preview`
}

/** Returns the URL that triggers a file download (Content-Disposition: attachment). */
export function artifactDownloadUrl(artifactId: string): string {
  return `${BASE_URL}/artifacts/${artifactId}/download`
}

/** Fetches the list of all publicly visible spaces. No auth required. */
export async function fetchSpaces(): Promise<Space[]> {
  const res = await fetch(`${BASE_URL}/spaces`)
  if (!res.ok) throw new Error(`Failed to fetch spaces: ${res.status}`)
  return res.json() as Promise<Space[]>
}

/** Fetches full detail for a single space including its UI and runner config. */
export async function fetchSpace(id: string): Promise<SpaceDetail> {
  const res = await fetch(`${BASE_URL}/spaces/${id}`)
  if (!res.ok) throw new Error(`Failed to fetch space: ${res.status}`)
  return res.json() as Promise<SpaceDetail>
}

/** Submits a job as multipart/form-data (text fields + optional file uploads). */
export async function submitJob(spaceId: string, payload: FormData): Promise<JobSubmitResponse> {
  const res = await fetch(`${BASE_URL}/spaces/${spaceId}/jobs`, {
    method: 'POST',
    headers: authHeaders(),
    body: payload,
  })
  if (!res.ok) throw new Error(`Submit failed: ${res.status}`)
  return res.json() as Promise<JobSubmitResponse>
}

/** Fetches the current state of a job (status, progress, queue position). */
export async function fetchJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}`)
  if (!res.ok) throw new Error(`Failed to fetch job: ${res.status}`)
  return res.json() as Promise<Job>
}

/** Requests cancellation of a running or queued job. The returned job may still show
 * CANCELLING until the orchestrator acknowledges it. */
export async function cancelJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}/cancel`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Cancel failed: ${res.status}`)
  return res.json() as Promise<Job>
}

/** Fetches the profile of the currently logged-in user. */
export async function fetchMe(): Promise<Me> {
  const res = await fetch(`${BASE_URL}/me`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`Failed to fetch profile: ${res.status}`)
  return res.json() as Promise<Me>
}

/** Fetches the job history for the currently logged-in user. */
export async function fetchMyHistory(): Promise<Job[]> {
  const res = await fetch(`${BASE_URL}/me/history`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`Failed to fetch history: ${res.status}`)
  return res.json() as Promise<Job[]>
}

/** Fetches the output artifacts produced by a job. */
export async function fetchJobArtifacts(jobId: string): Promise<Artifact[]> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}/artifacts`)
  if (!res.ok) throw new Error(`Failed to fetch artifacts: ${res.status}`)
  return res.json() as Promise<Artifact[]>
}

/** Removes a finished job from the current user's history. */
export async function deleteMyHistory(jobId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/me/history/${jobId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Failed to delete history item: ${res.status}`)
  return
}

// ── Creator API ────────────────────────────────────────────────────────────────

export interface CreatorInputDef {
  name: string
  type: 'text' | 'file' | 'number' | 'select'
  label: string
  required?: boolean
  options?: string[]
}

export interface CreatorSpace {
  id: string
  slug: string
  name: string
  description: string
  task_type: string
  input_types: string[]
  output_types: string[]
  owner_id: string
  container_image: string
  ui_config: { inputs: CreatorInputDef[] }
  runner_config: Record<string, unknown>
  visibility: 'PUBLIC' | 'PRIVATE'
  status: 'DRAFT' | 'PUBLISHED' | 'DISABLED'
  created_at: string
}

export interface SpacePayload {
  slug: string
  name: string
  description: string
  task_type: string
  input_types: string[]
  output_types: string[]
  container_image: string
  ui_config: { inputs: CreatorInputDef[] }
  runner_config: Record<string, unknown>
  visibility: 'PUBLIC' | 'PRIVATE'
  status: 'DRAFT' | 'PUBLISHED' | 'DISABLED'
}

export interface FieldError {
  field: string
  message: string
}

export interface ValidationResult {
  valid: boolean
  errors: FieldError[]
}

/** Shared fetch wrapper for creator endpoints — injects auth and surfaces the
 * API's detail message as the thrown error string. */
async function creatorRequest<T>(url: string, options: RequestInit): Promise<T> {
  const res = await fetch(url, { ...options, headers: { ...authHeaders(), ...options.headers as Record<string,string> } })
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string }
    throw new Error(body.detail ?? `Request failed: ${res.status}`)
  }
  return res.json() as Promise<T>
}

/** Fetches all spaces owned by the current creator. */
export async function fetchMySpaces(): Promise<CreatorSpace[]> {
  return creatorRequest<CreatorSpace[]>(`${BASE_URL}/creator/spaces`, {})
}

/** Creates a new space for the current creator. */
export async function createCreatorSpace(data: SpacePayload): Promise<CreatorSpace> {
  return creatorRequest<CreatorSpace>(`${BASE_URL}/creator/spaces`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

/** Partially updates an existing space (only provided fields are changed). */
export async function updateCreatorSpace(id: string, data: Partial<SpacePayload>): Promise<CreatorSpace> {
  return creatorRequest<CreatorSpace>(`${BASE_URL}/creator/spaces/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

/** Validates a space's config and returns any field-level errors without publishing it. */
export async function validateCreatorSpace(id: string): Promise<ValidationResult> {
  return creatorRequest<ValidationResult>(`${BASE_URL}/creator/spaces/${id}/validate`, { method: 'POST' })
}

// ── Admin API ──────────────────────────────────────────────────────────────────

export interface AdminUser {
  id: string
  email: string
  display_name: string | null
  role: string
  idp: string
  subject_id: string
  created_at: string
}

export interface AdminSpaceUpdate {
  name?: string
  description?: string
  task_type?: string
  visibility?: 'PUBLIC' | 'PRIVATE'
  status?: 'DRAFT' | 'PUBLISHED' | 'DISABLED'
  owner_id?: string
}

/** Shared fetch wrapper for admin endpoints — injects auth, surfaces the API's
 * detail message, and handles 204 No Content (e.g. delete) transparently. */
async function adminRequest<T>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers as Record<string, string>) },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string }
    throw new Error(body.detail ?? `Request failed: ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

/** Fetches all spaces regardless of owner (admin view). */
export async function fetchAdminSpaces(): Promise<CreatorSpace[]> {
  return adminRequest<CreatorSpace[]>(`${BASE_URL}/admin/spaces`)
}

/** Updates a space as admin (can change owner, status, visibility). */
export async function adminUpdateSpace(id: string, data: AdminSpaceUpdate): Promise<CreatorSpace> {
  return adminRequest<CreatorSpace>(`${BASE_URL}/admin/spaces/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

/** Permanently deletes a space and all associated jobs/artifacts. */
export async function adminDeleteSpace(id: string): Promise<void> {
  return adminRequest<void>(`${BASE_URL}/admin/spaces/${id}`, { method: 'DELETE' })
}

/** Fetches the full user list for the admin dashboard. */
export async function fetchAdminUsers(): Promise<AdminUser[]> {
  return adminRequest<AdminUser[]>(`${BASE_URL}/admin/users`)
}
