import { useState } from 'react'
import { StatusBadge } from './StatusBadge'
import { triggerApply } from '../api/client'
import { ReviewPanel } from './ReviewPanel'

export function JobCard({ job, onDelete }) {
  const [applying, setApplying] = useState(false)
  const [application, setApplication] = useState(null)
  const [applyError, setApplyError] = useState(null)

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div>
          <h3 style={{ margin: 0 }}>{job.title}</h3>
          <p style={{ margin: '4px 0', color: '#6b7280' }}>{job.company} · {job.location}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <StatusBadge score={job.match_score} />
          <StatusBadge status={job.status} />
          {job.source === 'webhook' && (
            <span style={{ fontSize: 11, color: '#8b5cf6' }}>via webhook</span>
          )}
        </div>
      </div>
      <p style={{ fontSize: 14, color: '#374151', marginTop: 8 }}>
        {job.description?.slice(0, 200)}{job.description?.length > 200 ? '…' : ''}
      </p>
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <a href={job.url} target="_blank" rel="noopener noreferrer">
          <button>View Job</button>
        </a>
        <button
          disabled={applying || ['applying', 'applied', 'emailing', 'emailed'].includes(job.status)}
          onClick={() => {
            setApplying(true)
            setApplyError(null)
            triggerApply(job.id)
              .then(app => setApplication(app))
              .catch(err => setApplyError(err?.response?.data?.detail || 'Apply failed. Please try again.'))
              .finally(() => setApplying(false))
          }}
        >
          {applying ? 'Preparing…' : 'Apply'}
        </button>
        <button disabled title="Available in Phase 3">Email HR</button>
        <button onClick={() => onDelete?.(job.id)} aria-label="Dismiss">Dismiss</button>
      </div>
      {applyError && (
        <p style={{ color: '#dc2626', fontSize: 13, margin: '8px 0 0' }}>{applyError}</p>
      )}
      {application && (
        <ReviewPanel
          application={application}
          onClose={() => setApplication(null)}
          onStatusChange={(updated) => setApplication(updated)}
        />
      )}
    </div>
  )
}
