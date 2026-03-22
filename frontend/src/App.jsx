import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Preferences } from './pages/Preferences'

export default function App() {
  return (
    <BrowserRouter>
      <nav style={{ padding: '12px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', gap: 16 }}>
        <Link to="/">Dashboard</Link>
        <Link to="/preferences">Preferences</Link>
      </nav>
      <main style={{ padding: 24 }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/preferences" element={<Preferences />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
