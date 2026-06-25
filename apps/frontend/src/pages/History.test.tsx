import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import History from './History'
import * as api from '../api/api'

vi.mock('../api/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/api')>()
  return { ...actual, fetchMyHistory: vi.fn(), deleteMyHistory: vi.fn() }
})

const mockedFetch = api.fetchMyHistory as unknown as ReturnType<typeof vi.fn>
const mockedDelete = api.deleteMyHistory as unknown as ReturnType<typeof vi.fn>

function makeJob(overrides: Partial<api.Job> = {}): api.Job {
  return {
    id: 'job-1',
    space_id: 'space-1',
    space_name: 'Image Magic',
    user_id: 'user-1',
    status: 'SUCCEEDED',
    queue_position: null,
    progress_percent: 100,
    progress_message: null,
    created_at: '2024-01-15T10:00:00Z',
    started_at: null,
    finished_at: null,
    cancelled_at: null,
    expires_at: null,
    error_code: null,
    error_message: null,
    ...overrides,
  }
}

function renderHistory() {
  return render(
    <MemoryRouter>
      <History />
    </MemoryRouter>,
  )
}

describe('History page', () => {
  beforeEach(() => {
    mockedFetch.mockReset()
    mockedDelete.mockReset()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.spyOn(window, 'alert').mockImplementation(() => undefined)
  })

  it('shows loading state then renders jobs', async () => {
    mockedFetch.mockResolvedValue([makeJob()])
    renderHistory()
    expect(screen.getByText(/loading history/i)).toBeInTheDocument()
    expect(await screen.findByText('Image Magic')).toBeInTheDocument()
    expect(screen.getByText('1 job')).toBeInTheDocument()
  })

  it('shows plural label for multiple jobs', async () => {
    mockedFetch.mockResolvedValue([
      makeJob({ id: 'j1', created_at: '2024-01-16T10:00:00Z' }),
      makeJob({ id: 'j2', created_at: '2024-01-15T10:00:00Z' }),
    ])
    renderHistory()
    expect(await screen.findByText('2 jobs')).toBeInTheDocument()
  })

  it('shows error message when fetch fails', async () => {
    mockedFetch.mockRejectedValue(new Error('network error'))
    renderHistory()
    expect(await screen.findByText(/failed to load history/i)).toBeInTheDocument()
    expect(screen.getByText(/network error/i)).toBeInTheDocument()
  })

  it('shows empty state when no jobs exist', async () => {
    mockedFetch.mockResolvedValue([])
    renderHistory()
    expect(await screen.findByText(/haven't run any jobs/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /browse spaces/i })).toBeInTheDocument()
  })

  it('shows correct status pill for a failed job', async () => {
    mockedFetch.mockResolvedValue([makeJob({ status: 'FAILED' })])
    renderHistory()
    await screen.findByText('Image Magic')
    expect(screen.getByText('Failed')).toBeInTheDocument()
  })

  it('sorts jobs newest first', async () => {
    mockedFetch.mockResolvedValue([
      makeJob({ id: 'older', space_name: 'Older Space', created_at: '2024-01-10T00:00:00Z' }),
      makeJob({ id: 'newer', space_name: 'Newer Space', created_at: '2024-01-20T00:00:00Z' }),
    ])
    renderHistory()
    await screen.findByText('Newer Space')
    const items = screen.getAllByRole('listitem')
    expect(within(items[0]).getByText('Newer Space')).toBeInTheDocument()
    expect(within(items[1]).getByText('Older Space')).toBeInTheDocument()
  })

  it('deletes a job when Delete is clicked and confirmed', async () => {
    mockedFetch.mockResolvedValue([makeJob({ id: 'job-del' })])
    mockedDelete.mockResolvedValue(undefined)

    renderHistory()
    await screen.findByText('Image Magic')

    await userEvent.click(screen.getByRole('button', { name: /delete/i }))

    expect(mockedDelete).toHaveBeenCalledWith('job-del')
    expect(screen.queryByText('Image Magic')).not.toBeInTheDocument()
  })

  it('does not delete when the confirm dialog is cancelled', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    mockedFetch.mockResolvedValue([makeJob({ id: 'job-keep' })])

    renderHistory()
    await screen.findByText('Image Magic')
    await userEvent.click(screen.getByRole('button', { name: /delete/i }))

    expect(mockedDelete).not.toHaveBeenCalled()
    expect(screen.getByText('Image Magic')).toBeInTheDocument()
  })

  it('shows alert when delete fails', async () => {
    mockedFetch.mockResolvedValue([makeJob()])
    mockedDelete.mockRejectedValue(new Error('delete failed'))

    renderHistory()
    await screen.findByText('Image Magic')
    await userEvent.click(screen.getByRole('button', { name: /delete/i }))

    expect(window.alert).toHaveBeenCalledWith('delete failed')
    expect(screen.getByText('Image Magic')).toBeInTheDocument()
  })
})
