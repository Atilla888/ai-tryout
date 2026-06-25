import type { InputFieldConfig } from '../api/api'

export type FormValues = Record<string, string | File | null>
export type FormErrors = Record<string, string>

export const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
export const AUDIO_TYPES = ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/webm']

export function validateForm(inputs: InputFieldConfig[], values: FormValues): FormErrors {
  const errors: FormErrors = {}
  for (const field of inputs) {
    const val = values[field.name]
    const empty = val === null || val === undefined || val === ''
    if (field.required && empty) {
      errors[field.name] = `${field.label} is required`
      continue
    }
    if (!empty) {
      if (typeof val === 'string') {
        if (field.maxLength && val.length > field.maxLength)
          errors[field.name] = `Max ${field.maxLength} characters`
        if (field.type === 'number') {
          const n = parseFloat(val)
          if (!isNaN(n)) {
            if (field.min !== undefined && n < field.min) errors[field.name] = `Minimum is ${field.min}`
            if (field.max !== undefined && n > field.max) errors[field.name] = `Maximum is ${field.max}`
          }
        }
      }
      if (val instanceof File) {
        const allowed = field.type === 'image_upload' ? IMAGE_TYPES : AUDIO_TYPES
        if (!allowed.includes(val.type)) {
          errors[field.name] = `Invalid file type`
        } else if (field.max_size_mb && val.size > field.max_size_mb * 1024 * 1024) {
          errors[field.name] = `File too large. Max ${field.max_size_mb} MB`
        }
      }
    }
  }
  return errors
}
