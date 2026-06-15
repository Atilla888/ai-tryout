import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  createCreatorSpace,
  fetchMySpaces,
  updateCreatorSpace,
  validateCreatorSpace,
  type CreatorInputDef,
  type CreatorSpace,
  type FieldError,
  type SpacePayload,
  type ValidationResult,
} from '../api/api'
import './SpaceEditor.css'

const INPUT_TYPES = ['text', 'file', 'number', 'select'] as const
const TASK_TYPES = ['Text', 'Image', 'Audio', 'Video', '3D']
const VISIBILITY_OPTIONS = ['PUBLIC', 'PRIVATE'] as const

interface InputRow extends CreatorInputDef {
  _key: number
  optionsRaw: string
}

/** Creates a blank input row with a stable React key so list rendering is correct. */
function emptyInputRow(key: number): InputRow {
  return { _key: key, name: '', type: 'text', label: '', required: false, optionsRaw: '' }
}

/** Strips the internal _key/_optionsRaw fields and converts the comma-separated options
 * string back to an array for the API payload. */
function toPayloadInputs(rows: InputRow[]): CreatorInputDef[] {
  return rows.map(({ _key: _k, optionsRaw, ...rest }) => {
    const def: CreatorInputDef = { ...rest }
    if (rest.type === 'select' && optionsRaw.trim()) {
      def.options = optionsRaw.split(',').map((s) => s.trim()).filter(Boolean)
    }
    return def
  })
}

/** Converts saved API inputs back to the editable InputRow format for the form. */
function fromExistingInputs(inputs: CreatorInputDef[]): InputRow[] {
  return inputs.map((inp, i) => ({
    ...inp,
    _key: i,
    optionsRaw: inp.options?.join(', ') ?? '',
  }))
}

/** Parses the runner_config textarea string. Returns null if the JSON is invalid or not an object. */
function parseRunnerConfig(raw: string): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(raw)
    if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>
    }
    return null
  } catch {
    return null
  }
}

interface FormState {
  slug: string
  name: string
  description: string
  task_type: string
  input_types: string
  output_types: string
  container_image: string
  visibility: 'PUBLIC' | 'PRIVATE'
  status: 'DRAFT' | 'PUBLISHED' | 'DISABLED'
  runner_config_raw: string
}

const DEFAULT_FORM: FormState = {
  slug: '',
  name: '',
  description: '',
  task_type: 'Text',
  input_types: 'text',
  output_types: 'text',
  container_image: '',
  visibility: 'PRIVATE',
  status: 'DRAFT',
  runner_config_raw: '{}',
}

/** Derives a URL-safe slug from a display name (auto-applied until the user edits the slug manually). */
function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

/** Create / edit page for a creator space. Handles draft saving, validation, publish/unpublish.
 * Publish first saves the payload, then validates; on failure it reverts to DRAFT. */
