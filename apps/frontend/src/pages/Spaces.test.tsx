import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useParams } from 'react-router-dom'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Spaces from './Spaces'
import * as api from '../api/api'
import type { SpaceDetail } from '../api/api'

vi.mock('react-oidc-context', () => ({
  useAuth: () => ({ isAuthenticated: false, isLoading: false, user: null }),
}))

vi.mock('../api/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/api')>()
  return {
    ...actual,
    fetchSpace: vi.fn(),
    submitJob: vi.fn(),
    fetchMyHistory: vi.fn(),
    fetchJobArtifacts: vi.fn(),
  }
})

const mockedFetchSpace = api.fetchSpace as unknown as ReturnType<typeof vi.fn>
const mockedSubmitJob = api.submitJob as unknown as ReturnType<typeof vi.fn>
const mockedFetchMyHistory = api.fetchMyHistory as unknown as ReturnType<typeof vi.fn>

const space: SpaceDetail = {
  id: 'space-1',
  name: 'Image Magic',
  slug: 'image-magic',
  description: 'Generate images from text prompts',
  task_type: 'Image',
  input_types: ['Text'],
  output_types: ['Image'],
  status: 'published',
  visibility: 'public',
  owner_id: null,
  owner_number: null,
  container_image: null,
  resource_requirements: {},
  ui_config: {
    inputs: [{ name: 'prompt', type: 'text', label: 'Prompt', required: true }],
  },
  runner_config: {},
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function JobPageStub() {
  const { jobId } = useParams<{ jobId: string }>()
  return <div>Job page {jobId}</div>
}

function renderSpaces() {
  return render(
    <MemoryRouter initialEntries={['/spaces/space-1']}>
      <Routes>
        <Route path="/spaces/:spaceId" element={<Spaces />} />
        <Route path="/jobs/:jobId" element={<JobPageStub />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Spaces submit flow', () => {
  beforeEach(() => {
    mockedFetchSpace.mockReset()
    mockedSubmitJob.mockReset()
    mockedFetchMyHistory.mockReset()
    mockedFetchSpace.mockResolvedValue(space)
    mockedFetchMyHistory.mockResolvedValue([])
  })

  it('shows a validation error and does not submit when required fields are empty', async () => {
    renderSpaces()
    await screen.findByText('Image Magic', { selector: '.space-heading' })

    await userEvent.click(screen.getByRole('button', { name: /submit/i }))

    expect(await screen.findByText(/prompt is required/i)).toBeInTheDocument()
    expect(mockedSubmitJob).not.toHaveBeenCalled()
  })

  it('submits the form and navigates to the job detail page', async () => {
    mockedSubmitJob.mockResolvedValue({ id: 'job-123', status: 'QUEUED', queue_position: 1 })

    renderSpaces()
    await screen.findByText('Image Magic', { selector: '.space-heading' })

    await userEvent.type(screen.getByLabelText(/prompt/i), 'a cat in space')
    await userEvent.click(screen.getByRole('button', { name: /submit/i }))

    expect(await screen.findByText('Job page job-123')).toBeInTheDocument()
    expect(mockedSubmitJob).toHaveBeenCalledTimes(1)
    expect(mockedSubmitJob.mock.calls[0][0]).toBe('space-1')
    expect(mockedSubmitJob.mock.calls[0][1]).toBeInstanceOf(FormData)
    expect((mockedSubmitJob.mock.calls[0][1] as FormData).get('prompt')).toBe('a cat in space')
  })

  it('shows an alert when submission fails', async () => {
    mockedSubmitJob.mockRejectedValue(new Error('boom'))
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})

    renderSpaces()
    await screen.findByText('Image Magic', { selector: '.space-heading' })

    await userEvent.type(screen.getByLabelText(/prompt/i), 'a cat in space')
    await userEvent.click(screen.getByRole('button', { name: /submit/i }))

    expect(await screen.findByRole('button', { name: /submit/i })).toBeEnabled()
    expect(alertSpy).toHaveBeenCalledWith('Failed to submit job. Please try again.')

    alertSpy.mockRestore()
  })
})
