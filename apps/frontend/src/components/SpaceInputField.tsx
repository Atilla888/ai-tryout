import { useRef, useState } from 'react'
import type { InputFieldConfig } from '../api/api'
import { AUDIO_TYPES, IMAGE_TYPES } from './spaceForm'

interface DropZoneProps {
  field: InputFieldConfig
  value: File | null
  hasError: boolean
  onChange: (file: File | null) => void
}

function DropZone({ field, value, hasError, onChange }: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const accept = field.type === 'image_upload' ? 'image/*' : 'audio/*'
  const allowed = field.type === 'image_upload' ? IMAGE_TYPES : AUDIO_TYPES

  const handleFile = (file: File | undefined) => {
    if (!file) return
    onChange(allowed.includes(file.type) ? file : null)
  }

  return (
    <div
      className={'drop-zone' + (dragging ? ' dragover' : '') + (hasError ? ' input-error' : '')}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <strong>{value ? value.name : 'Drop file or click to upload'}</strong>
      <span className="drop-note">
        Accepted: {field.mime_types?.join(', ') || accept} · Max {field.max_size_mb ?? 10} MB
      </span>
    </div>
  )
}

interface SpaceInputFieldProps {
  config: InputFieldConfig
  value: string | File | null
  error?: string
  onChange: (name: string, val: string | File | null) => void
}

function SpaceInputField({ config, value, error, onChange }: SpaceInputFieldProps) {
  const { name, type, label, description, required, placeholder, maxLength, min, max, options } = config
  const hasError = !!error

  const renderControl = () => {
    switch (type) {
      case 'text':
        return (
          <input
            type="text"
            id={name}
            className={hasError ? 'input-error' : ''}
            placeholder={placeholder}
            maxLength={maxLength}
            value={(value as string) ?? ''}
            onChange={(e) => onChange(name, e.target.value)}
          />
        )
      case 'textarea':
        return (
          <textarea
            id={name}
            className={hasError ? 'input-error' : ''}
            placeholder={placeholder}
            maxLength={maxLength}
            value={(value as string) ?? ''}
            onChange={(e) => onChange(name, e.target.value)}
          />
        )
      case 'number':
        return (
          <input
            type="number"
            id={name}
            className={hasError ? 'input-error' : ''}
            placeholder={placeholder}
            min={min}
            max={max}
            value={(value as string) ?? ''}
            onChange={(e) => onChange(name, e.target.value)}
          />
        )
      case 'select':
        return (
          <select
            id={name}
            className={hasError ? 'input-error' : ''}
            value={(value as string) ?? ''}
            onChange={(e) => onChange(name, e.target.value)}
          >
            <option value="">{placeholder ?? 'Select an option'}</option>
            {(options ?? []).map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        )
      case 'image_upload':
      case 'audio_upload':
        return (
          <DropZone
            field={config}
            value={value as File | null}
            hasError={hasError}
            onChange={(file) => onChange(name, file)}
          />
        )
      default:
        console.warn(`Unsupported input type: "${type}". Rendering fallback text input.`)
        return (
          <input
            type="text"
            id={name}
            placeholder={placeholder}
            value={(value as string) ?? ''}
            onChange={(e) => onChange(name, e.target.value)}
          />
        )
    }
  }

  return (
    <div className="form-row">
      <label htmlFor={name}>
        {label}
        {required && <span className="required-indicator">*</span>}
      </label>
      {description && <div className="form-description">{description}</div>}
      {renderControl()}
      {error && <div className="field-error">{error}</div>}
    </div>
  )
}

export default SpaceInputField
