import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import { TagInput } from './TagInput'

describe('TagInput', () => {
  it('renders existing values as tags', () => {
    render(<TagInput values={['Python', 'React']} onChange={vi.fn()} />)
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('React')).toBeInTheDocument()
  })

  it('adds a tag on Enter and clears the input', () => {
    const onChange = vi.fn()
    render(<TagInput values={[]} onChange={onChange} />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'Go Engineer' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(onChange).toHaveBeenCalledWith(['Go Engineer'])
  })

  it('adds a tag on comma keydown', () => {
    const onChange = vi.fn()
    render(<TagInput values={[]} onChange={onChange} />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'DevOps' } })
    fireEvent.keyDown(input, { key: ',' })
    expect(onChange).toHaveBeenCalledWith(['DevOps'])
  })

  it('removes a tag when × is clicked', () => {
    const onChange = vi.fn()
    render(<TagInput values={['Python', 'React']} onChange={onChange} />)
    fireEvent.click(screen.getAllByRole('button')[0])
    expect(onChange).toHaveBeenCalledWith(['React'])
  })

  it('removes last tag on Backspace when input is empty', () => {
    const onChange = vi.fn()
    render(<TagInput values={['Python', 'React']} onChange={onChange} />)
    const input = screen.getByRole('textbox')
    fireEvent.keyDown(input, { key: 'Backspace' })
    expect(onChange).toHaveBeenCalledWith(['Python'])
  })

  it('does not add duplicate values', () => {
    const onChange = vi.fn()
    render(<TagInput values={['Python']} onChange={onChange} />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'Python' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(onChange).not.toHaveBeenCalled()
  })

  it('forwards id to the inner input', () => {
    render(<TagInput values={[]} onChange={vi.fn()} id="job_titles" />)
    expect(document.getElementById('job_titles')).toBeInTheDocument()
  })
})
