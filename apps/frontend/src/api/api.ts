const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

let accessToken: string | null = null
export function setAccessToken(token: string | null) {
  accessToken = token
}
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

export function artifactPreviewUrl(artifactId: string): string {
  return `${BASE_URL}/artifacts/${artifactId}/preview`
}

export function artifactDownloadUrl(artifactId: string): string {
  return `${BASE_URL}/artifacts/${artifactId}/download`
}

export async function fetchSpaces(): Promise<Space[]> {
  const res = await fetch(`${BASE_URL}/spaces`)
  return res.json() as Promise<Space[]>
}

export async function fetchSpace(id: string): Promise<SpaceDetail> {
  const res = await fetch(`${BASE_URL}/spaces/${id}`)
  if (!res.ok) throw new Error(`Failed to fetch space: ${res.status}`)
  return res.json() as Promise<SpaceDetail>
}

export async function submitJob(spaceId: string, payload: FormData): Promise<JobSubmitResponse> {
  const res = await fetch(`${BASE_URL}/spaces/${spaceId}/jobs`, {
    method: 'POST',
    headers: authHeaders(),
    body: payload,
  })
  if (!res.ok) throw new Error(`Submit failed: ${res.status}`)
  return res.json() as Promise<JobSubmitResponse>
}

export async function fetchJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}`)
  if (!res.ok) throw new Error(`Failed to fetch job: ${res.status}`)
  return res.json() as Promise<Job>
}

export async function cancelJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}/cancel`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Cancel failed: ${res.status}`)
  return res.json() as Promise<Job>
}

export async function fetchMe(): Promise<Me> {
  const res = await fetch(`${BASE_URL}/me`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`Failed to fetch profile: ${res.status}`)
  return res.json() as Promise<Me>
}

export async function fetchMyHistory(): Promise<Job[]> {
  const res = await fetch(`${BASE_URL}/me/history`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`Failed to fetch history: ${res.status}`)
  return res.json() as Promise<Job[]>
}

export async function fetchJobArtifacts(jobId: string): Promise<Artifact[]> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}/artifacts`)
  if (!res.ok) throw new Error(`Failed to fetch artifacts: ${res.status}`)
  return res.json() as Promise<Artifact[]>
}

export async function deleteMyHistory(jobId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/me/history/${jobId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Failed to delete history item: ${res.status}`)
  return
}
