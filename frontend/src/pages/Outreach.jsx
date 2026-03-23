import { useEffect, useState } from 'react'
import { getOutreach, getJobs } from '../api/client'

export function Outreach() {
  const [records, setRecords] = useState([])
  const [jobs, setJobs] = useState({})

  useEffect(() => {
    getOutreach().then(setRecords)
    getJobs().then(js => setJobs(Object.fromEntries(js.map(j => [j.id, j]))))
  }, [])

  return (
    <div>
      <h1>Outreach History</h1>
      {records.length === 0
        ? <p style={{ color: '#9ca3af' }}>No outreach records yet.</p>
        : records.map(r => (
          <div key={r.id} style={{ border: '1px solid #e5e7eb', borderRadius: 6, padding: 12, marginBottom: 8 }}>
            <strong>{jobs[r.job_id]?.title}</strong> at {jobs[r.job_id]?.company}
            <p style={{ margin: '4px 0', fontSize: 13, color: '#6b7280' }}>
              To: {r.hr_name || 'Unknown'} &lt;{r.hr_email || '—'}&gt;
            </p>
            <span style={{
              fontSize: 11, padding: '2px 6px', borderRadius: 4,
              background: r.status === 'sent' ? '#22c55e' : '#f59e0b', color: '#fff'
            }}>
              {r.status}
            </span>
            {r.sent_at && <span style={{ fontSize: 11, color: '#6b7280', marginLeft: 8 }}>
              {new Date(r.sent_at).toLocaleString()}
            </span>}
          </div>
        ))
      }
    </div>
  )
}
