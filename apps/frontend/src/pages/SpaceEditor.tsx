import InputFieldRow from '../components/InputFieldRow'
import { useSpaceEditor } from './useSpaceEditor'
import './SpaceEditor.css'

const TASK_TYPES = ['Text', 'Image', 'Audio', 'Video', '3D']
const VISIBILITY_OPTIONS = ['PUBLIC', 'PRIVATE'] as const

/** Create / edit page for a creator space. All behaviour lives in useSpaceEditor;
 * this component only renders the form and wires events to the hook's handlers. */
function SpaceEditor() {
  const {
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
  } = useSpaceEditor()

  return (
    <div className="editor-page">
      <div className="editor-header">
        <button className="editor-back" onClick={goBack}>
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
                onChange={(e) => onSlugChange(e.target.value)}
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
            {inputs.map((row, idx) => (
              <InputFieldRow
                key={row._key}
                row={row}
                index={idx}
                validation={validation}
                onUpdate={updateInput}
                onRemove={removeInput}
              />
            ))}
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
              onChange={(e) => onRunnerConfigChange(e.target.value)}
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
