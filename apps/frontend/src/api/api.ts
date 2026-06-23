/** Barrel module: re-exports the domain-split API so existing imports
 * (`from '../api/api'`) keep working. New code may import from the domain
 * modules (./spaces, ./jobs, ./creator, ./admin) or the shared ./http wrapper. */
export * from './http'
export * from './spaces'
export * from './jobs'
export * from './creator'
export * from './admin'
