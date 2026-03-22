import { useEffect, useState } from 'react'
import { getPreferences, savePreferences, uploadResume, getResume } from '../api/client'

export function Preferences() {
  const [form, setForm] = useState({
    job_titles: '', location: '', remote_hybrid: 'any',
    experience_level: '', domain: '', company_size: '', poll_interval_hrs: 6,
  })
  const [resume, setResume] = useState(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getPreferences().then(pref => {
      if (pref) setForm({
        job_titles: pref.job_titles.join(', '),
        location: pref.location || '',
        remote_hybrid: pref.remote_hybrid || 'any',
        experience_level: pref.experience_level || '',
        domain: pref.domain || '',
        company_size: (pref.company_size || []).join(', '),
        poll_interval_hrs: pref.poll_interval_hrs || 6,
      })
    })
    getResume().then(setResume)
  }, [])

  const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }))

  const handleSave = (e) => {
    e.preventDefault()
    savePreferences({
      ...form,
      job_titles: form.job_titles.split(',').map(s => s.trim()).filter(Boolean),
      company_size: form.company_size.split(',').map(s => s.trim()).filter(Boolean),
      poll_interval_hrs: Number(form.poll_interval_hrs),
    }).then(() => setSaved(true))
  }

  const handleResumeUpload = (e) => {
    const file = e.target.files[0]
    if (file) uploadResume(file).then(setResume)
  }

  return (
    <div>
      <h1>Preferences</h1>
      <form onSubmit={handleSave}>
        <div><label htmlFor="job_titles">Job Titles (comma-separated)</label>
          <input id="job_titles" value={form.job_titles} onChange={set('job_titles')} /></div>
        <div><label htmlFor="location">Location</label>
          <input id="location" value={form.location} onChange={set('location')} /></div>
        <div><label htmlFor="remote_hybrid">Work Arrangement</label>
          <select id="remote_hybrid" value={form.remote_hybrid} onChange={set('remote_hybrid')}>
            <option value="any">Any</option><option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option><option value="onsite">Onsite</option>
          </select></div>
        <div><label htmlFor="experience_level">Experience Level</label>
          <input id="experience_level" value={form.experience_level} onChange={set('experience_level')} /></div>
        <div><label htmlFor="domain">Domain</label>
          <input id="domain" value={form.domain} onChange={set('domain')} /></div>
        <div><label htmlFor="company_size">Company Size (comma-separated)</label>
          <input id="company_size" value={form.company_size} onChange={set('company_size')} /></div>
        <div><label htmlFor="poll_interval_hrs">Poll Interval (hours)</label>
          <input id="poll_interval_hrs" type="number" min="1" value={form.poll_interval_hrs} onChange={set('poll_interval_hrs')} /></div>
        <button type="submit">Save Preferences</button>
        {saved && <span style={{ color: 'green', marginLeft: 8 }}>Saved!</span>}
      </form>
      <h2>Resume</h2>
      {resume && <p>Current: <strong>{resume.filename}</strong></p>}
      <input type="file" accept=".pdf,.docx" onChange={handleResumeUpload} />
    </div>
  )
}
