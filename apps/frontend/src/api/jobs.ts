import { apiRequest, BASE_URL } from './http'

export type JobStatus =
  | 'QUEUED'
  | 'STARTING'
  | 'RUNNING'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'CANCELLING'
  | 'CANCELLED'
  | 'EXPIRED'

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

export function artifactPreviewUrl(artifactId: string): string {
  return `${BASE_URL}/artifacts/${artifactId}/preview`
}

export function artifactDownloadUrl(artifactId: string): string {
  return `${BASE_URL}/artifacts/${artifactId}/download`
}

/** Submits a job as multipart/form-data (text fields + optional file uploads). */
export async function submitJob(spaceId: string, payload: FormData): Promise<JobSubmitResponse> {
  return apiRequest<JobSubmitResponse>(`/spaces/${spaceId}/jobs`, { method: 'POST', body: payload })
}

export async function fetchJob(jobId: string): Promise<Job> {
  return apiRequest<Job>(`/jobs/${jobId}`)
}

/** Requests cancellation of a running or queued job. The returned job may still show
 * CANCELLING until the orchestrator acknowledges it. */
export async function cancelJob(jobId: string): Promise<Job> {
  return apiRequest<Job>(`/jobs/${jobId}/cancel`, { method: 'POST' })
}

export async function fetchMe(): Promise<Me> {
  return apiRequest<Me>('/me')
}

export async function fetchMyHistory(): Promise<Job[]> {
  return apiRequest<Job[]>('/me/history')
}

export async function fetchJobArtifacts(jobId: string): Promise<Artifact[]> {
  return apiRequest<Artifact[]>(`/jobs/${jobId}/artifacts`)
}

export async function deleteMyHistory(jobId: string): Promise<void> {
  await apiRequest<void>(`/me/history/${jobId}`, { method: 'DELETE' })
}
