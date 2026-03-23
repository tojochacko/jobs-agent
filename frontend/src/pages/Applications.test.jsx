import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import * as api from '../api/client'
import { Applications } from './Applications'

test('renders pipeline stage headers', async () => {
  vi.spyOn(api, 'getApplications').mockResolvedValue([])
  vi.spyOn(api, 'getJobs').mockResolvedValue([])
  render(<Applications />)
  await waitFor(() => {
    expect(screen.getByText(/reviewing/i)).toBeInTheDocument()
    expect(screen.getByText(/applied/i)).toBeInTheDocument()
    expect(screen.getByText(/response/i)).toBeInTheDocument()
  })
})

test('displays application in correct pipeline stage', async () => {
  vi.spyOn(api, 'getApplications').mockResolvedValue([
    { id: 1, job_id: 1, status: 'submitted' }
  ])
  vi.spyOn(api, 'getJobs').mockResolvedValue([
    { id: 1, title: 'Python Engineer', company: 'Acme', status: 'applied' }
  ])
  render(<Applications />)
  await waitFor(() => {
    expect(screen.getByText('Python Engineer')).toBeInTheDocument()
  })
})
