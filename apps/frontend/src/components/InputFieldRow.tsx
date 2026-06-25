import { type ValidationResult } from '../api/api'
import { type InputRow } from '../pages/useSpaceEditor'

const INPUT_TYPES = ['text', 'file', 'number', 'select'] as const

interface InputFieldRowProps {
  row: InputRow
  index: number
  validation: ValidationResult | null
  onUpdate: (key: number, field: keyof InputRow, value: string | boolean) => void
  onRemove: (key: number) => void
}

/** Renders and edits a single dynamic input-field definition, showing per-field
 * validation errors scoped to this row's index. */
function InputFieldRow({ row, index, validation, onUpdate, onRemove }: InputFieldRowProps) {
  const rowError = (f: string) =>
    validation?.errors.find((e) => e.field === `ui_config.inputs[${index}].${f}`)

  return (
    <div className="input-row">
      <div className="input-row-top">
        <span className="input-row-num">#{index + 1}</span>
        <button
          type="button"
          className="input-row-remove"
          onClick={() => onRemove(row._key)}
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
            onChange={(e) => onUpdate(row._key, 'name', e.target.value)}
            placeholder="my_field"
          />
          {rowError('name') && <span className="editor-field-error">{rowError('name')!.message}</span>}
        </div>
        <div className="editor-field">
          <label className="editor-label">Label *</label>
          <input
            className={`editor-input ${rowError('label') ? 'editor-input-error' : ''}`}
            value={row.label}
            onChange={(e) => onUpdate(row._key, 'label', e.target.value)}
            placeholder="My Field"
          />
          {rowError('label') && <span className="editor-field-error">{rowError('label')!.message}</span>}
        </div>
        <div className="editor-field">
          <label className="editor-label">Type *</label>
          <select
            className={`editor-select ${rowError('type') ? 'editor-input-error' : ''}`}
            value={row.type}
            onChange={(e) => onUpdate(row._key, 'type', e.target.value)}
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
            onChange={(e) => onUpdate(row._key, 'required', e.target.checked)}
          />
          Required
        </label>

        {row.type === 'select' && (
          <div className="editor-field">
            <label className="editor-label">Options (comma-separated) *</label>
            <input
              className={`editor-input ${rowError('options') ? 'editor-input-error' : ''}`}
              value={row.optionsRaw}
              onChange={(e) => onUpdate(row._key, 'optionsRaw', e.target.value)}
              placeholder="Option A, Option B, Option C"
            />
            {rowError('options') && <span className="editor-field-error">{rowError('options')!.message}</span>}
          </div>
        )}
      </div>
    </div>
  )
}

export default InputFieldRow
