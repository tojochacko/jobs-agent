import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import * as api from '../api/client'
import { Applications } from './Applications'

test('renders all four pipeline stage headers', async () => {
  vi.spyOn(api, 'getApplications').mockResolvedValue([])
  vi.spyOn(api, 'getJobs').mockResolvedValue([])
  render(<Applications />)
  await waitFor(() => {
    expect(screen.getByText(/reviewing \(0\)/i)).toBeInTheDocument()
    expect(screen.getByText(/manual required \(0\)/i)).toBeInTheDocument()
    expect(screen.getByText(/applied \(0\)/i)).toBeInTheDocument()
    expect(screen.getByText(/response \(0\)/i)).toBeInTheDocument()
  })
})

test('displays application in the Applied stage column', async () => {
  vi.spyOn(api, 'getApplications').mockResolvedValue([
    { id: 1, job_id: 1, status: 'submitted' }
  ])
  vi.spyOn(api, 'getJobs').mockResolvedValue([
    { id: 1, title: 'Python Engineer', company: 'Acme', status: 'applied' }
  ])
  render(<Applications />)
  await waitFor(() => {
    // Applied column should show 1 application
    expect(screen.getByText(/applied \(1\)/i)).toBeInTheDocument()
    // The job title should appear
    expect(screen.getByText('Python Engineer')).toBeInTheDocument()
    // Other columns should remain empty
    expect(screen.getByText(/reviewing \(0\)/i)).toBeInTheDocument()
  })
})
