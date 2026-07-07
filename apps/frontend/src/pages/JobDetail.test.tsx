import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import JobDetail from './JobDetail'
import * as api from '../api/api'
import type { Artifact, Job } from '../api/api'

vi.mock('../api/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/api')>()
  return {
    ...actual,
    fetchJob: vi.fn(),
    fetchJobArtifacts: vi.fn(),
    cancelJob: vi.fn(),
  }
})

const mockedFetchJob = api.fetchJob as unknown as ReturnType<typeof vi.fn>
const mockedFetchJobArtifacts = api.fetchJobArtifacts as unknown as ReturnType<typeof vi.fn>
const mockedCancelJob = api.cancelJob as unknown as ReturnType<typeof vi.fn>

function baseJob(overrides: Partial<Job> = {}): Job {
  return {
    id: 'job-123',
    space_id: 'space-1',
    space_name: 'Image Magic',
    user_id: 'user-1',
    user_number: 1,
    status: 'QUEUED',
    queue_position: null,
    progress_percent: 0,
    progress_message: null,
    created_at: '2026-01-01T00:00:00Z',
    started_at: null,
    finished_at: null,
    cancelled_at: null,
    expires_at: null,
    error_code: null,
    error_message: null,
    ...overrides,
  }
}

function renderJobDetail() {
  return render(
    <MemoryRouter initialEntries={['/jobs/job-123']}>
      <Routes>
        <Route path="/jobs/:jobId" element={<JobDetail />} />
      </Routes>
    </MemoryRouter>,
  )
}

const POLL_MS = 2000
const FAKE_HANDLE = -1 as unknown as ReturnType<typeof setInterval>

// Capture JobDetail's poll interval callback so tests can trigger a poll
// tick on demand. Other intervals (e.g. RTL's internal waitFor polling)
// are passed through to the real timer functions untouched.
let intervalCallback: (() => unknown) | undefined

describe('JobDetail job-poll flow', () => {
  beforeEach(() => {
    intervalCallback = undefined
    const realSetInterval = globalThis.setInterval.bind(globalThis)
    const realClearInterval = globalThis.clearInterval.bind(globalThis)

    vi.spyOn(globalThis, 'setInterval').mockImplementation(
      ((cb: () => unknown, ms?: number, ...args: unknown[]) => {
        if (ms === POLL_MS) {
          intervalCallback = cb
          return FAKE_HANDLE
        }
        return realSetInterval(cb as TimerHandler, ms, ...args)
      }) as typeof setInterval,
    )

    vi.spyOn(globalThis, 'clearInterval').mockImplementation(((handle?: unknown) => {
      if (handle === FAKE_HANDLE) return
      realClearInterval(handle as Parameters<typeof clearInterval>[0])
    }) as typeof clearInterval)

    mockedFetchJob.mockReset()
    mockedFetchJobArtifacts.mockReset()
    mockedCancelJob.mockReset()
    mockedFetchJobArtifacts.mockResolvedValue([])
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  async function pollOnce() {
    await act(async () => {
      await intervalCallback?.()
    })
  }

  it('shows the queue position for a queued job', async () => {
    mockedFetchJob.mockResolvedValue(baseJob({ status: 'QUEUED', queue_position: 3 }))

    renderJobDetail()

    expect(await screen.findByText(/Queue position: 3/)).toBeInTheDocument()
  })

  it('polls for updates and shows progress while running', async () => {
    mockedFetchJob
      .mockResolvedValueOnce(baseJob({ status: 'QUEUED', queue_position: 1 }))
      .mockResolvedValueOnce(
        baseJob({ status: 'RUNNING', progress_percent: 40, progress_message: 'Working...' }),
      )

    renderJobDetail()
    await screen.findByText(/Queue position: 1/)

    await pollOnce()

    expect(screen.getByText(/Progress: 40%/)).toBeInTheDocument()
    expect(screen.getAllByText('Working...').length).toBeGreaterThan(0)
    expect(mockedFetchJob).toHaveBeenCalledTimes(2)
  })

  it('shows results once the job succeeds', async () => {
    mockedFetchJob
      .mockResolvedValueOnce(baseJob({ status: 'RUNNING', progress_percent: 90 }))
      .mockResolvedValueOnce(baseJob({ status: 'SUCCEEDED' }))

    const artifact: Artifact = {
      id: 'artifact-1',
      artifact_type: 'OUTPUT',
      file_name: 'result.png',
      content_type: 'image/png',
      size_bytes: 1234,
      storage_path: '/tmp/result.png',
      preview_supported: true,
      created_at: '2026-01-01T00:00:00Z',
      expires_at: null,
      job_id: 'job-123',
    }
    mockedFetchJobArtifacts.mockResolvedValue([artifact])

    renderJobDetail()
    await screen.findByText(/Progress: 90%/)

    await pollOnce()

    expect(screen.getByText('result.png')).toBeInTheDocument()
    expect(mockedFetchJobArtifacts).toHaveBeenCalledWith('job-123')
  })

  it('cancels a running job', async () => {
    mockedFetchJob.mockResolvedValue(baseJob({ status: 'RUNNING', progress_percent: 10 }))
    mockedCancelJob.mockResolvedValue(baseJob({ status: 'CANCELLED' }))

    renderJobDetail()
    await screen.findByText(/Progress: 10%/)

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /cancel job/i }))
    })

    expect(screen.getByText('Job was cancelled')).toBeInTheDocument()
    expect(mockedCancelJob).toHaveBeenCalledWith('job-123')
  })
})