function SpaceEditor() {
  const { spaceId } = useParams<{ spaceId: string }>()
  const isEdit = Boolean(spaceId)
  const navigate = useNavigate()

  const [form, setForm] = useState<FormState>(DEFAULT_FORM)
  const [inputs, setInputs] = useState<InputRow[]>([emptyInputRow(0)])
  const [nextKey, setNextKey] = useState(1)
  const [slugManual, setSlugManual] = useState(false)

  const [saving, setSaving] = useState(false)
  const [validating, setValidating] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [runnerConfigError, setRunnerConfigError] = useState<string | null>(null)
  const [validation, setValidation] = useState<ValidationResult | null>(null)

  useEffect(() => {
    if (!spaceId) return
    fetchMySpaces().then((spaces) => {
      const space = spaces.find((s: CreatorSpace) => s.id === spaceId)
      if (!space) return
      setForm({
        slug: space.slug,
        name: space.name,
        description: space.description,
        task_type: space.task_type,
        input_types: space.input_types.join(', '),
        output_types: space.output_types.join(', '),
        container_image: space.container_image,
        visibility: space.visibility,
        status: space.status,
        runner_config_raw: JSON.stringify(space.runner_config, null, 2),
      })
      setInputs(fromExistingInputs(space.ui_config?.inputs ?? []))
      setSlugManual(true)
    }).catch(() => {})
  }, [spaceId])

  function set(field: keyof FormState, value: string) {
    setForm((prev) => {
      const next = { ...prev, [field]: value }
      if (field === 'name' && !slugManual) {
        next.slug = slugify(value)
      }
      return next
    })
  }

  function addInput() {
    setInputs((prev) => [...prev, emptyInputRow(nextKey)])
    setNextKey((k) => k + 1)
  }

  function removeInput(key: number) {
    setInputs((prev) => prev.filter((r) => r._key !== key))
  }

  function updateInput(key: number, field: keyof InputRow, value: string | boolean) {
    setInputs((prev) =>
      prev.map((r) => (r._key === key ? { ...r, [field]: value } : r))
    )
  }

  function buildPayload(overrideStatus?: 'DRAFT' | 'PUBLISHED'): SpacePayload | null {
    const runner = parseRunnerConfig(form.runner_config_raw)
    if (runner === null) {
      setRunnerConfigError('runner_config must be a valid JSON object')
      return null
    }
    setRunnerConfigError(null)
    return {
      slug: form.slug.trim(),
      name: form.name.trim(),
      description: form.description.trim(),
      task_type: form.task_type,
      input_types: form.input_types.split(',').map((s) => s.trim()).filter(Boolean),
      output_types: form.output_types.split(',').map((s) => s.trim()).filter(Boolean),
      container_image: form.container_image.trim(),
      ui_config: { inputs: toPayloadInputs(inputs) },
      runner_config: runner,
      visibility: form.visibility,
      status: overrideStatus ?? form.status,
    }
  }

  async function handleSave(overrideStatus?: 'DRAFT' | 'PUBLISHED') {
    const payload = buildPayload(overrideStatus)
    if (!payload) return
    setSaving(true)
    setSaveError(null)
    try {
      if (isEdit && spaceId) {
        await updateCreatorSpace(spaceId, payload)
        if (overrideStatus) setForm((f) => ({ ...f, status: overrideStatus }))
      } else {
        const created = await createCreatorSpace(payload)
        navigate(`/creator/spaces/${created.id}/edit`, { replace: true })
      }
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function handleValidate() {
    if (!spaceId) return
    setValidating(true)
    setValidation(null)
    try {
      const result = await validateCreatorSpace(spaceId)
      setValidation(result)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Validation request failed')
    } finally {
      setValidating(false)
    }
  }

  async function handlePublish() {
    const payload = buildPayload('PUBLISHED')
    if (!payload) return
    setSaving(true)
    setSaveError(null)
    setValidation(null)
    try {
      if (isEdit && spaceId) {
        await updateCreatorSpace(spaceId, payload)
        const result = await validateCreatorSpace(spaceId)
        setValidation(result)
        if (result.valid) {
          setForm((f) => ({ ...f, status: 'PUBLISHED' }))
        } else {
          await updateCreatorSpace(spaceId, { status: 'DRAFT' })
          setForm((f) => ({ ...f, status: 'DRAFT' }))
          setSaveError('Fix validation errors before publishing.')
        }
      } else {
        const created = await createCreatorSpace(payload)
        navigate(`/creator/spaces/${created.id}/edit`, { replace: true })
      }
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Publish failed')
    } finally {
      setSaving(false)
    }
  }

  const fieldError = (field: string): FieldError | undefined =>
    validation?.errors.find((e) => e.field === field || e.field.startsWith(field))

  return (
    <div className="editor-page">
      <div className="editor-header">
        <button className="editor-back" onClick={() => navigate('/creator')}>
          ← My Spaces
        </button>
        <h1 className="editor-title">{isEdit ? 'Edit Space' : 'New Space'}</h1>
        {isEdit && (
          <span className={`creator-status-badge creator-status-${form.status.toLowerCase()}`}>
            {form.status}
          </span>
        )}
      </div>

      {saveError && <div className="editor-error-box">{saveError}</div>}

      {validation && (
        <div className={`editor-validation-box ${validation.valid ? 'valid' : 'invalid'}`}>
          {validation.valid ? (
            <span>✓ Configuration is valid</span>
          ) : (
            <>
              <strong>Validation failed</strong>
              <ul className="editor-error-list">
                {validation.errors.map((e, i) => (
                  <li key={i}><code>{e.field}</code>: {e.message}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      <div className="editor-sections">
        {/* ── Basic info ── */}
        <section className="editor-section">
          <h2 className="editor-section-title">Basic info</h2>
          <div className="editor-grid-2">
            <div className="editor-field">
              <label className="editor-label">Name *</label>
              <input
                className="editor-input"
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
                placeholder="My Space"
              />
            </div>
            <div className="editor-field">
              <label className="editor-label">Slug *</label>
              <input
                className="editor-input"
                value={form.slug}
                onChange={(e) => { setSlugManual(true); set('slug', e.target.value) }}
                placeholder="my-space"
              />
            </div>
          </div>

          <div className="editor-field">
            <label className="editor-label">Description</label>
            <textarea
              className="editor-textarea editor-textarea-sm"
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
              placeholder="What does this space do?"
            />
          </div>

          <div className="editor-grid-2">
            <div className="editor-field">
              <label className="editor-label">Task type *</label>
              <select className="editor-select" value={form.task_type} onChange={(e) => set('task_type', e.target.value)}>
                {TASK_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="editor-field">
              <label className="editor-label">Container image *</label>
              <input
                className={`editor-input ${fieldError('container_image') ? 'editor-input-error' : ''}`}
                value={form.container_image}
                onChange={(e) => set('container_image', e.target.value)}
                placeholder="ghcr.io/org/model:latest"
              />
              {fieldError('container_image') && (
                <span className="editor-field-error">{fieldError('container_image')!.message}</span>
              )}
            </div>
          </div>

          <div className="editor-grid-2">
            <div className="editor-field">
              <label className="editor-label">Input types (comma-separated)</label>
              <input
                className="editor-input"
                value={form.input_types}
                onChange={(e) => set('input_types', e.target.value)}
                placeholder="text, image"
              />
            </div>
            <div className="editor-field">
              <label className="editor-label">Output types (comma-separated)</label>
              <input
                className="editor-input"
                value={form.output_types}
                onChange={(e) => set('output_types', e.target.value)}
                placeholder="text"
              />
            </div>
          </div>
        </section>

        {/* ── Dynamic inputs ── */}
        <section className="editor-section">
          <div className="editor-section-header-row">
            <h2 className="editor-section-title">Input fields</h2>
            <button type="button" className="btn-creator-secondary btn-sm" onClick={addInput}>
              + Add field
            </button>
          </div>
          <p className="editor-section-hint">
            Define the form fields a user fills in when submitting a job.
          </p>

          {fieldError('ui_config.inputs') && (
            <div className="editor-field-error-banner">{fieldError('ui_config.inputs')!.message}</div>
          )}

          {inputs.length === 0 && (
            <p className="editor-empty-hint">No input fields yet. Add one above.</p>
          )}

          <div className="input-rows">
            {inputs.map((row, idx) => {
              const rowError = (f: string) =>
                validation?.errors.find((e) => e.field === `ui_config.inputs[${idx}].${f}`)

              return (
                <div key={row._key} className="input-row">
                  <div className="input-row-top">
                    <span className="input-row-num">#{idx + 1}</span>
                    <button
                      type="button"
                      className="input-row-remove"
                      onClick={() => removeInput(row._key)}
                      title="Remove field"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="editor-grid-3">
                    <div className="editor-field">
                      <label className="editor-label">Name *</label>
                      <input
                        className={`editor-input ${rowError('name') ? 'editor-input-error' : ''}`}
                        value={row.name}
                        onChange={(e) => updateInput(row._key, 'name', e.target.value)}
                        placeholder="my_field"
                      />
                      {rowError('name') && <span className="editor-field-error">{rowError('name')!.message}</span>}
                    </div>
                    <div className="editor-field">
                      <label className="editor-label">Label *</label>
                      <input
                        className={`editor-input ${rowError('label') ? 'editor-input-error' : ''}`}
                        value={row.label}
                        onChange={(e) => updateInput(row._key, 'label', e.target.value)}
                        placeholder="My Field"
                      />
                      {rowError('label') && <span className="editor-field-error">{rowError('label')!.message}</span>}
                    </div>
                    <div className="editor-field">
                      <label className="editor-label">Type *</label>
                      <select
                        className={`editor-select ${rowError('type') ? 'editor-input-error' : ''}`}
                        value={row.type}
                        onChange={(e) => updateInput(row._key, 'type', e.target.value)}
                      >
                        {INPUT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </div>
                  </div>

                  <div className="editor-grid-2">
                    <label className="editor-checkbox-label">
                      <input
                        type="checkbox"
                        checked={row.required ?? false}
                        onChange={(e) => updateInput(row._key, 'required', e.target.checked)}
                      />
                      Required
                    </label>

                    {row.type === 'select' && (
                      <div className="editor-field">
                        <label className="editor-label">Options (comma-separated) *</label>
                        <input
                          className={`editor-input ${rowError('options') ? 'editor-input-error' : ''}`}
                          value={row.optionsRaw}
                          onChange={(e) => updateInput(row._key, 'optionsRaw', e.target.value)}
                          placeholder="Option A, Option B, Option C"
                        />
                        {rowError('options') && <span className="editor-field-error">{rowError('options')!.message}</span>}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        {/* ── Runner config ── */}
        <section className="editor-section">
          <h2 className="editor-section-title">Runner config</h2>
          <p className="editor-section-hint">
            JSON object. Optional keys: <code>timeout_seconds</code> (1–86400), <code>memory_mb</code> (64–65536).
          </p>
          <div className="editor-field">
            <textarea
              className={`editor-textarea editor-textarea-code ${runnerConfigError ? 'editor-input-error' : ''}`}
              value={form.runner_config_raw}
              onChange={(e) => { set('runner_config_raw', e.target.value); setRunnerConfigError(null) }}
              rows={4}
            />
            {runnerConfigError && <span className="editor-field-error">{runnerConfigError}</span>}
            {fieldError('runner_config') && (
              <span className="editor-field-error">{fieldError('runner_config')!.message}</span>
            )}
          </div>
        </section>

        {/* ── Visibility & status ── */}
        <section className="editor-section">
          <h2 className="editor-section-title">Visibility &amp; status</h2>
          <div className="editor-grid-2">
            <div className="editor-field">
              <label className="editor-label">Visibility</label>
              <div className="editor-radio-group">
                {VISIBILITY_OPTIONS.map((v) => (
                  <label key={v} className="editor-radio-label">
                    <input
                      type="radio"
                      name="visibility"
                      value={v}
                      checked={form.visibility === v}
                      onChange={() => set('visibility', v)}
                    />
                    {v === 'PUBLIC' ? '🌐 Public' : '🔒 Private'}
                  </label>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* ── Action bar ── */}
      <div className="editor-actions">
        {!isEdit ? (
          <button className="btn-creator-primary" onClick={() => void handleSave('DRAFT')} disabled={saving}>
            {saving ? 'Saving…' : 'Save as Draft'}
          </button>
        ) : (
          <>
            <button className="btn-creator-secondary" onClick={() => void handleSave()} disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              className="btn-creator-outline"
              onClick={() => void handleValidate()}
              disabled={validating || saving}
            >
              {validating ? 'Validating…' : 'Validate'}
            </button>
            {form.status !== 'PUBLISHED' ? (
              <button
                className="btn-creator-primary"
                onClick={() => void handlePublish()}
                disabled={saving}
              >
                {saving ? 'Publishing…' : 'Publish'}
              </button>
            ) : (
              <button
                className="btn-creator-danger"
                onClick={() => void handleSave('DRAFT')}
                disabled={saving}
              >
                Unpublish
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default SpaceEditor
