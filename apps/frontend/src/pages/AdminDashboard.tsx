import { useEffect, useState } from 'react'
import {
  adminDeleteSpace,
  adminUpdateSpace,
  fetchAdminSpaces,
  fetchAdminUsers,
  type AdminSpaceUpdate,
  type AdminUser,
  type CreatorSpace,
} from '../api/api'
import './AdminDashboard.css'

function StatusBadge({ status }: { status: string }) {
  return <span className={`adm-badge adm-status-${status.toLowerCase()}`}>{status}</span>
}

function VisBadge({ visibility }: { visibility: string }) {
  return <span className={`adm-badge adm-vis-${visibility.toLowerCase()}`}>{visibility}</span>
}

function RoleBadge({ role }: { role: string }) {
  return <span className={`adm-badge adm-role-${role.toLowerCase()}`}>{role}</span>
}

interface EditFormProps {
  space: CreatorSpace
  users: AdminUser[]
  onSave: (id: string, patch: AdminSpaceUpdate) => Promise<void>
  onClose: () => void
}

/** Inline form that lets an admin change a space's status, visibility, and owner. */
function SpaceEditForm({ space, users, onSave, onClose }: EditFormProps) {
  const [status, setStatus] = useState(space.status)
  const [visibility, setVisibility] = useState(space.visibility)
  const [ownerId, setOwnerId] = useState(space.owner_id)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      await onSave(space.id, { status, visibility, owner_id: ownerId })
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="adm-edit-form">
      {error && <div className="adm-inline-error">{error}</div>}
      <div className="adm-edit-row">
        <label className="adm-edit-label">Status</label>
        <select className="adm-select" value={status} onChange={(e) => setStatus(e.target.value as typeof status)}>
          <option value="DRAFT">DRAFT</option>
          <option value="PUBLISHED">PUBLISHED</option>
          <option value="DISABLED">DISABLED</option>
        </select>
      </div>
      <div className="adm-edit-row">
        <label className="adm-edit-label">Visibility</label>
        <select className="adm-select" value={visibility} onChange={(e) => setVisibility(e.target.value as typeof visibility)}>
          <option value="PUBLIC">PUBLIC</option>
          <option value="PRIVATE">PRIVATE</option>
        </select>
      </div>
      <div className="adm-edit-row">
        <label className="adm-edit-label">Owner</label>
        <select className="adm-select" value={ownerId ?? ''} onChange={(e) => setOwnerId(e.target.value)}>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              #{u.user_number} · {u.display_name ?? u.email} ({u.role})
            </option>
          ))}
        </select>
      </div>
      <div className="adm-edit-actions">
        <button className="adm-btn-primary btn-sm" onClick={() => void handleSave()} disabled={saving}>
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button className="adm-btn-ghost btn-sm" onClick={onClose} disabled={saving}>
          Cancel
        </button>
      </div>
    </div>
  )
}

interface SpacesTabProps {
  spaces: CreatorSpace[]
  users: AdminUser[]
  onSpaceUpdated: (updated: CreatorSpace) => void
  onSpaceDeleted: (id: string) => void
}

