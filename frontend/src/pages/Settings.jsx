import { useState } from 'react'
import { connectEmail } from '../api/client'

export function Settings() {
  const [connecting, setConnecting] = useState(false)
  const webhookUrl = `${window.location.origin.replace('5173', '8000')}/webhook/job-alerts`
  const webhookSecret = '(set WEBHOOK_SECRET in backend .env)'

  const handleConnect = () => {
    setConnecting(true)
    connectEmail()
      .then(({ auth_url }) => window.open(auth_url, '_blank'))
      .finally(() => setConnecting(false))
  }

  return (
    <div>
      <h1>Settings</h1>
      <h2>Email Connection</h2>
      <p>Connect your Gmail or Outlook account to send cold emails.</p>
      <button onClick={handleConnect} disabled={connecting}>
        {connecting ? 'Opening…' : 'Connect Email Account'}
      </button>

      <h2>Webhook</h2>
      <p>Use this URL to receive job alerts from external agents:</p>
      <code style={{ display: 'block', background: '#f9fafb', padding: 8, borderRadius: 4, marginTop: 4 }}>
        {webhookUrl}
      </code>
      <p style={{ marginTop: 8 }}>Include header: <code>X-Webhook-Secret: {webhookSecret}</code></p>
    </div>
  )
}
