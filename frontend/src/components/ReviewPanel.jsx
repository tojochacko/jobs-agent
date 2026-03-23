import { useState } from 'react'
import { updateApplication, openInBrowser } from '../api/client'

export function ReviewPanel({ application, onClose, onStatusChange }) {
  const [submitting, setSubmitting] = useState(false)

  const fields = (() => {
    try { return Object.entries(JSON.parse(application.form_payload || '{}')) }
    catch { return [] }
  })()

  const handleMarkSubmitted = () => {
    setSubmitting(true)
    updateApplication(application.id, { status: 'submitted' })
      .then((updated) => { onStatusChange?.(updated); onClose() })
      .finally(() => setSubmitting(false))
  }

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 20, marginTop: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Application Review</h3>
        <button onClick={onClose}>✕ Close</button>
      </div>

      {application.tailored_resume_text && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ margin: '0 0 8px' }}>Tailored Resume</h4>
          <pre style={{ background: '#f9fafb', padding: 12, borderRadius: 4, fontSize: 12, overflow: 'auto', maxHeight: 200, margin: 0 }}>
            {application.tailored_resume_text}
          </pre>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <h4 style={{ margin: '0 0 8px' }}>Pre-filled Form Fields</h4>
        {fields.length === 0
          ? <p style={{ color: '#6b7280', margin: 0 }}>No fields could be auto-filled.</p>
          : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: '4px 8px', color: '#374151' }}>Field</th>
                  <th style={{ textAlign: 'left', padding: '4px 8px', color: '#374151' }}>Value</th>
                </tr>
              </thead>
              <tbody>
                {fields.map(([k, v]) => (
                  <tr key={k} style={{ borderBottom: '1px solid #e5e7eb' }}>
                    <td style={{ padding: '6px 8px', color: '#6b7280' }}>{k}</td>
                    <td style={{ padding: '6px 8px' }}>{String(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        }
      </div>

      {application.status === 'manual_required'
        ? (
          <div style={{ padding: 12, background: '#fef3c7', borderRadius: 4 }}>
            <p style={{ margin: '0 0 8px' }}><strong>Manual Required:</strong> The form could not be auto-scraped. Please open the job URL manually.</p>
          </div>
        )
        : (
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => openInBrowser(application.id)}
              style={{ padding: '8px 16px', cursor: 'pointer' }}
            >
              Open in Browser (Pre-filled)
            </button>
            <button
              onClick={handleMarkSubmitted}
              disabled={submitting}
              style={{ padding: '8px 16px', cursor: 'pointer' }}
            >
              {submitting ? 'Saving…' : 'Mark as Submitted'}
            </button>
          </div>
        )
      }
    </div>
  )
}
