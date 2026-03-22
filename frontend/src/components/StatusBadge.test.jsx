import { render, screen } from '@testing-library/react'
import { StatusBadge } from './StatusBadge'

test('renders status text', () => {
  render(<StatusBadge status="new" />)
  expect(screen.getByText('new')).toBeInTheDocument()
})

test('renders match score as percentage', () => {
  render(<StatusBadge score={0.85} />)
  expect(screen.getByText('85%')).toBeInTheDocument()
})
