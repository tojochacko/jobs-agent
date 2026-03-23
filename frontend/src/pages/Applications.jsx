import { useEffect, useState } from 'react'
import { getApplications, getJobs } from '../api/client'

const PIPELINE = [
  { key: 'reviewing', label: 'Reviewing', statuses: ['pending', 'reviewing'] },
  { key: 'manual', label: 'Manual Required', statuses: ['manual_required'] },
  { key: 'applied', label: 'Applied', statuses: ['submitted'] },
  { key: 'response', label: 'Response', statuses: ['rejected', 'interviewing', 'offered'] },
]

export function Applications() {
  const [applications, setApplications] = useState([])
  const [jobs, setJobs] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([getApplications(), getJobs()])
      .then(([apps, jobList]) => {
        setApplications(apps)
        setJobs(Object.fromEntries(jobList.map(j => [j.id, j])))
      })
      .catch(() => setError('Failed to load applications. Please refresh.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p>Loading applications…</p>
  if (error) return <p style={{ color: '#dc2626' }}>{error}</p>

  return (
    <div>
      <h1>Applications Pipeline</h1>
      <div style={{ display: 'flex', gap: 16, overflowX: 'auto' }}>
        {PIPELINE.map(stage => {
          const stageApps = applications.filter(a => stage.statuses.includes(a.status))
          return (
            <div key={stage.key} style={{ minWidth: 220, flex: 1 }}>
              <h3 style={{ borderBottom: '2px solid #e5e7eb', paddingBottom: 8 }}>
                {stage.label} ({stageApps.length})
              </h3>
              {stageApps.length === 0
                ? <p style={{ color: '#9ca3af', fontSize: 13 }}>Empty</p>
                : stageApps.map(app => (
                  <div key={app.id} style={{ border: '1px solid #e5e7eb', borderRadius: 6, padding: 10, marginBottom: 8 }}>
                    <strong>{jobs[app.job_id]?.title || `Job #${app.job_id}`}</strong>
                    <p style={{ margin: '2px 0', fontSize: 12, color: '#6b7280' }}>
                      {jobs[app.job_id]?.company}
                    </p>
                    <span style={{ fontSize: 11, color: '#8b5cf6' }}>{app.status}</span>
                  </div>
                ))
              }
            </div>
          )
        })}
      </div>
    </div>
  )
}
