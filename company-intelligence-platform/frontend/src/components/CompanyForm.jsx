// CompanyForm.jsx
import React, { useState } from 'react'
import { Search, Compass, Sliders, Play, Server } from 'lucide-react'

export default function CompanyForm({ onSubmit, loading }) {
  const [companyName, setCompanyName] = useState('')
  const [industry, setIndustry] = useState('Technology')
  const [customQuery, setCustomQuery] = useState('')
  const [threshold, setThreshold] = useState(0.85)
  const [maxAttempts, setMaxAttempts] = useState(3)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!companyName.trim()) return
    onSubmit({
      company_name: companyName.trim(),
      industry,
      custom_query: customQuery.trim() || null,
      confidence_threshold: parseFloat(threshold),
      max_attempts: parseInt(maxAttempts, 10)
    })
  }

  const industries = [
    'Technology', 'SaaS', 'Fintech', 'Healthcare', 'E-commerce', 
    'Energy', 'Logistics', 'Automotive', 'Real Estate', 'Education'
  ]

  return (
    <div className="glass-panel" style={{ padding: '32px', maxWidth: '640px', margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
        <Compass style={{ color: 'var(--indigo-neon)', width: '32px', height: '32px' }} />
        <div>
          <h2 style={{ fontFamily: 'var(--font-title)', fontWeight: 700, fontSize: '24px' }}>Target Search Console</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Launch real-time parallel multi-agent extraction</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>Company Name</label>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search style={{ position: 'absolute', left: '16px', color: 'var(--text-muted)', width: '18px' }} />
            <input 
              type="text" 
              className="input-field" 
              placeholder="e.g. OpenAI, Stripe, Snowflake..." 
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              required
              style={{ width: '100%', paddingLeft: '48px', height: '50px', fontSize: '16px' }}
              disabled={loading}
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '16px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>Industry Segment</label>
            <select 
              className="input-field" 
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              style={{ height: '50px', fontSize: '15px' }}
              disabled={loading}
            >
              {industries.map((ind) => (
                <option key={ind} value={ind}>{ind}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>Custom Research Directives (Optional)</label>
          <textarea 
            className="input-field" 
            placeholder="Focus on recent partner expansions, developer adoption details, primary technical database stacks, etc." 
            value={customQuery}
            onChange={(e) => setCustomQuery(e.target.value)}
            style={{ minHeight: '90px', resize: 'vertical', fontSize: '14px', lineHeight: '1.6' }}
            disabled={loading}
          />
        </div>

        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
          <button 
            type="button" 
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={{ 
              background: 'none', 
              border: 'none', 
              color: 'var(--text-secondary)', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '6px',
              fontSize: '14px',
              fontWeight: 500
            }}
          >
            <Sliders style={{ width: '16px' }} />
            {showAdvanced ? 'Hide Quality Guard Parameters' : 'Show Quality Guard Parameters'}
          </button>

          {showAdvanced && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px', padding: '16px', background: 'rgba(0,0,0,0.2)', borderRadius: '10px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <label style={{ fontSize: '12px', fontWeight: 600 }}>Confidence Target</label>
                  <span style={{ fontSize: '12px', color: 'var(--cyan-neon)', fontWeight: 700 }}>{Math.round(threshold * 100)}%</span>
                </div>
                <input 
                  type="range" 
                  min="0.5" 
                  max="1.0" 
                  step="0.05" 
                  value={threshold}
                  onChange={(e) => setThreshold(e.target.value)}
                  style={{ accentColor: 'var(--indigo-neon)', height: '6px' }}
                  disabled={loading}
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Max Retry Attempts</label>
                <input 
                  type="number" 
                  min="1" 
                  max="5" 
                  className="input-field" 
                  value={maxAttempts}
                  onChange={(e) => setMaxAttempts(e.target.value)}
                  style={{ height: '36px', fontSize: '13px', padding: '6px 12px' }}
                  disabled={loading}
                />
              </div>
            </div>
          )}
        </div>

        <button 
          type="submit" 
          className="btn-primary" 
          disabled={loading}
          style={{ 
            height: '52px', 
            fontSize: '16px', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            gap: '10px',
            marginTop: '10px'
          }}
        >
          {loading ? (
            <>
              <div className="spinner" style={{ width: '20px', height: '20px' }}></div>
              Initializing LangGraph Orchestration...
            </>
          ) : (
            <>
              <Play style={{ width: '18px', fill: 'currentColor' }} />
              Trigger Research Pipeline
            </>
          )}
        </button>
      </form>
    </div>
  )
}
