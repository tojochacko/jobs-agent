// frontend/src/pages/Preferences.test.jsx
import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import * as api from '../api/client'
import { Preferences } from './Preferences'

test('renders the preferences form', async () => {
  vi.spyOn(api, 'getPreferences').mockResolvedValue(null)
  vi.spyOn(api, 'getResume').mockResolvedValue(null)
  render(<Preferences />)
  await waitFor(() => expect(screen.getByLabelText(/job titles/i)).toBeInTheDocument())
})
