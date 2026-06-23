import { apiRequest } from './http'
import type { CreatorSpace } from './creator'

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

/** Fetches all spaces regardless of owner (admin view). */
export async function fetchAdminSpaces(): Promise<CreatorSpace[]> {
  return apiRequest<CreatorSpace[]>('/admin/spaces')
}

/** Updates a space as admin (can change owner, status, visibility). */
export async function adminUpdateSpace(id: string, data: AdminSpaceUpdate): Promise<CreatorSpace> {
  return apiRequest<CreatorSpace>(`/admin/spaces/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

/** Permanently deletes a space and all associated jobs/artifacts. */
export async function adminDeleteSpace(id: string): Promise<void> {
  await apiRequest<void>(`/admin/spaces/${id}`, { method: 'DELETE' })
}

/** Fetches the full user list for the admin dashboard. */
export async function fetchAdminUsers(): Promise<AdminUser[]> {
  return apiRequest<AdminUser[]>('/admin/users')
}
