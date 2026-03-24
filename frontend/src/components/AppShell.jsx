// frontend/src/components/AppShell.jsx
import { NavLink } from 'react-router-dom'
import './AppShell.css'

const NAV_LINKS = [
  { to: '/',             label: 'Dashboard'    },
  { to: '/preferences',  label: 'Preferences'  },
  { to: '/applications', label: 'Applications' },
  { to: '/outreach',     label: 'Outreach'     },
  { to: '/settings',     label: 'Settings'     },
]

export function AppShell({ children }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-name">JobApplier</div>
          <div className="sidebar-brand-sub">Agent</div>
        </div>
        <nav className="sidebar-nav">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                'sidebar-link' + (isActive ? ' active' : '')
              }
            >
              <span className="sidebar-dot" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="app-main">{children}</main>
    </div>
  )
}
