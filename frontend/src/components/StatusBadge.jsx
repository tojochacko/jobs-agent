const STATUS_COLORS = {
  new: '#3b82f6', saved: '#8b5cf6', dismissed: '#6b7280',
  applying: '#f59e0b', applied: '#22c55e', error: '#ef4444',
  emailing: '#f59e0b', emailed: '#22c55e',
}

export function StatusBadge({ status, score }) {
  const style = { color: '#fff', padding: '2px 8px', borderRadius: 4, fontSize: 12 }
  if (score !== undefined) {
    const pct = Math.round(score * 100)
    const bg = pct >= 80 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#ef4444'
    return <span style={{ ...style, background: bg }}>{pct}%</span>
  }
  return <span style={{ ...style, background: STATUS_COLORS[status] || '#6b7280' }}>{status}</span>
}