/** Admin spaces table with search, inline edit form, and two-step delete confirmation. */
function SpacesTab({ spaces, users, onSpaceUpdated, onSpaceDeleted }: SpacesTabProps) {
  const [query, setQuery] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  const filtered = spaces.filter((s) => {
    const q = query.toLowerCase()
    return !q || s.name.toLowerCase().includes(q) || s.slug.toLowerCase().includes(q)
  })

  async function handleDelete(id: string) {
    setDeleting(true)
    try {
      await adminDeleteSpace(id)
      onSpaceDeleted(id)
    } catch {
      // error surfaced to user via alert
      alert('Delete failed')
    } finally {
      setDeleting(false)
      setConfirmDeleteId(null)
    }
  }

  async function handleSave(id: string, patch: AdminSpaceUpdate) {
    const updated = await adminUpdateSpace(id, patch)
    onSpaceUpdated(updated)
  }

  // owner_id is the creator's public UUID; resolve it to a readable name from
  // the loaded users list. The creator's running number comes from owner_number.
  const ownerName = (space: CreatorSpace) => {
    const u = users.find((u) => u.id === space.owner_id)
    return u ? (u.display_name ?? u.email) : 'Unknown user'
  }

  return (
    <div>
      <input
        className="adm-search"
        placeholder="Search by name or slug…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <p className="adm-count">{filtered.length} space{filtered.length !== 1 ? 's' : ''}</p>

      <div className="adm-table-wrap">
        <table className="adm-table">
          <thead>
            <tr>
              <th>Name / Slug</th>
              <th>Owner</th>
              <th>Status</th>
              <th>Visibility</th>
              <th>Task type</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((space) => (
              <>
                <tr key={space.id} className={editingId === space.id ? 'adm-row-active' : ''}>
                  <td>
                    <div className="adm-space-name">{space.name}</div>
                    <div className="adm-space-slug">/{space.slug}</div>
                  </td>
                  <td className="adm-cell-secondary">
                    <span className="adm-id-chip">#{space.owner_number}</span> {ownerName(space)}
                  </td>
                  <td><StatusBadge status={space.status} /></td>
                  <td><VisBadge visibility={space.visibility} /></td>
                  <td className="adm-cell-secondary">{space.task_type}</td>
                  <td>
                    <div className="adm-row-actions">
                      <button
                        className="adm-btn-secondary btn-sm"
                        onClick={() => setEditingId(editingId === space.id ? null : space.id)}
                      >
                        {editingId === space.id ? 'Close' : 'Edit'}
                      </button>
                      {confirmDeleteId === space.id ? (
                        <>
                          <button
                            className="adm-btn-danger btn-sm"
                            onClick={() => void handleDelete(space.id)}
                            disabled={deleting}
                          >
                            {deleting ? 'Deleting…' : 'Confirm'}
                          </button>
                          <button
                            className="adm-btn-ghost btn-sm"
                            onClick={() => setConfirmDeleteId(null)}
                            disabled={deleting}
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button
                          className="adm-btn-danger btn-sm"
                          onClick={() => setConfirmDeleteId(space.id)}
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
                {editingId === space.id && (
                  <tr key={`${space.id}-edit`} className="adm-edit-row-container">
                    <td colSpan={6}>
                      <SpaceEditForm
                        space={space}
                        users={users}
                        onSave={handleSave}
                        onClose={() => setEditingId(null)}
                      />
                    </td>
                  </tr>
                )}
              </>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="adm-empty-cell">No spaces match your search.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/** Admin users table with name/email search. Read-only — user management is via Keycloak. */
function UsersTab({ users }: { users: AdminUser[] }) {
  const [query, setQuery] = useState('')
  const filtered = users.filter((u) => {
    const q = query.toLowerCase()
    return !q || u.email.toLowerCase().includes(q) || (u.display_name ?? '').toLowerCase().includes(q)
  })

  return (
    <div>
      <input
        className="adm-search"
        placeholder="Search by email or name…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <p className="adm-count">{filtered.length} user{filtered.length !== 1 ? 's' : ''}</p>

      <div className="adm-table-wrap">
        <table className="adm-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>IdP</th>
              <th>Joined</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((u) => (
              <tr key={u.id}>
                <td><span className="adm-id-chip">#{u.user_number}</span></td>
                <td className="adm-user-name">{u.display_name ?? '—'}</td>
                <td className="adm-cell-secondary">{u.email}</td>
                <td><RoleBadge role={u.role} /></td>
                <td className="adm-cell-secondary">{u.idp}</td>
                <td className="adm-cell-secondary">{new Date(u.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="adm-empty-cell">No users match your search.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

type Tab = 'spaces' | 'users'

/** Admin dashboard shell — loads all spaces and users upfront, then renders the active tab. */
function AdminDashboard() {
  const [tab, setTab] = useState<Tab>('spaces')
  const [spaces, setSpaces] = useState<CreatorSpace[]>([])
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchAdminSpaces(), fetchAdminUsers()])
      .then(([s, u]) => { setSpaces(s); setUsers(u) })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load admin data'))
      .finally(() => setLoading(false))
  }, [])

  function handleSpaceUpdated(updated: CreatorSpace) {
    setSpaces((prev) => prev.map((s) => (s.id === updated.id ? updated : s)))
  }

  function handleSpaceDeleted(id: string) {
    setSpaces((prev) => prev.filter((s) => s.id !== id))
  }

  return (
    <div className="adm-page">
      <div className="adm-header">
        <h1 className="adm-title">Admin</h1>
        <p className="adm-subtitle">Manage all spaces and users</p>
      </div>

      <div className="adm-tabs">
        <button
          className={`adm-tab ${tab === 'spaces' ? 'adm-tab-active' : ''}`}
          onClick={() => setTab('spaces')}
        >
          Spaces {!loading && <span className="adm-tab-count">{spaces.length}</span>}
        </button>
        <button
          className={`adm-tab ${tab === 'users' ? 'adm-tab-active' : ''}`}
          onClick={() => setTab('users')}
        >
          Users {!loading && <span className="adm-tab-count">{users.length}</span>}
        </button>
      </div>

      {loading && <p className="adm-loading">Loading…</p>}

      {!loading && error && (
        <div className="adm-error-box">
          <strong>Could not load admin data.</strong> {error}
        </div>
      )}

      {!loading && !error && tab === 'spaces' && (
        <SpacesTab
          spaces={spaces}
          users={users}
          onSpaceUpdated={handleSpaceUpdated}
          onSpaceDeleted={handleSpaceDeleted}
        />
      )}

      {!loading && !error && tab === 'users' && <UsersTab users={users} />}
    </div>
  )
}

export default AdminDashboard
