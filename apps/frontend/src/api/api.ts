const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type SpaceVisibility = 'public' | 'private'
export type SpaceStatus = 'draft' | 'published' | 'disabled'
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

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

export interface Job {
  id: string
  space_id: string
  user_id: string | null
  status: JobStatus
  queue_position: number | null
  progress_percent: number | null
  progress_message: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  expires_at: string | null
  error_code: string | null
  error_message: string | null
}

export async function fetchSpaces(): Promise<Space[]> {
  const res = await fetch(`${BASE_URL}/spaces`)
  return res.json() as Promise<Space[]>
}

export async function fetchJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}`)
  return res.json() as Promise<Job>
}
