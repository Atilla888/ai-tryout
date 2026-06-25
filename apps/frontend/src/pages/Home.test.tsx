import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Home from './Home'
import * as api from '../api/api'

vi.mock('../api/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/api')>()
  return { ...actual, fetchSpaces: vi.fn() }
})

const mockedFetchSpaces = api.fetchSpaces as unknown as ReturnType<typeof vi.fn>

const spaces: api.Space[] = [
  {
    id: 'space-1',
    name: 'Image Magic',
    slug: 'image-magic',
    description: 'Generate images from text prompts',
    task_type: 'Image',
    input_types: ['Text'],
    output_types: ['Image'],
    status: 'published',
    visibility: 'public',
  },
  {
    id: 'space-2',
    name: 'Voice Clone',
    slug: 'voice-clone',
    description: 'Clone a voice from an audio sample',
    task_type: 'Audio',
    input_types: ['Audio'],
    output_types: ['Audio'],
    status: 'published',
    visibility: 'public',
  },
]

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  )
}

describe('Home page', () => {
  beforeEach(() => {
    mockedFetchSpaces.mockReset()
  })

  it('shows a loading state and then lists available spaces', async () => {
    mockedFetchSpaces.mockResolvedValue(spaces)

    renderHome()

    expect(screen.getByText(/loading spaces/i)).toBeInTheDocument()

    expect(await screen.findByText('Image Magic')).toBeInTheDocument()
    expect(screen.getByText('Voice Clone')).toBeInTheDocument()
    expect(screen.getByText('2 spaces available')).toBeInTheDocument()
  })

  it('filters spaces by search query', async () => {
    mockedFetchSpaces.mockResolvedValue(spaces)

    renderHome()
    await screen.findByText('Image Magic')

    await userEvent.type(screen.getByPlaceholderText(/search spaces/i), 'voice')

    expect(screen.queryByText('Image Magic')).not.toBeInTheDocument()
    expect(screen.getByText('Voice Clone')).toBeInTheDocument()
    expect(screen.getByText('1 space available')).toBeInTheDocument()
  })

  it('filters spaces by task type chip', async () => {
    mockedFetchSpaces.mockResolvedValue(spaces)

    renderHome()
    await screen.findByText('Image Magic')

    await userEvent.click(screen.getByText('Audio', { selector: '.chip' }))

    expect(screen.queryByText('Image Magic')).not.toBeInTheDocument()
    expect(screen.getByText('Voice Clone')).toBeInTheDocument()
  })

  it('shows an error state when the API call fails', async () => {
    mockedFetchSpaces.mockRejectedValue(new Error('network error'))

    renderHome()

    expect(await screen.findByText(/unable to load spaces/i)).toBeInTheDocument()
  })
})
