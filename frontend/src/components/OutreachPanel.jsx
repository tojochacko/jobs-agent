import { useState } from 'react'
import { patchOutreach, sendOutreach } from '../api/client'

const CONFIDENCE_COLORS = {
  search_result: '#22c55e',
  inferred_pattern: '#f59e0b',
  unknown: '#ef4444',
}

export function OutreachPanel({ record: initialRecord, onClose, onSent }) {
  const [record, setRecord] = useState(initialRecord)
  const [sending, setSending] = useState(false)

  const handleFieldChange = (field) => (e) => {
    const value = e.target.value
    setRecord(r => ({ ...r, [field]: value }))
    patchOutreach(record.id, { [field]: value })
  }

  const handleSend = () => {
    setSending(true)
    sendOutreach(record.id)
      .then(updated => { setRecord(updated); onSent?.(updated); onClose() })
      .catch(err => alert(err.response?.data?.detail || 'Send failed'))
      .finally(() => setSending(false))
  }

  const confidenceColor = CONFIDENCE_COLORS[record.hr_confidence] || '#6b7280'

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 20, marginTop: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <h3>Email HR</h3>
        <button onClick={onClose}>✕ Close</button>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label><strong>HR Contact</strong></label>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 4 }}>
          <input value={record.hr_name || ''} onChange={handleFieldChange('hr_name')}
            placeholder="Name" style={{ flex: 1 }} />
          <input value={record.hr_email || ''} onChange={handleFieldChange('hr_email')}
            placeholder="Email" style={{ flex: 2 }} />
          <span style={{ fontSize: 11, color: confidenceColor, whiteSpace: 'nowrap' }}>
            {record.hr_confidence}
          </span>
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label><strong>Cover Letter</strong></label>
        <textarea
          value={record.cover_letter || ''}
          onChange={handleFieldChange('cover_letter')}
          rows={10}
          style={{ width: '100%', marginTop: 4, fontFamily: 'inherit', fontSize: 13 }}
        />
      </div>

      {record.resume_version_path && (
        <p style={{ fontSize: 13, color: '#6b7280' }}>
          Attachment: {record.resume_version_path.split('/').pop()}
        </p>
      )}

      {record.status === 'sent'
        ? <p style={{ color: '#22c55e' }}>✓ Email sent at {new Date(record.sent_at).toLocaleString()}</p>
        : (
          <button onClick={handleSend} disabled={sending || !record.hr_email} aria-label="Send Email">
            {sending ? 'Sending…' : 'Send Email'}
          </button>
        )
      }
    </div>
  )
}
