import { apiRequest } from './http'

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

export async function fetchMySpaces(): Promise<CreatorSpace[]> {
  return apiRequest<CreatorSpace[]>('/creator/spaces')
}

export async function createCreatorSpace(data: SpacePayload): Promise<CreatorSpace> {
  return apiRequest<CreatorSpace>('/creator/spaces', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateCreatorSpace(id: string, data: Partial<SpacePayload>): Promise<CreatorSpace> {
  return apiRequest<CreatorSpace>(`/creator/spaces/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function validateCreatorSpace(id: string): Promise<ValidationResult> {
  return apiRequest<ValidationResult>(`/creator/spaces/${id}/validate`, { method: 'POST' })
}
