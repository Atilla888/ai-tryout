const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function fetchSpaces() {
  const res = await fetch(`${BASE_URL}/spaces`)
  return res.json()
}

export async function fetchJob(jobId: string) {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}`)
  return res.json()
}