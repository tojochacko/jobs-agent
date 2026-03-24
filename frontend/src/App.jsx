import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { Dashboard } from './pages/Dashboard'
import { Preferences } from './pages/Preferences'
import { Applications } from './pages/Applications'
import { Outreach } from './pages/Outreach'
import { Settings } from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/preferences" element={<Preferences />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/outreach" element={<Outreach />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}
