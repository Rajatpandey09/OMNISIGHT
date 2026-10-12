
import { useState } from 'react'
import './App.css'

const scans = [
  { name: 'Demo Store', url: 'demo-store.local', viewport: 'Desktop + Mobile', date: 'Today, 10:42 AM', status: 'Completed', issues: 8 },
  { name: 'Marketing Website', url: 'marketing.local', viewport: 'Desktop', date: 'Today, 09:18 AM', status: 'Review needed', issues: 3 },
  { name: 'Dashboard UI', url: 'dashboard.local', viewport: 'Mobile', date: 'Yesterday', status: 'Completed', issues: 2 },
  { name: 'Portfolio Site', url: 'portfolio.local', viewport: 'Desktop + Mobile', date: 'Yesterday', status: 'Failed', issues: 0 },
]

const issues = [
  { title: 'Button overflows viewport', page: '/products', severity: 'High', type: 'Layout' },
  { title: 'Heading overlaps navigation', page: '/home', severity: 'Medium', type: 'Responsive' },
  { title: 'Low contrast text', page: '/checkout', severity: 'Low', type: 'Accessibility' },
]

function Icon({ name }) {
  const icons = {
    grid: '▦', scan: '◎', issues: '△', settings: '⚙',
    search: '⌕', bell: '♧', arrow: '↗', clock: '◷',
    check: '✓', menu: '☰', plus: '+', dots: '···',
  }
  return <span className="icon" aria-hidden="true">{icons[name] || '•'}</span>
}

