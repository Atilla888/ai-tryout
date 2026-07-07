import { apiRequest } from './http'
import type { CreatorSpace } from './creator'

export interface AdminUser {
  id: string
  user_number: number
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

export async function fetchAdminSpaces(): Promise<CreatorSpace[]> {
  return apiRequest<CreatorSpace[]>('/admin/spaces')
}

export async function adminUpdateSpace(id: string, data: AdminSpaceUpdate): Promise<CreatorSpace> {
  return apiRequest<CreatorSpace>(`/admin/spaces/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function adminDeleteSpace(id: string): Promise<void> {
  await apiRequest<void>(`/admin/spaces/${id}`, { method: 'DELETE' })
}

export async function fetchAdminUsers(): Promise<AdminUser[]> {
  return apiRequest<AdminUser[]>('/admin/users')
}
