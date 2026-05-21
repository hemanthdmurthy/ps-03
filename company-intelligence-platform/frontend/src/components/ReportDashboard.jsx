// ReportDashboard.jsx
import React, { useState, useEffect } from 'react'
import { 
  FileText, AlertTriangle, Search, ChevronDown, ChevronRight, CheckCircle, Database, RefreshCw
} from 'lucide-react'

export default function ReportDashboard({ report, rawOutputs, sessionId }) {
  const [activeTab, setActiveTab] = useState(null)

  // State for parameters tab
  const [parametersData, setParametersData] = useState(null)
  const [paramsLoading, setParamsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [difficultyFilter, setDifficultyFilter] = useState('All') // All, Low, Medium, High
  const [statusFilter, setStatusFilter] = useState('All') // All, Verified, Estimated, Pending
  const [expandedDomains, setExpandedDomains] = useState({})
  const [expandedRows, setExpandedRows] = useState({})

  useEffect(() => {
    if (!parametersData && !paramsLoading && sessionId) {
      setParamsLoading(true)
      fetch(`/api/session/${sessionId}/parameters`)
        .then(res => res.json())
        .then(data => {
          setParametersData(data)
          // Expand all by default
          if (data.domains) {
            const initialExpanded = {}
            Object.keys(data.domains).forEach(d => initialExpanded[d] = true)
            setExpandedDomains(initialExpanded)
            
            // Set first domain as active tab
            const domainNames = Object.keys(data.domains)
            if (domainNames.length > 0) {
              setActiveTab(domainNames[0])
            }
          }
        })
        .catch(err => console.error("Failed to fetch parameters:", err))
        .finally(() => setParamsLoading(false))
    }
  }, [sessionId, parametersData, paramsLoading])

  if (!report) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <FileText style={{ width: '48px', height: '48px', margin: '0 auto 16px', opacity: 0.4 }} />
        <p style={{ fontSize: '15px' }}>Compiling final executive brief...</p>
      </div>
    )
  }

  const toggleDomain = (domainName) => {
    setExpandedDomains(prev => ({ ...prev, [domainName]: !prev[domainName] }))
  }

  const toggleRow = (rowKey) => {
    setExpandedRows(prev => ({ ...prev, [rowKey]: !prev[rowKey] }))
  }

  const renderStatusBadge = (status) => {
    let color = 'var(--text-muted)'
    let bg = 'rgba(255,255,255,0.05)'
    if (status === 'Verified') { color = 'var(--success)'; bg = 'rgba(16, 185, 129, 0.1)' }
    if (status === 'Estimated') { color = 'var(--warning)'; bg = 'rgba(245, 158, 11, 0.1)' }
    if (status === 'Pending') { color = 'var(--danger)'; bg = 'rgba(239, 68, 68, 0.1)' }
    return (
      <span style={{ fontSize: '10px', fontWeight: 700, color, background: bg, padding: '2px 8px', borderRadius: '12px', border: `1px solid ${color}40`, display: 'flex', alignItems: 'center', gap: '4px' }}>
        {status === 'Verified' && <CheckCircle style={{ width: '10px' }} />}
        {status}
      </span>
    )
  }

  const renderParamRow = (p, idx, agentSource) => {
    // Determine the actual live value
    let realValue = p.value;
    
    // We only filter artificial backend placeholders, not real database values
    const isPlaceholder = (val) => typeof val === 'string' && [
      "Verified Domain Data", 
      "In-depth Verified Metric", 
      "High-Fidelity Reconciled Estimate"
    ].includes(val);

    // If p.value is missing or a placeholder, attempt to rescue it from rawOutputs
    if (realValue === null || realValue === undefined || realValue === "" || isPlaceholder(realValue)) {
      if (rawOutputs && agentSource && rawOutputs[agentSource]?.raw_json_output) {
        const liveVal = rawOutputs[agentSource].raw_json_output[p.key];
        if (liveVal !== undefined && liveVal !== null && liveVal !== "" && !isPlaceholder(liveVal)) {
          realValue = liveVal;
        }
      }
    }
    
    // Final filter to ensure artificial placeholders don't reach the UI renderer
    if (isPlaceholder(realValue)) {
      realValue = null;
    }

    const isExpanded = expandedRows[p.key]

    // Value Renderer
    const renderValue = (val) => {
      if (val === null || val === undefined || val === '') {
        return <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Not Available</span>;
      }
      
      if (Array.isArray(val)) {
        if (val.length === 0) return <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Empty List</span>;
        return (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {val.map((item, i) => (
              <span key={i} style={{ background: 'rgba(99,102,241,0.1)', color: 'var(--indigo-neon)', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', border: '1px solid rgba(99,102,241,0.2)' }}>
                {typeof item === 'object' ? JSON.stringify(item) : String(item)}
              </span>
            ))}
          </div>
        )
      }
      
      if (typeof val === 'object') {
        const jsonStr = JSON.stringify(val, null, 2);
        if (jsonStr.length > 100 && !isExpanded) {
          return (
            <div>
              <pre style={{ background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: '6px', fontSize: '11px', color: 'var(--cyan-neon)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {jsonStr}
              </pre>
              <button onClick={() => toggleRow(p.key)} style={{ background: 'none', border: 'none', color: 'var(--indigo-neon)', fontSize: '11px', cursor: 'pointer', padding: '4px 0', fontWeight: 600 }}>View Full JSON</button>
            </div>
          )
        }
        return (
          <div>
            <pre style={{ background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: '6px', fontSize: '11px', color: 'var(--cyan-neon)', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {jsonStr}
            </pre>
            {jsonStr.length > 100 && <button onClick={() => toggleRow(p.key)} style={{ background: 'none', border: 'none', color: 'var(--indigo-neon)', fontSize: '11px', cursor: 'pointer', padding: '4px 0', fontWeight: 600 }}>Collapse JSON</button>}
          </div>
        )
      }

      const strVal = String(val);
      
      // URL detection
      if (strVal.startsWith('http://') || strVal.startsWith('https://')) {
        return <a href={strVal} target="_blank" rel="noreferrer" style={{ color: 'var(--cyan-neon)', textDecoration: 'none', wordBreak: 'break-all' }}>{strVal}</a>;
      }
      
      if (strVal.length > 120 && !isExpanded) {
        return (
          <div>
            <span style={{ whiteSpace: 'pre-wrap' }}>{strVal.substring(0, 120)}...</span>
            <button onClick={() => toggleRow(p.key)} style={{ background: 'none', border: 'none', color: 'var(--indigo-neon)', fontSize: '11px', cursor: 'pointer', padding: '4px 0', display: 'block', fontWeight: 600 }}>Read More</button>
          </div>
        )
      }
      
      return (
        <div>
          <span style={{ whiteSpace: 'pre-wrap' }}>{strVal}</span>
          {strVal.length > 120 && <button onClick={() => toggleRow(p.key)} style={{ background: 'none', border: 'none', color: 'var(--indigo-neon)', fontSize: '11px', cursor: 'pointer', padding: '4px 0', display: 'block', fontWeight: 600 }}>Show Less</button>}
        </div>
      )
    }

    return (
      <div key={p.key || idx} style={{ display: 'flex', padding: '16px', borderBottom: '1px solid var(--border-subtle)', background: 'rgba(255,255,255,0.01)', alignItems: 'flex-start', gap: '20px' }}>
        <div style={{ flex: '2', minWidth: '0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', lineHeight: '1.4' }}>{p.label}</span>
            {renderStatusBadge(p.status)}
          </div>
          <div style={{ display: 'flex', gap: '8px', fontSize: '11px', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
            <span style={{ background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>{p.cluster}</span>
            <span style={{ background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', color: p.difficulty === 'High' ? 'var(--warning)' : 'inherit' }}>{p.difficulty} Diff</span>
          </div>
        </div>
        <div style={{ flex: '3', fontSize: '13px', color: 'var(--text-secondary)', wordBreak: 'break-word', paddingTop: '2px' }}>
          {renderValue(realValue)}
        </div>
      </div>
    )
  }

  const renderActiveDomain = () => {
    if (paramsLoading) {
      return (
        <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
          <RefreshCw className="pulse-ring-active" style={{ width: '32px', height: '32px', margin: '0 auto 16px', animation: 'spin 2s infinite linear' }} />
          <p style={{ fontSize: '14px' }}>Querying Supabase and rendering Domain Intelligence...</p>
        </div>
      )
    }

    if (!parametersData || !parametersData.domains) {
      return (
        <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--danger)' }}>
          <AlertTriangle style={{ width: '32px', height: '32px', margin: '0 auto 16px' }} />
          <p style={{ fontSize: '14px' }}>Failed to load domain intelligence data.</p>
        </div>
      )
    }

    if (!activeTab) return null

    const domainName = activeTab
    const domainData = parametersData.domains[domainName]
    if (!domainData) return null

    // Flatten parameters for this domain
    const allParams = Object.values(domainData.parameters).map(p => ({ ...p, domainName }))

    // Filter logic
    const filteredParams = allParams.filter(p => {
      const matchesSearch = p.label.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            String(p.value).toLowerCase().includes(searchQuery.toLowerCase())
      const matchesDifficulty = difficultyFilter === 'All' || p.difficulty === difficultyFilter
      const matchesStatus = statusFilter === 'All' || p.status === statusFilter
      return matchesSearch && matchesDifficulty && matchesStatus
    })

    const isExpanded = expandedDomains[domainName] !== false // default true
    const totalParams = Object.keys(domainData.parameters).length
    const confidence = Math.round((domainData.meta?.domain_confidence_score || 0) * 100)

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Toolbar */}
        <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexWrap: 'wrap', gap: '16px', justifyContent: 'space-between', alignItems: 'center' }}>
          
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flex: 1, minWidth: '250px' }}>
            <div style={{ position: 'relative', flex: 1 }}>
              <Search style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', width: '16px', color: 'var(--text-muted)' }} />
              <input 
                type="text" 
                placeholder={`Search in ${domainName}...`} 
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ width: '100%', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '10px 10px 10px 36px', color: 'var(--text-primary)', fontSize: '13px', outline: 'none' }}
              />
            </div>
            
            <div style={{ display: 'flex', gap: '8px' }}>
              <select 
                value={difficultyFilter} 
                onChange={e => setDifficultyFilter(e.target.value)}
                style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '10px', color: 'var(--text-primary)', fontSize: '13px', outline: 'none', cursor: 'pointer' }}
              >
                <option value="All">All Diff</option>
                <option value="Low">Low Diff</option>
                <option value="Medium">Medium Diff</option>
                <option value="High">High Diff</option>
              </select>
              
              <select 
                value={statusFilter} 
                onChange={e => setStatusFilter(e.target.value)}
                style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '10px', color: 'var(--text-primary)', fontSize: '13px', outline: 'none', cursor: 'pointer' }}
              >
                <option value="All">All Status</option>
                <option value="Verified">Verified</option>
                <option value="Estimated">Estimated</option>
                <option value="Pending">Pending</option>
              </select>
            </div>
          </div>
        </div>

        {/* Domain Panel */}
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <div 
            onClick={() => toggleDomain(domainName)}
            style={{ padding: '16px 20px', background: 'rgba(255,255,255,0.02)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', borderBottom: isExpanded ? '1px solid var(--border-subtle)' : 'none' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {isExpanded ? <ChevronDown style={{ width: '18px', color: 'var(--indigo-neon)' }} /> : <ChevronRight style={{ width: '18px', color: 'var(--text-muted)' }} />}
              <div>
                <h4 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>{domainName}</h4>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>{domainData.meta?.domain_description}</p>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{filteredParams.length} / {totalParams} Params</span>
              <span style={{ fontSize: '12px', fontWeight: 600, color: confidence >= 85 ? 'var(--success)' : 'var(--warning)', background: 'rgba(255,255,255,0.05)', padding: '4px 8px', borderRadius: '12px' }}>
                {confidence}% Confidence
              </span>
            </div>
          </div>
          
          {isExpanded && (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {filteredParams.length > 0 ? (
                filteredParams.map((p, idx) => renderParamRow(p, idx, domainData.meta?.agent_source))
              ) : (
                <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '14px' }}>
                  No parameters match the current filters.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Dynamic Tabs based on domain names
  const tabItems = parametersData?.domains ? Object.keys(parametersData.domains).map(domainName => ({
    id: domainName,
    name: domainName,
    icon: Database // We can use Database icon for all domains
  })) : []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Info */}
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--cyan-neon)', letterSpacing: '1px' }}>COMPILED BUSINESS INTELLIGENCE DOSSIER</span>
          <h2 style={{ fontFamily: 'var(--font-title)', fontSize: '30px', fontWeight: 800, marginTop: '4px' }}>{report.company_name}</h2>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '8px 16px', borderRadius: '30px' }}>
          <span style={{ width: '8px', height: '8px', background: 'var(--success)', borderRadius: '50%' }} className="pulse-ring-active"></span>
          <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--success)' }}>QUALIFIED PROFILE</span>
        </div>
      </div>

      {/* Tabs list */}
      {tabItems.length > 0 ? (
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '8px', scrollbarWidth: 'thin' }}>
          {tabItems.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px 20px',
                  border: '1px solid',
                  borderColor: isActive ? 'var(--indigo-neon)' : 'var(--border-subtle)',
                  background: isActive ? 'rgba(99, 102, 241, 0.08)' : 'var(--bg-surface)',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  borderRadius: '10px',
                  fontWeight: 600,
                  fontSize: '13px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  whiteSpace: 'nowrap'
                }}
              >
                <Icon style={{ width: '16px', color: isActive ? 'var(--indigo-neon)' : 'var(--text-muted)' }} />
                {tab.name}
              </button>
            )
          })}
        </div>
      ) : (
        <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
          {paramsLoading ? 'Loading domains...' : 'No domains available.'}
        </div>
      )}

      {/* Dynamic Tab Panel */}
      <div style={{ marginTop: '4px' }}>
        {renderActiveDomain()}
      </div>
    </div>
  )
}