function App() {
  const [page, setPage] = useState('Overview')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [notice, setNotice] = useState('')

  const navItems = [
    { label: 'Overview', icon: 'grid' },
    { label: 'Scans', icon: 'scan' },
    { label: 'Issues', icon: 'issues' },
    { label: 'Settings', icon: 'settings' },
  ]

  function runScan() {
    setPage('Scans')
    setNotice('Demo mode: backend scanning is not connected yet.')
  }

  return (
    <div className="app-shell">
      {mobileOpen && <button className="mobile-overlay" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <a className="brand" href="#" onClick={() => setPage('Overview')}>
          <span className="brand-mark">O</span>
          <span>omni<span className="brand-light">sight</span><small>VISUAL QA PLATFORM</small></span>
        </a>

        <div className="workspace-label">WORKSPACE</div>
        <button className="workspace-select" onClick={() => setNotice('You are viewing the demo workspace.')}>
          <span className="workspace-avatar">O</span>
          <span className="workspace-name">OmniSight Team<small>Free workspace</small></span>
          <span className="chevron">⌄</span>
        </button>

        <div className="nav-label">PLATFORM</div>
        <nav className="navigation">
          {navItems.map(item => (
            <button key={item.label} className={`nav-item ${page === item.label ? 'active' : ''}`}
              onClick={() => { setPage(item.label); setNotice(''); setMobileOpen(false) }}>
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.label === 'Issues' && <span className="nav-count">13</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="usage-card">
            <div className="usage-top"><span>Scan usage</span><span>64%</span></div>
            <div className="usage-track"><div /></div>
            <p>32 of 50 demo scans used</p>
          </div>
          <button className="profile">
            <span className="profile-avatar">R</span>
            <span className="profile-info">Rajat Pandey<small>Frontend developer</small></span>
            <Icon name="dots" />
          </button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button className="mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Icon name="menu" /></button>
          <div className="breadcrumb">Workspace <span>/</span> <strong>{page}</strong></div>
          <div className="topbar-actions">
            <span className="demo-pill"><span /> DEMO ENVIRONMENT</span>
            <button className="icon-button" aria-label="Notifications" onClick={() => setNotice('No new notifications in demo mode.')}><Icon name="bell" /></button>
            <span className="top-avatar">R</span>
          </div>
        </header>

        <div className="content">
          {notice && <div className="notice"><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss">×</button></div>}

          {page === 'Overview' && <>
            <section className="page-heading">
              <div><div className="eyebrow">YOUR QUALITY COMMAND CENTER</div><h1>Overview<span className="heading-dot">.</span></h1><p>Monitor visual quality and track issues across your websites.</p></div>
              <button className="primary-button" onClick={runScan}><Icon name="plus" /> Run a scan</button>
            </section>

            <div className="demo-warning"><span className="warning-symbol">i</span><span><strong>Preview data</strong> — These metrics are illustrative and are not live scan results.</span></div>

            <section className="stats-grid">
              <article className="stat-card"><div className="stat-heading"><span>Total scans</span><span className="stat-icon cyan"><Icon name="scan" /></span></div><div className="stat-value">48</div><div className="stat-foot"><span className="positive">↗ 12%</span><span>vs. previous period</span></div><div className="sparkline cyan-line"><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/></div></article>
              <article className="stat-card"><div className="stat-heading"><span>Issues detected</span><span className="stat-icon orange"><Icon name="issues" /></span></div><div className="stat-value">126</div><div className="stat-foot"><span className="positive">↘ 8%</span><span>vs. previous period</span></div><div className="sparkline orange-line"><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/></div></article>
              <article className="stat-card"><div className="stat-heading"><span>Verified fixes</span><span className="stat-icon green"><Icon name="check" /></span></div><div className="stat-value">84</div><div className="stat-foot"><span className="muted">66.7% </span><span>of detected issues</span></div><div className="sparkline green-line"><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/></div></article>
              <article className="stat-card"><div className="stat-heading"><span>Pending reviews</span><span className="stat-icon purple"><Icon name="clock" /></span></div><div className="stat-value">9</div><div className="stat-foot"><span className="attention">Needs attention</span><span>· awaiting review</span></div><div className="sparkline purple-line"><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/></div></article>
            </section>

            <section className="panel scan-panel">
              <div className="panel-heading"><div><h2>Recent scans</h2><p>A quick look at your latest test runs</p></div><button className="text-button" onClick={() => setPage('Scans')}>View all scans <Icon name="arrow" /></button></div>
              <div className="table-wrap"><table><thead><tr><th>TARGET</th><th>VIEWPORT</th><th>ISSUES</th><th>STATUS</th><th>DATE</th><th></th></tr></thead>
                <tbody>{scans.slice(0, 3).map((scan, i) => <tr key={scan.name}><td><div className="target-cell"><span className={`target-icon target-${i}`}>{scan.name.charAt(0)}</span><span><strong>{scan.name}</strong><small>{scan.url}</small></span></div></td><td>{scan.viewport}</td><td><span className="issue-number">{scan.issues}</span></td><td><span className={`status ${scan.status === 'Completed' ? 'status-done' : 'status-review'}`}><i />{scan.status}</span></td><td className="date-cell">{scan.date}</td><td><button className="row-action" onClick={() => { setPage('Scans'); setNotice(`Showing demo scan: ${scan.name}`) }} aria-label={`View ${scan.name}`}>↗</button></td></tr>)}</tbody>
              </table></div>
              <button className="mobile-view-all" onClick={() => setPage('Scans')}>View all scans <Icon name="arrow" /></button>
            </section>

            <section className="panel issues-panel">
              <div className="panel-heading"><div><h2>Issues to review</h2><p>Examples of detected visual defects</p></div><button className="text-button" onClick={() => setPage('Issues')}>All issues <Icon name="arrow" /></button></div>
              <div className="issues-list">{issues.map(issue => <div className="issue-row" key={issue.title}><span className={`severity-dot severity-${issue.severity.toLowerCase()}`} /><div className="issue-description"><strong>{issue.title}</strong><small>{issue.page} <span>·</span> {issue.type}</small></div><span className={`severity-label severity-label-${issue.severity.toLowerCase()}`}>{issue.severity}</span><button className="row-action" onClick={() => { setPage('Issues'); setNotice(`Demo issue selected: ${issue.title}`) }} aria-label={`View ${issue.title}`}>↗</button></div>)}</div>
            </section>
          </>}

          {page === 'Scans' && <section className="page-section"><div className="page-heading"><div><div className="eyebrow">TEST RUN HISTORY</div><h1>Scans<span className="heading-dot">.</span></h1><p>Review previous scans and their outcomes.</p></div><button className="primary-button" onClick={runScan}><Icon name="plus" /> Run a scan</button></div><div className="panel"><div className="panel-heading"><div><h2>All scans</h2><p>Illustrative sample records</p></div></div><div className="table-wrap"><table><thead><tr><th>TARGET</th><th>VIEWPORT</th><th>ISSUES</th><th>STATUS</th><th>DATE</th></tr></thead><tbody>{scans.map(scan => <tr key={scan.name}><td><div className="target-cell"><span className="target-icon">{scan.name.charAt(0)}</span><span><strong>{scan.name}</strong><small>{scan.url}</small></span></div></td><td>{scan.viewport}</td><td>{scan.issues}</td><td><span className={`status ${scan.status === 'Completed' ? 'status-done' : 'status-review'}`}><i />{scan.status}</span></td><td className="date-cell">{scan.date}</td></tr>)}</tbody></table></div></div></section>}

          {page === 'Issues' && <section className="page-section"><div className="page-heading"><div><div className="eyebrow">VISUAL DEFECT TRACKER</div><h1>Issues<span className="heading-dot">.</span></h1><p>Review example defects found during visual testing.</p></div></div><div className="panel"><div className="panel-heading"><div><h2>Issue queue</h2><p>Demo issues only — no live scan data</p></div><span className="demo-pill">3 EXAMPLES</span></div><div className="issues-list">{issues.map(issue => <div className="issue-row" key={issue.title}><span className={`severity-dot severity-${issue.severity.toLowerCase()}`} /><div className="issue-description"><strong>{issue.title}</strong><small>{issue.page} <span>·</span> {issue.type}</small></div><span className={`severity-label severity-label-${issue.severity.toLowerCase()}`}>{issue.severity}</span></div>)}</div></div></section>}

          {page === 'Settings' && <section className="page-section"><div className="page-heading"><div><div className="eyebrow">PREFERENCES</div><h1>Settings<span className="heading-dot">.</span></h1><p>Application configuration preview.</p></div></div><div className="panel settings-card"><h2>Workspace settings</h2><p>Backend integration is not configured yet.</p><div className="setting-row"><div><strong>API connection</strong><small>Configure this when the FastAPI backend is ready.</small></div><span className="status status-review"><i />Not connected</span></div><div className="setting-row"><div><strong>Data mode</strong><small>Dashboard currently uses illustrative demo data.</small></div><span className="demo-pill">DEMO</span></div></div></section>}

          <footer className="footer"><span><span className="footer-dot" /> OmniSight <span className="footer-separator">/</span> Visual QA workspace</span><span>Frontend preview · v0.1.0</span></footer>
        </div>
      </main>
    </div>
  )
}

export default App
