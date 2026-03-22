// @vitest-environment node
import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  }
}))

describe('API client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getJobs calls GET /jobs', async () => {
    axios.get.mockResolvedValue({ data: [] })
    const { getJobs } = await import('./client.js')
    await getJobs()
    expect(axios.get).toHaveBeenCalledWith('/jobs')
  })

  it('savePreferences calls POST /preferences', async () => {
    axios.post.mockResolvedValue({ data: {} })
    const { savePreferences } = await import('./client.js')
    const prefs = { job_titles: ['Engineer'], location: 'Remote' }
    await savePreferences(prefs)
    expect(axios.post).toHaveBeenCalledWith('/preferences', prefs)
  })

  it('deleteJob calls DELETE /jobs/:id', async () => {
    axios.delete.mockResolvedValue({ data: {} })
    const { deleteJob } = await import('./client.js')
    await deleteJob(42)
    expect(axios.delete).toHaveBeenCalledWith('/jobs/42')
  })
})
