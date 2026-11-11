import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertCircle, ArrowRight, ArrowUpRight, Bell, Check,
  CheckCircle2, ChevronDown, ChevronRight, CircleHelp, Download, FileBarChart2,
  FileCheck2, FileClock, Filter, Globe2, Layers3, LockKeyhole, Menu, Plus, Radar,
  RefreshCw, Search, Settings2, Shield, ShieldAlert, ShieldCheck,
  Sparkles, Target as TargetIcon, X, Zap,
} from 'lucide-react';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: Layers3, group: 'Workspace' },
  { id: 'targets', label: 'Targets', icon: TargetIcon, group: 'Workspace' },
  { id: 'scans', label: 'Scans', icon: Radar, group: 'Workspace' },
  { id: 'findings', label: 'Findings', icon: ShieldAlert, group: 'Workspace' },
  { id: 'drift', label: 'Drift history', icon: Activity, group: 'Analysis' },
  { id: 'verification', label: 'Remediation', icon: FileCheck2, group: 'Analysis' },
  { id: 'reports', label: 'Reports', icon: FileBarChart2, group: 'Analysis' },
  { id: 'settings', label: 'Settings', icon: Settings2, group: 'System' },
];

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : 'The request could not be completed.';
    throw new Error(detail);
  }
  return body;
}

