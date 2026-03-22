import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('axios')

describe('API client', () => {
  let axios

  beforeEach(async () => {
    vi.resetModules()
    axios = (await import('axios')).default
  })

  it('getJobs calls GET /jobs', async () => {
    axios.get = vi.fn().mockResolvedValue({ data: [] })
    const { getJobs } = await import('./client.js')
    await getJobs()
    expect(axios.get).toHaveBeenCalledWith('/jobs')
  })

  it('savePreferences calls POST /preferences', async () => {
    axios.post = vi.fn().mockResolvedValue({ data: {} })
    const { savePreferences } = await import('./client.js')
    const prefs = { job_titles: ['Engineer'], location: 'Remote' }
    await savePreferences(prefs)
    expect(axios.post).toHaveBeenCalledWith('/preferences', prefs)
  })

  it('deleteJob calls DELETE /jobs/:id', async () => {
    axios.delete = vi.fn().mockResolvedValue({ data: {} })
    const { deleteJob } = await import('./client.js')
    await deleteJob(42)
    expect(axios.delete).toHaveBeenCalledWith('/jobs/42')
  })
})
