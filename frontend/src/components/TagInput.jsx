// frontend/src/components/TagInput.jsx
import { useState, useRef } from 'react'
import './TagInput.css'

export function TagInput({ values, onChange, placeholder = 'Add, press Enter', id }) {
  const [input, setInput] = useState('')
  const inputRef = useRef(null)

  const addTag = () => {
    const trimmed = input.trim().replace(/,$/, '')
    if (trimmed && !values.includes(trimmed)) {
      onChange([...values, trimmed])
    }
    setInput('')
  }

  const removeTag = (index) => {
    onChange(values.filter((_, i) => i !== index))
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addTag()
    } else if (e.key === 'Backspace' && input === '') {
      onChange(values.slice(0, -1))
    }
  }

  return (
    <div
      className="tag-input-container"
      onClick={() => inputRef.current?.focus()}
    >
      {values.map((val, i) => (
        <span key={val} className="tag">
          {val}
          <button
            type="button"
            className="tag-remove"
            onClick={(e) => { e.stopPropagation(); removeTag(i) }}
            aria-label={`Remove ${val}`}
          >
            ×
          </button>
        </span>
      ))}
      <input
        ref={inputRef}
        id={id}
        className="tag-input"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={values.length === 0 ? placeholder : ''}
      />
    </div>
  )
}