function timeAgo(date) {
  if (!date) return 'No activity yet';
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(date).getTime()) / 1000));
  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return new Date(date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function prettyDate(date) {
  return date ? new Date(date).toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';
}

function Badge({ children, tone = 'neutral', dot = false }) {
  return <span className={`badge badge-${tone}`}>{dot && <i />}{children}</span>;
}

function EmptyState({ icon: Icon = ShieldCheck, title, detail, action }) {
  return <div className="empty-state"><div className="empty-icon"><Icon size={19} /></div><h3>{title}</h3><p>{detail}</p>{action}</div>;
}

function Metric({ label, value, caption, icon: Icon, tone = 'blue', trend }) {
  return <article className="metric-card"><div className={`metric-icon metric-${tone}`}><Icon size={18} /></div><div className="metric-copy"><span>{label}</span><strong>{value}</strong><small>{caption}</small></div>{trend && <span className="metric-trend"><ArrowUpRight size={13} />{trend}</span>}</article>;
}

function Sparkline({ values }) {
  if (!values.length || values.every((v) => v === 0)) return <div className="chart-empty">Run a scan to start your history</div>;
  const max = Math.max(...values, 1);
  const points = values.map((v, i) => `${(i / Math.max(values.length - 1, 1)) * 100},${31 - (v / max) * 25}`).join(' ');
  return <svg className="sparkline" viewBox="0 0 100 36" preserveAspectRatio="none" aria-label="Findings per scan trend"><defs><linearGradient id="linefill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#42d6b0" stopOpacity=".2"/><stop offset="100%" stopColor="#42d6b0" stopOpacity="0"/></linearGradient></defs><polygon points={`0,36 ${points} 100,36`} fill="url(#linefill)"/><polyline points={points} fill="none" stroke="#42d6b0" strokeWidth="1.4" vectorEffect="non-scaling-stroke"/><line x1="0" y1="34" x2="100" y2="34" stroke="#263447" strokeDasharray="1 3" vectorEffect="non-scaling-stroke"/></svg>;
}

function App() {
  const [page, setPage] = useState('dashboard');
  const [targets, setTargets] = useState([]);
  const [scans, setScans] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [loading, setLoading] = useState(true);
  const [apiState, setApiState] = useState('checking');
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [showTargetModal, setShowTargetModal] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [toast, setToast] = useState('');

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    else setRefreshing(true);
    try {
      const freshTargets = await api('/api/targets');
      const scanGroups = await Promise.all(freshTargets.map(async (target) => {
        const rows = await api(`/api/targets/${target.id}/scans`);
        return rows.map((scan) => ({ ...scan, target_name: target.name, target_address: target.address }));
      }));
      const freshScans = scanGroups.flat().sort((a, b) => new Date(b.started_at) - new Date(a.started_at));
      const evidenceGroups = await Promise.all(freshScans.map(async (scan) => {
        const rows = await api(`/api/scans/${scan.id}/evidence`);
        return rows.map((row) => ({ ...row, scan, target_name: scan.target_name }));
      }));
      setTargets(freshTargets);
      setScans(freshScans);
      setEvidence(evidenceGroups.flat().sort((a, b) => new Date(b.observed_at) - new Date(a.observed_at)));
      setApiState('online');
      setError('');
    } catch (err) {
      setApiState('offline');
      setError(err.message || 'Could not connect to the DriftGuard API.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    if (!toast) return undefined;
    const timer = setTimeout(() => setToast(''), 3600);
    return () => clearTimeout(timer);
  }, [toast]);

  const current = NAV.find((item) => item.id === page) || NAV[0];
  const findingCounts = useMemo(() => evidence.reduce((acc, item) => { acc[item.severity] = (acc[item.severity] || 0) + 1; return acc; }, {}), [evidence]);
  const trendValues = useMemo(() => [...scans].reverse().slice(-8).map((scan) => evidence.filter((item) => item.scan_id === scan.id).length), [scans, evidence]);
  const filteredTargets = useMemo(() => targets.filter((target) => `${target.name} ${target.address}`.toLowerCase().includes(search.toLowerCase()) && (filter === 'all' || target.authorization_status === filter)), [targets, search, filter]);
  const filteredFindings = useMemo(() => evidence.filter((item) => `${item.title} ${item.category} ${item.resource} ${item.target_name}`.toLowerCase().includes(search.toLowerCase())), [evidence, search]);

  async function queueScan(target) {
    try {
      await api(`/api/targets/${target.id}/scans`, { method: 'POST' });
      setToast(`Scan request queued for ${target.name}`);
      await refresh(true);
    } catch (err) { setToast(err.message); }
  }

  async function createTarget(payload) {
    const target = await api('/api/targets', { method: 'POST', body: JSON.stringify(payload) });
    setToast(`${target.name} added to target inventory`);
    setShowTargetModal(false);
    await refresh(true);
  }

  function exportReport() {
    const rows = [['Target', 'Scan ID', 'Observed at', 'Category', 'Finding', 'Severity', 'Resource', 'Fingerprint']];
    evidence.forEach((item) => rows.push([item.target_name, item.scan_id, item.observed_at, item.category, item.title, item.severity, item.resource, item.fingerprint]));
    const csv = rows.map((row) => row.map((cell) => `"${String(cell ?? '').replaceAll('"', '""')}"`).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = `driftguard-evidence-${new Date().toISOString().slice(0, 10)}.csv`; link.click(); URL.revokeObjectURL(url);
    setToast('Evidence report exported');
  }

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Shield size={19} strokeWidth={2.2} /></div><div><strong>driftguard</strong><small>SECURITY INTELLIGENCE</small></div><button className="icon-button mobile-close" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X size={18}/></button></div>
      <div className="workspace-switch"><div className="workspace-avatar">R</div><div><strong>Research workspace</strong><small>Local environment</small></div><ChevronDown size={15} /></div>
      <nav className="side-nav" aria-label="Main navigation">
        {['Workspace', 'Analysis', 'System'].map((group) => <div className="nav-group" key={group}><div className="nav-label">{group}</div>{NAV.filter((item) => item.group === group).map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => { setPage(id); setMobileNav(false); setSearch(''); }}><Icon size={17} strokeWidth={1.8}/><span>{label}</span>{id === 'findings' && evidence.length > 0 && <i className="nav-count">{evidence.length}</i>}</button>)}</div>)}
      </nav>
      <div className="sidebar-bottom"><div className={`connection-card ${apiState}`}><span className="connection-dot"/><div><strong>{apiState === 'online' ? 'API connected' : apiState === 'checking' ? 'Connecting…' : 'API unavailable'}</strong><small>{apiState === 'online' ? 'Local backend' : '127.0.0.1:8000'}</small></div><button className="icon-button" onClick={() => refresh(true)} aria-label="Reconnect"><RefreshCw size={14}/></button></div><div className="user-card"><div className="user-avatar">M</div><div><strong>Research admin</strong><small>Local session</small></div><MoreMenu /></div></div>
    </aside>

    {mobileNav && <button className="nav-scrim" onClick={() => setMobileNav(false)} aria-label="Close navigation"/>}

    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="icon-button menu-toggle" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={20}/></button><div className="breadcrumbs"><span>DriftGuard</span><ChevronRight size={14}/><strong>{current.label}</strong></div></div><div className="topbar-right"><div className="environment-chip"><span/>Local test environment</div><div className="top-divider"/><button className="icon-button notification-button" aria-label="Notifications"><Bell size={18}/><i/></button><button className={`button button-secondary button-small ${refreshing ? 'is-loading' : ''}`} onClick={() => refresh(true)} disabled={refreshing}><RefreshCw size={14}/><span>Refresh</span></button></div></header>

      <div className="page-wrap">
        {error && <div className="error-banner"><AlertCircle size={17}/><div><strong>Backend connection failed</strong><span>{error} Start the API from <code>backend/</code> to load stored project data.</span></div><button className="icon-button" onClick={() => refresh(true)} aria-label="Retry"><RefreshCw size={15}/></button></div>}
        {page === 'dashboard' && <Dashboard targets={targets} scans={scans} evidence={evidence} findingCounts={findingCounts} trendValues={trendValues} loading={loading} onNavigate={setPage} onAdd={() => setShowTargetModal(true)} onScan={queueScan} />}
        {page === 'targets' && <TargetsPage targets={filteredTargets} allCount={targets.length} loading={loading} search={search} setSearch={setSearch} filter={filter} setFilter={setFilter} onAdd={() => setShowTargetModal(true)} onScan={queueScan} />}
        {page === 'scans' && <ScansPage scans={scans} targets={targets} loading={loading} onScan={queueScan} onNavigate={setPage} />}
        {page === 'findings' && <FindingsPage findings={filteredFindings} allCount={evidence.length} loading={loading} search={search} setSearch={setSearch} />}
        {page === 'drift' && <CapabilityPage icon={Activity} eyebrow="CHANGE INTELLIGENCE" title="Drift history" description="Track findings as they appear, persist, get fixed, or return across consecutive assessments." stage="Awaiting assessment engine" steps={['Baseline comparison rules are implemented in the backend.', 'The scan worker will write drift events when it stores assessment evidence.', 'History will populate automatically after the first completed comparison.']} />}
        {page === 'verification' && <CapabilityPage icon={FileCheck2} eyebrow="REMEDIATION ASSURANCE" title="Remediation verification" description="Keep administrator-reported fixes separate from technically verified outcomes." stage="Verification workflow in progress" steps={['Remediation records are included in the data model.', 'The assessment worker will re-check a reported issue against fresh evidence.', 'A finding will only be marked verified after a successful follow-up assessment.']} />}
        {page === 'reports' && <ReportsPage scans={scans} evidence={evidence} onExport={exportReport} />}
        {page === 'settings' && <SettingsPage apiState={apiState} apiBase={API_BASE} targetCount={targets.length} scanCount={scans.length} />}
      </div>
      <footer className="app-footer"><span><span className="footer-pulse"/>Evidence first. AI explanations are supplementary.</span><span>DriftGuard <b>0.1.0</b><i/>Local deployment</span></footer>
    </main>
    {showTargetModal && <TargetModal onClose={() => setShowTargetModal(false)} onSave={createTarget} />}
    {toast && <div className="toast"><CheckCircle2 size={17}/>{toast}<button onClick={() => setToast('')} aria-label="Dismiss"><X size={15}/></button></div>}
  </div>;
}

