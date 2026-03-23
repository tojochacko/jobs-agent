import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import * as api from '../api/client'
import { ReviewPanel } from './ReviewPanel'

const mockApp = {
  id: 1, job_id: 1, status: 'pending',
  form_payload: JSON.stringify({ first_name: 'John', email: 'john@example.com' }),
  tailored_resume_text: 'Tailored resume text',
}

test('renders form fields for review', () => {
  render(<ReviewPanel application={mockApp} onClose={() => {}} />)
  expect(screen.getByText('first_name')).toBeInTheDocument()
  expect(screen.getByText('John')).toBeInTheDocument()
})

test('calls updateApplication with submitted on mark submitted', async () => {
  vi.spyOn(api, 'updateApplication').mockResolvedValue({ ...mockApp, status: 'submitted', applied_at: '2026-01-01' })
  const onClose = vi.fn()
  render(<ReviewPanel application={mockApp} onClose={onClose} />)
  fireEvent.click(screen.getByRole('button', { name: /mark as submitted/i }))
  await waitFor(() => expect(api.updateApplication).toHaveBeenCalledWith(1, { status: 'submitted' }))
  await waitFor(() => expect(onClose).toHaveBeenCalled())
})

test('shows manual required message when status is manual_required', () => {
  const manualApp = { ...mockApp, status: 'manual_required', form_payload: null }
  render(<ReviewPanel application={manualApp} onClose={() => {}} />)
  expect(screen.getByText(/manual required/i)).toBeInTheDocument()
})
