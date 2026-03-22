import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import { JobCard } from './JobCard'

const job = {
  id: 1, title: 'Senior Python Engineer', company: 'Acme Corp',
  location: 'Remote', match_score: 0.9, status: 'new',
  description: 'Build cool APIs with Python', url: 'https://acme.com/1', source: 'serpapi',
}

test('renders title and company', () => {
  render(<JobCard job={job} />)
  expect(screen.getByText('Senior Python Engineer')).toBeInTheDocument()
  expect(screen.getByText(/Acme Corp/)).toBeInTheDocument()
})

test('calls onDelete when dismiss clicked', () => {
  const onDelete = vi.fn()
  render(<JobCard job={job} onDelete={onDelete} />)
  fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
  expect(onDelete).toHaveBeenCalledWith(1)
})

test('shows webhook badge for webhook source', () => {
  render(<JobCard job={{ ...job, source: 'webhook' }} />)
  expect(screen.getByText(/webhook/i)).toBeInTheDocument()
})