function MoreMenu() { return <button className="icon-button user-more" title="User menu"><ChevronDown size={15}/></button>; }

function Dashboard({ targets, scans, evidence, findingCounts, trendValues, loading, onNavigate, onAdd, onScan }) {
  const active = targets.filter((target) => target.status === 'active').length;
  const pending = targets.filter((target) => target.authorization_status !== 'authorized').length;
  const latest = scans.find((scan) => scan.status === 'completed');
  const latestEvidence = latest ? evidence.filter((item) => item.scan_id === latest.id) : [];
  const latestSeverityCounts = latestEvidence.reduce((acc, item) => { acc[item.severity] = (acc[item.severity] || 0) + 1; return acc; }, {});
  const topEvidence = evidence.slice(0, 5);
  const queued = scans.filter((scan) => scan.status === 'queued').length;
  return <>
    <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>POSTURE OVERVIEW</div><h1>Security at a glance<span className="heading-period">.</span></h1><p>A baseline-aware view of your registered application security.</p></div><div className="heading-actions"><button className="button button-secondary" onClick={() => onNavigate('reports')}><FileBarChart2 size={16}/>View reports</button><button className="button button-primary" onClick={onAdd}><Plus size={17}/>Add target</button></div></div>
    <div className="overview-strip"><div className="overview-indicator"><span className="overview-icon"><ShieldCheck size={19}/></span><div><strong>{loading ? 'Loading posture…' : targets.length ? 'Monitoring workspace' : 'Workspace ready'}</strong><small>{targets.length ? `${active} active asset${active === 1 ? '' : 's'} · ${pending} awaiting authorization` : 'Register an authorized target to begin'}</small></div></div><div className="overview-meta"><span className="live-dot"/>Updated {timeAgo(latest?.started_at || targets[0]?.created_at)}<span className="overview-divider"/><span>Last assessment</span><b>{latest ? prettyDate(latest.started_at) : '—'}</b></div></div>
    <section className="metric-grid">
      <Metric label="Registered targets" value={loading ? '—' : targets.length} caption={`${active} active in workspace`} icon={Globe2} tone="blue" />
      <Metric label="Assessment runs" value={loading ? '—' : scans.length} caption={queued ? `${queued} queued · execution not active` : 'Stored scan history'} icon={Radar} tone="violet" />
      <Metric label="Recorded evidence" value={loading ? '—' : evidence.length} caption={evidence.length ? `${findingCounts.High || 0} high · ${findingCounts.Medium || 0} medium` : 'No evidence recorded yet'} icon={ShieldAlert} tone="amber" />
      <Metric label="Verified remediations" value="—" caption="Verification workflow not active" icon={ShieldCheck} tone="green" />
    </section>
    <section className="dashboard-grid">
      <article className="panel trend-panel"><div className="panel-head"><div><div className="panel-kicker">ASSESSMENT ACTIVITY</div><h2>Finding trend</h2></div><div className="trend-range"><span className="trend-dot"/>Findings per scan</div></div><div className="chart-area"><div className="chart-y-labels"><span>{Math.max(1, ...trendValues)}</span><span>{Math.ceil(Math.max(1, ...trendValues) / 2)}</span><span>0</span></div><div className="chart-content"><div className="chart-gridlines"><i/><i/><i/></div><Sparkline values={trendValues}/><div className="chart-x-labels">{scans.length ? [...scans].reverse().slice(-4).map((scan) => <span key={scan.id}>#{scan.id}</span>) : <><span>Baseline</span><span>+1</span><span>+2</span><span>Current</span></>}</div></div></div><div className="panel-foot"><span><i className="mini-pulse"/>Counts use stored evidence from the API</span><button className="text-button" onClick={() => onNavigate('scans')}>Scan history <ArrowRight size={14}/></button></div></article>
      <article className="panel risk-panel"><div className="panel-head"><div><div className="panel-kicker">LATEST ASSESSMENT</div><h2>Evidence by severity</h2></div><button className="icon-button panel-more" title="Findings view" onClick={() => onNavigate('findings')}><ArrowRight size={16}/></button></div><div className="risk-total"><strong>{latestEvidence.length}</strong><span>{latest ? `scan #${latest.id}` : 'no completed assessment'}</span></div><div className="risk-bars">{[['Critical', 'critical'], ['High', 'high'], ['Medium', 'medium'], ['Low', 'low'], ['Informational', 'info']].map(([name, tone]) => { const count = latestSeverityCounts[name] || 0; return <div className="risk-row" key={name}><span>{name}</span><div className="risk-track"><i className={`risk-fill ${tone}`} style={{ width: latestEvidence.length ? `${Math.max(count ? 5 : 0, (count / latestEvidence.length) * 100)}%` : '0%' }}/></div><b>{count}</b></div>; })}</div><button className="panel-link" onClick={() => onNavigate('findings')}>Explore findings <ArrowRight size={14}/></button></article>
    </section>
    <section className="lower-grid"><article className="panel assets-panel"><div className="panel-head"><div><div className="panel-kicker">INVENTORY</div><h2>Monitored targets</h2></div><button className="text-button" onClick={() => onNavigate('targets')}>All targets <ArrowRight size={14}/></button></div>{targets.length ? <div className="table-wrap"><table><thead><tr><th>Target</th><th>Scope</th><th>Authorization</th><th>Last scan</th><th/></tr></thead><tbody>{targets.slice(0, 5).map((target) => { const last = scans.find((scan) => scan.target_id === target.id); return <tr key={target.id}><td><div className="target-cell"><span className="table-target-icon"><Globe2 size={16}/></span><span><strong>{target.name}</strong><small>{target.address}</small></span></div></td><td><span className="scope-list">{target.approved_scope?.length ? target.approved_scope.map((scope) => scope.replace('_', '/')).join(' · ') : 'No scope'}</span></td><td><Badge tone={target.authorization_status === 'authorized' ? 'green' : 'amber'} dot>{target.authorization_status}</Badge></td><td className="muted-cell">{last ? timeAgo(last.started_at) : 'Never'}</td><td><button className="icon-button row-arrow" onClick={() => target.authorization_status === 'authorized' && onScan(target)} disabled={target.authorization_status !== 'authorized'} title={target.authorization_status === 'authorized' ? 'Queue scan' : 'Authorization required'}><ArrowRight size={15}/></button></td></tr>; })}</tbody></table></div> : <EmptyState icon={TargetIcon} title="No targets registered" detail="Add an explicitly authorized asset to start recording its security posture." action={<button className="button button-primary button-small" onClick={onAdd}><Plus size={15}/>Register a target</button>}/>}</article>
      <article className="panel activity-panel"><div className="panel-head"><div><div className="panel-kicker">LATEST EVIDENCE</div><h2>Recent findings</h2></div><button className="text-button" onClick={() => onNavigate('findings')}>View all <ArrowRight size={14}/></button></div>{topEvidence.length ? <div className="activity-list">{topEvidence.map((item) => <div className="activity-item" key={item.id}><span className={`severity-mark ${String(item.severity).toLowerCase()}`}><ShieldAlert size={15}/></span><div className="activity-copy"><strong>{item.title}</strong><span>{item.target_name} <i/> {item.category} <i/> scan #{item.scan_id}</span></div><Badge tone={severityTone(item.severity)}>{item.severity}</Badge></div>)}</div> : <EmptyState icon={ShieldCheck} title="Nothing detected yet" detail={targets.length ? 'Stored assessment evidence will appear here after a scan completes.' : 'Findings are always sourced from stored assessment evidence.'}/>}</article></section>
    <div className="dashboard-bottom"><div className="readiness-card"><div className="readiness-symbol"><Zap size={18}/></div><div><strong>{targets.length ? 'Ready to assess' : 'Set up your first target'}</strong><span>{targets.length ? 'Assessment runs are gated by each target’s authorization and approved scope.' : 'Target registration captures the approved assessment scope before any scan can be requested.'}</span></div><button className="button button-quiet" onClick={() => targets.length ? onNavigate('targets') : onAdd()}>{targets.length ? 'Review inventory' : 'Register target'}<ArrowRight size={14}/></button></div><div className="research-note"><LockKeyhole size={15}/><span>Local-first storage</span><i/>No external AI processing configured</div></div>
  </>;
}

function TargetsPage({ targets, allCount, loading, search, setSearch, filter, setFilter, onAdd, onScan }) {
  return <><div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>ASSET INVENTORY</div><h1>Targets<span className="heading-period">.</span></h1><p>Manage registered assets and their approved assessment boundaries.</p></div><button className="button button-primary" onClick={onAdd}><Plus size={17}/>Register target</button></div><div className="list-toolbar"><div className="toolbar-count"><strong>{allCount}</strong> registered target{allCount === 1 ? '' : 's'}</div><div className="toolbar-controls"><label className="search-field"><Search size={16}/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search targets"/></label><label className="select-field"><Filter size={14}/><select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">All authorization</option><option value="authorized">Authorized</option><option value="pending">Pending</option></select><ChevronDown size={13}/></label></div></div><div className="panel page-table-panel">{targets.length ? <div className="table-wrap"><table className="wide-table"><thead><tr><th>Target / endpoint</th><th>Type</th><th>Approved scope</th><th>Approved ports</th><th>Authorization</th><th>Status</th><th>Created</th><th/></tr></thead><tbody>{targets.map((target) => <tr key={target.id}><td><div className="target-cell"><span className="table-target-icon"><Globe2 size={16}/></span><span><strong>{target.name}</strong><small>{target.address}</small></span></div></td><td><span className="type-label">{target.target_type}</span></td><td>{target.approved_scope?.length ? target.approved_scope.map((scope) => <span className="scope-chip" key={scope}>{scope.replace('_', '/')}</span>) : <span className="muted-cell">Not set</span>}</td><td className="muted-cell">{target.approved_ports?.length ? target.approved_ports.join(', ') : '—'}</td><td><Badge tone={target.authorization_status === 'authorized' ? 'green' : 'amber'} dot>{target.authorization_status}</Badge></td><td><Badge tone={target.status === 'active' ? 'blue' : 'neutral'}>{target.status}</Badge></td><td className="muted-cell">{prettyDate(target.created_at)}</td><td><button className="button button-quiet button-small" disabled={target.status !== 'active' || target.authorization_status !== 'authorized' || !target.approved_scope?.length} onClick={() => onScan(target)}><Radar size={14}/>Queue scan</button></td></tr>)}</tbody></table></div> : loading ? <div className="loading-state"><span className="spinner"/>Loading registered targets…</div> : <EmptyState icon={TargetIcon} title={allCount ? 'No matching targets' : 'Your inventory is empty'} detail={allCount ? 'Try another name or authorization filter.' : 'Register a target and record its authorization and assessment scope before requesting a scan.'} action={!allCount && <button className="button button-primary button-small" onClick={onAdd}><Plus size={15}/>Register a target</button>}/>}</div><div className="inline-note"><LockKeyhole size={15}/><span>Scan requests are rejected by the API unless the target is active, explicitly authorized, and has an approved scope.</span></div></>;
}

function ScansPage({ scans, targets, loading, onScan, onNavigate }) {
  return <><div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>ASSESSMENT RECORDS</div><h1>Scans<span className="heading-period">.</span></h1><p>Historical assessment requests and their stored evidence.</p></div><div className="heading-actions"><span className="count-pill"><Radar size={14}/>{scans.length} records</span></div></div><div className="panel page-table-panel">{scans.length ? <div className="table-wrap"><table className="wide-table"><thead><tr><th>Assessment</th><th>Target</th><th>Status</th><th>Baseline</th><th>Started</th><th>Evidence</th></tr></thead><tbody>{scans.map((scan) => <tr key={scan.id}><td><div className="scan-id"><span className="scan-icon"><Radar size={15}/></span><strong>Scan #{scan.id}</strong></div></td><td><div className="table-target"><strong>{scan.target_name}</strong><small>{scan.target_address}</small></div></td><td><Badge tone={scan.status === 'completed' ? 'green' : scan.status === 'failed' ? 'red' : 'blue'} dot>{scan.status}</Badge></td><td>{scan.is_baseline ? <Badge tone="violet">Baseline</Badge> : <span className="muted-cell">Follow-up</span>}</td><td className="muted-cell">{prettyDate(scan.started_at)}</td><td><EvidenceCount scan={scan}/></td></tr>)}</tbody></table></div> : loading ? <div className="loading-state"><span className="spinner"/>Loading assessment records…</div> : <EmptyState icon={Radar} title="No scan records yet" detail="Authorized targets can receive scan requests. Requests remain queued until the assessment worker is connected." action={<button className="button button-secondary button-small" onClick={() => onNavigate('targets')}>Review targets<ArrowRight size={14}/></button>}/>}</div><div className="notice-card notice-blue"><div className="notice-icon"><CircleHelp size={17}/></div><div><strong>Assessment execution is not connected yet</strong><span>Queued records represent a request only. No network assessment has run and no security status is implied.</span></div><span className="notice-state">FOUNDATION</span></div>{targets.some((target) => target.authorization_status === 'authorized') && <div className="quick-queue"><span>Authorized assets</span>{targets.filter((target) => target.authorization_status === 'authorized').slice(0, 3).map((target) => <button key={target.id} className="button button-quiet button-small" onClick={() => onScan(target)}><Plus size={13}/>{target.name}</button>)}</div>}</>;
}

function EvidenceCount({ scan }) {
  const [count, setCount] = useState('—');
  useEffect(() => { api(`/api/scans/${scan.id}/evidence`).then((rows) => setCount(rows.length)).catch(() => setCount('—')); }, [scan.id]);
  return <span className="evidence-count"><span/>{count} findings</span>;
}

function FindingsPage({ findings, allCount, loading, search, setSearch }) {
  return <><div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>SECURITY EVIDENCE</div><h1>Findings<span className="heading-period">.</span></h1><p>Structured observations recorded by completed assessments.</p></div><span className="count-pill"><ShieldAlert size={14}/>{allCount} evidence items</span></div><div className="list-toolbar"><div className="toolbar-count">{allCount ? <><strong>{findings.length}</strong> shown from {allCount} evidence items</> : 'Evidence-backed findings only'}</div><label className="search-field"><Search size={16}/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search findings"/></label></div><div className="panel page-table-panel">{findings.length ? <div className="table-wrap"><table className="wide-table"><thead><tr><th>Finding</th><th>Target</th><th>Category</th><th>Severity</th><th>Observed</th><th>Scan</th></tr></thead><tbody>{findings.map((finding) => <tr key={finding.id}><td><div className="finding-cell"><span className={`severity-mark ${String(finding.severity).toLowerCase()}`}><ShieldAlert size={15}/></span><span><strong>{finding.title}</strong><small>{finding.resource}</small></span></div></td><td className="muted-cell">{finding.target_name}</td><td><span className="category-chip">{finding.category}</span></td><td><Badge tone={severityTone(finding.severity)} dot>{finding.severity}</Badge></td><td className="muted-cell">{prettyDate(finding.observed_at)}</td><td className="muted-cell">#{finding.scan_id}</td></tr>)}</tbody></table></div> : loading ? <div className="loading-state"><span className="spinner"/>Loading evidence…</div> : <EmptyState icon={ShieldCheck} title={allCount ? 'No findings match this search' : 'No evidence recorded'} detail={allCount ? 'Adjust the search term to find another evidence record.' : 'This view stays empty until completed assessments store evidence in the backend.'}/>}</div><div className="inline-note"><LockKeyhole size={15}/><span>Assessment evidence is authoritative. Findings are never generated from sample dashboard data.</span></div></>;
}

function CapabilityPage({ icon: Icon, eyebrow, title, description, stage, steps }) {
  return <><div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>{eyebrow}</div><h1>{title}<span className="heading-period">.</span></h1><p>{description}</p></div></div><div className="capability-layout"><section className="capability-hero panel"><div className="capability-glow"/><div className="capability-icon"><Icon size={22}/></div><Badge tone="amber" dot>{stage}</Badge><h2>Built for evidence<br/>over assumptions.</h2><p>This area is connected to the research workflow and will populate from persisted backend records as those modules come online.</p><div className="capability-rule"/><div className="capability-foot"><span><LockKeyhole size={14}/>No simulated records</span><span>DRIFTGUARD CORE</span></div></section><section className="panel roadmap-panel"><div className="panel-kicker">WORKFLOW STATUS</div><h2>What happens next</h2><div className="roadmap-list">{steps.map((step, index) => <div className="roadmap-item" key={step}><span className={`roadmap-number ${index === 0 ? 'complete' : ''}`}>{index === 0 ? <Check size={13}/> : `0${index + 1}`}</span><div><strong>{index === 0 ? 'In place' : index === 1 ? 'Next integration' : 'Follows verification'}</strong><span>{step}</span></div>{index === 0 && <CheckCircle2 size={16} className="roadmap-check"/>}</div>)}</div><div className="roadmap-note"><Sparkles size={15}/><span>AI remains optional and cannot determine finding state or drift classification.</span></div></section></div></>;
}

function ReportsPage({ scans, evidence, onExport }) {
  return <><div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>RESEARCH OUTPUT</div><h1>Reports<span className="heading-period">.</span></h1><p>Export an evidence register from records currently stored by the backend.</p></div><button className="button button-primary" onClick={onExport} disabled={!evidence.length}><Download size={16}/>Export evidence CSV</button></div><section className="report-summary"><article className="report-summary-card"><div className="report-icon"><FileBarChart2 size={18}/></div><div><small>Scan records</small><strong>{scans.length}</strong></div><span>Stored in backend</span></article><article className="report-summary-card"><div className="report-icon report-icon-teal"><ShieldCheck size={18}/></div><div><small>Evidence records</small><strong>{evidence.length}</strong></div><span>Exportable to CSV</span></article><article className="report-summary-card"><div className="report-icon report-icon-violet"><Activity size={18}/></div><div><small>Drift events</small><strong>—</strong></div><span>Comparison worker pending</span></article></section><section className="panel report-panel"><div className="panel-head"><div><div className="panel-kicker">AVAILABLE OUTPUT</div><h2>Evidence register</h2></div><Badge tone={evidence.length ? 'green' : 'neutral'} dot>{evidence.length ? 'Ready' : 'No evidence yet'}</Badge></div><p className="report-description">A comma-separated export of findings currently stored in completed scan records. The export includes the target name, scan identifier, observation time, category, finding title, severity, resource and stable fingerprint.</p><div className="report-file"><div className="file-symbol"><FileBarChart2 size={18}/></div><div><strong>DriftGuard evidence register</strong><small>CSV · generated locally in your browser · {evidence.length} rows</small></div><button className="button button-secondary button-small" onClick={onExport} disabled={!evidence.length}><Download size={14}/>Download</button></div>{!evidence.length && <div className="report-empty"><FileClock size={15}/>Reports become available when backend scans contain persisted evidence.</div>}</section></>;
}

function SettingsPage({ apiState, apiBase, targetCount, scanCount }) {
  return <><div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>SYSTEM CONFIGURATION</div><h1>Settings<span className="heading-period">.</span></h1><p>Local API connection and research data status.</p></div></div><div className="settings-grid"><section className="panel settings-panel"><div className="panel-head"><div><div className="panel-kicker">CONNECTION</div><h2>Backend API</h2></div><Badge tone={apiState === 'online' ? 'green' : apiState === 'offline' ? 'red' : 'amber'} dot>{apiState}</Badge></div><div className="setting-row"><div><strong>API base URL</strong><span>Configured through <code>VITE_API_URL</code></span></div><code className="setting-value">{apiBase}</code></div><div className="setting-row"><div><strong>Connection security</strong><span>Development instance bound to loopback</span></div><span className="setting-state"><LockKeyhole size={14}/>Local only</span></div><div className="setting-row"><div><strong>Authentication</strong><span>Administrator authentication is not implemented yet</span></div><Badge tone="amber">Not enabled</Badge></div></section><section className="panel settings-panel"><div className="panel-head"><div><div className="panel-kicker">DATA FOOTPRINT</div><h2>Stored records</h2></div><Layers3 size={17} className="panel-icon-muted"/></div><div className="data-stats"><div><strong>{targetCount}</strong><span>Targets</span></div><div><strong>{scanCount}</strong><span>Scan records</span></div></div><div className="setting-row"><div><strong>Database</strong><span>SQLite, configured in backend environment</span></div><Badge tone="blue">Local</Badge></div><div className="setting-row"><div><strong>External AI</strong><span>Optional integration is not configured</span></div><Badge tone="neutral">Disabled</Badge></div></section></div><div className="notice-card notice-amber"><div className="notice-icon"><AlertCircle size={17}/></div><div><strong>Research deployment note</strong><span>This workspace does not demonstrate a hosting location or data-sovereignty arrangement. No Uganda data-residency claim is made.</span></div></div></>;
}

function TargetModal({ onClose, onSave }) {
  const [form, setForm] = useState({ name: '', address: '', target_type: 'web', authorization_status: 'pending', approved_scope: [], approved_ports: '', status: 'active' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const toggleScope = (scope) => setForm((prev) => ({ ...prev, approved_scope: prev.approved_scope.includes(scope) ? prev.approved_scope.filter((item) => item !== scope) : [...prev.approved_scope, scope] }));
  async function submit(event) {
    event.preventDefault(); setSaving(true); setError('');
    try { await onSave({ ...form, approved_ports: form.approved_ports.trim() ? form.approved_ports.split(',').map((item) => Number(item.trim())) : [] }); }
    catch (err) { setError(err.message || 'Could not register this target.'); }
    finally { setSaving(false); }
  }
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="target-modal" role="dialog" aria-modal="true" aria-labelledby="target-title"><div className="modal-head"><div><div className="eyebrow"><span className="eyebrow-line"/>TARGET INVENTORY</div><h2 id="target-title">Register a target</h2><p>Set the asset and its explicit assessment boundaries.</p></div><button className="icon-button" onClick={onClose} aria-label="Close"><X size={18}/></button></div><form onSubmit={submit}><label className="form-label">Target name<input autoFocus required maxLength="120" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="e.g. Local eServices portal"/></label><label className="form-label">Hostname or origin URL<input required value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} placeholder="https://localhost:8443"/><small>Do not include paths, credentials, query parameters, or fragments.</small></label><div className="form-two"><label className="form-label">Target type<select value={form.target_type} onChange={(event) => setForm({ ...form, target_type: event.target.value })}><option value="web">Web application</option><option value="api">API</option><option value="host">Network host</option></select></label><label className="form-label">Authorization status<select value={form.authorization_status} onChange={(event) => setForm({ ...form, authorization_status: event.target.value })}><option value="pending">Pending authorization</option><option value="authorized">Authorized for testing</option></select><small>Only select authorized when permission is documented.</small></label></div><fieldset className="scope-fieldset"><legend>Approved assessment scope</legend><div className="scope-options">{[['tls', 'TLS / SSL'], ['network', 'Network exposure'], ['http_api', 'HTTP / API']].map(([value, label]) => <label key={value} className={`scope-option ${form.approved_scope.includes(value) ? 'selected' : ''}`}><input type="checkbox" checked={form.approved_scope.includes(value)} onChange={() => toggleScope(value)}/><span className="scope-check">{form.approved_scope.includes(value) && <Check size={12}/>}</span>{label}</label>)}</div></fieldset><label className="form-label">Approved ports <span className="optional-label">Optional · comma separated</span><input value={form.approved_ports} onChange={(event) => setForm({ ...form, approved_ports: event.target.value })} placeholder="443, 8443"/></label>{error && <div className="form-error"><AlertCircle size={15}/>{error}</div>}<div className="modal-security"><LockKeyhole size={14}/><span>Requests can only be queued after authorization and scope are recorded.</span></div><div className="modal-actions"><button type="button" className="button button-secondary" onClick={onClose}>Cancel</button><button type="submit" className="button button-primary" disabled={saving || !form.approved_scope.length}>{saving ? <><span className="spinner spinner-small"/>Saving…</> : <><Plus size={15}/>Register target</>}</button></div></form></section></div>;
}

function severityTone(severity) {
  return ({ Critical: 'red', High: 'orange', Medium: 'amber', Low: 'blue', Informational: 'neutral' })[severity] || 'neutral';
}

export default App;
