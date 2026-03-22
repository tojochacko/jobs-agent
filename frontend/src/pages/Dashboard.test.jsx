// frontend/src/pages/Dashboard.test.jsx
import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import * as api from '../api/client'
import { Dashboard } from './Dashboard'

const mockJobs = [{
  id: 1, title: 'Python Engineer', company: 'Acme', location: 'Remote',
  match_score: 0.9, status: 'new', description: 'Build APIs', url: 'https://acme.com/1', source: 'serpapi',
}]

test('renders job cards from API', async () => {
  vi.spyOn(api, 'getJobs').mockResolvedValue(mockJobs)
  render(<Dashboard />)
  await waitFor(() => expect(screen.getByText('Python Engineer')).toBeInTheDocument())
})

test('shows empty state when no jobs', async () => {
  vi.spyOn(api, 'getJobs').mockResolvedValue([])
  render(<Dashboard />)
  await waitFor(() => expect(screen.getByText(/no jobs found/i)).toBeInTheDocument())
})
