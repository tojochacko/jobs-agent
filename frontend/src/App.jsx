import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Preferences } from './pages/Preferences'
import { Applications } from './pages/Applications'
import { Outreach } from './pages/Outreach'
import { Settings } from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <nav style={{ padding: '12px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', gap: 16 }}>
        <Link to="/">Dashboard</Link>
        <Link to="/preferences">Preferences</Link>
        <Link to="/applications">Applications</Link>
        <Link to="/outreach">Outreach</Link>
        <Link to="/settings">Settings</Link>
      </nav>
      <main style={{ padding: 24 }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/preferences" element={<Preferences />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/outreach" element={<Outreach />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
