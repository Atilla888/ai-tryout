import { apiRequest } from './http'

export type SpaceVisibility = 'public' | 'private'
export type SpaceStatus = 'draft' | 'published' | 'disabled'

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

/** Fetches the list of all publicly visible spaces. No auth required. */
export async function fetchSpaces(): Promise<Space[]> {
  return apiRequest<Space[]>('/spaces')
}

/** Fetches full detail for a single space including its UI and runner config. */
export async function fetchSpace(id: string): Promise<SpaceDetail> {
  return apiRequest<SpaceDetail>(`/spaces/${id}`)
}
