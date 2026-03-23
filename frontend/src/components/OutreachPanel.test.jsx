import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import * as api from '../api/client'
import { OutreachPanel } from './OutreachPanel'

const mockRecord = {
  id: 1, job_id: 1, hr_name: 'Jane Smith', hr_email: 'jane@acme.com',
  hr_confidence: 'search_result', cover_letter: 'Dear Jane...', status: 'draft', sent_at: null,
}

test('renders HR contact and cover letter', () => {
  render(<OutreachPanel record={mockRecord} onClose={() => {}} />)
  expect(screen.getByDisplayValue('jane@acme.com')).toBeInTheDocument()
  expect(screen.getByDisplayValue('Dear Jane...')).toBeInTheDocument()
})

test('calls sendOutreach on Send click', async () => {
  vi.spyOn(api, 'sendOutreach').mockResolvedValue({ ...mockRecord, status: 'sent' })
  render(<OutreachPanel record={mockRecord} onClose={() => {}} />)
  fireEvent.click(screen.getByRole('button', { name: /send email/i }))
  await waitFor(() => expect(api.sendOutreach).toHaveBeenCalledWith(1))
})
