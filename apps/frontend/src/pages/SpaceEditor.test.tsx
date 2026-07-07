import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import SpaceEditor from './SpaceEditor'
import * as api from '../api/api'
import type { CreatorSpace } from '../api/api'

vi.mock('../api/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/api')>()
  return {
    ...actual,
    fetchMySpaces: vi.fn(),
    createCreatorSpace: vi.fn(),
    updateCreatorSpace: vi.fn(),
    validateCreatorSpace: vi.fn(),
  }
})

const mockedFetchMySpaces = api.fetchMySpaces as unknown as ReturnType<typeof vi.fn>
const mockedCreate = api.createCreatorSpace as unknown as ReturnType<typeof vi.fn>
const mockedUpdate = api.updateCreatorSpace as unknown as ReturnType<typeof vi.fn>
const mockedValidate = api.validateCreatorSpace as unknown as ReturnType<typeof vi.fn>

const draftSpace: CreatorSpace = {
  id: 'space-1',
  slug: 'my-space',
  name: 'My Space',
  description: 'desc',
  task_type: 'Text',
  input_types: [],
  output_types: [],
  owner_id: 'owner-1',
  owner_number: 1,
  container_image: 'img:latest',
  ui_config: { inputs: [] },
  runner_config: {},
  visibility: 'PRIVATE',
  status: 'DRAFT',
  created_at: '2026-01-01T00:00:00Z',
}

function renderEditor(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/creator" element={<div>My Spaces list</div>} />
        <Route path="/creator/spaces/new" element={<SpaceEditor />} />
        <Route path="/creator/spaces/:spaceId/edit" element={<SpaceEditor />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('SpaceEditor', () => {
  beforeEach(() => {
    mockedFetchMySpaces.mockReset()
    mockedCreate.mockReset()
    mockedUpdate.mockReset()
    mockedValidate.mockReset()
    mockedFetchMySpaces.mockResolvedValue([])
  })

  it('auto-generates the slug from the name until the slug is edited manually', async () => {
    renderEditor('/creator/spaces/new')

    const nameInput = screen.getByPlaceholderText('My Space')
    const slugInput = screen.getByPlaceholderText('my-space')

    await userEvent.type(nameInput, 'Hello World')
    expect(slugInput).toHaveValue('hello-world')

    // Once the user edits the slug, it stops tracking the name.
    await userEvent.clear(slugInput)
    await userEvent.type(slugInput, 'custom')
    await userEvent.type(nameInput, ' Again')
    expect(slugInput).toHaveValue('custom')
  })

  it('Save as Draft calls the create API with the expected payload', async () => {
    mockedCreate.mockResolvedValue({ ...draftSpace, id: 'new-id' })

    renderEditor('/creator/spaces/new')

    await userEvent.type(screen.getByPlaceholderText('My Space'), 'My Space')
    await userEvent.type(screen.getByPlaceholderText('ghcr.io/org/model:latest'), 'img:latest')
    await userEvent.click(screen.getByRole('button', { name: /save as draft/i }))

    await waitFor(() => expect(mockedCreate).toHaveBeenCalledTimes(1))
    const payload = mockedCreate.mock.calls[0][0]
    expect(payload).toMatchObject({
      name: 'My Space',
      slug: 'my-space',
      container_image: 'img:latest',
      visibility: 'PRIVATE',
      status: 'DRAFT',
    })
    expect(payload.ui_config.inputs).toEqual([
      { name: '', type: 'text', label: '', required: false },
    ])
    expect(payload.runner_config).toEqual({})
  })

  it('shows an error and does not call the API when runner_config JSON is invalid', async () => {
    renderEditor('/creator/spaces/new')

    const runnerConfig = screen.getByDisplayValue('{}')
    await userEvent.clear(runnerConfig)
    await userEvent.type(runnerConfig, 'not valid json')

    await userEvent.click(screen.getByRole('button', { name: /save as draft/i }))

    expect(
      await screen.findByText(/runner_config must be a valid JSON object/i),
    ).toBeInTheDocument()
    expect(mockedCreate).not.toHaveBeenCalled()
  })

  it('keeps the space in DRAFT and shows the error when publish validation fails', async () => {
    mockedFetchMySpaces.mockResolvedValue([draftSpace])
    mockedUpdate.mockResolvedValue(draftSpace)
    mockedValidate.mockResolvedValue({
      valid: false,
      errors: [{ field: 'ui_config.inputs', message: 'At least one input is required' }],
    })

    renderEditor('/creator/spaces/space-1/edit')

    // Wait for the existing space to load into the form.
    await screen.findByDisplayValue('My Space')

    await userEvent.click(screen.getByRole('button', { name: /^publish$/i }))

    // The message appears both in the validation summary and the field banner.
    expect((await screen.findAllByText(/At least one input is required/i)).length).toBeGreaterThan(0)
    expect(screen.getByText(/Fix validation errors before publishing/i)).toBeInTheDocument()
    // Validation ran and the space was reverted to DRAFT.
    expect(mockedValidate).toHaveBeenCalledWith('space-1')
    expect(mockedUpdate).toHaveBeenCalledWith('space-1', { status: 'DRAFT' })
    expect(screen.getByText('DRAFT')).toBeInTheDocument()
  })
})
