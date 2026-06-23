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

/** One editable input-field row in the form, with a stable React key and the raw
 * comma-separated options string the user types. */
export interface InputRow extends CreatorInputDef {
  _key: number
  optionsRaw: string
}

/** Creates a blank input row with a stable React key so list rendering is correct. */
function emptyInputRow(key: number): InputRow {
  return { _key: key, name: '', type: 'text', label: '', required: false, optionsRaw: '' }
}

/** Strips the internal _key/optionsRaw fields and converts the comma-separated options
 * string back to an array for the API payload. */
function toPayloadInputs(rows: InputRow[]): CreatorInputDef[] {
  return rows.map((row) => {
    const def: CreatorInputDef = {
      name: row.name,
      type: row.type,
      label: row.label,
      required: row.required,
    }
    if (row.options) def.options = row.options
    if (row.type === 'select' && row.optionsRaw.trim()) {
      def.options = row.optionsRaw.split(',').map((s) => s.trim()).filter(Boolean)
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

export interface FormState {
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

/** All state and handlers for the SpaceEditor page. Keeps the component a pure
 * view: draft saving, validation and publish/unpublish all live here. */
export function useSpaceEditor() {
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

  /** Slug edited by hand — stop auto-deriving it from the name. */
  function onSlugChange(value: string) {
    setSlugManual(true)
    set('slug', value)
  }

  /** Update the runner_config text and clear any stale parse error while typing. */
  function onRunnerConfigChange(value: string) {
    set('runner_config_raw', value)
    setRunnerConfigError(null)
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

  /** Navigate back to the creator's space list. */
  function goBack() {
    navigate('/creator')
  }

  return {
    isEdit,
    form,
    inputs,
    saving,
    validating,
    saveError,
    runnerConfigError,
    validation,
    set,
    onSlugChange,
    onRunnerConfigChange,
    addInput,
    removeInput,
    updateInput,
    handleSave,
    handleValidate,
    handlePublish,
    fieldError,
    goBack,
  }
}
