// ValidationReport.jsx
import React from 'react'
import { ShieldCheck, ShieldAlert, RefreshCw, Layers, CheckCircle2, AlertTriangle } from 'lucide-react'

export default function ValidationReport({ history, failedFields, confidenceScore, threshold, passed }) {
  const thresholdPct = Math.round((threshold || 0.85) * 100)

  // If no validation run has occurred yet
  if (!history || history.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '180px' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
          <Layers style={{ width: '32px', height: '32px', margin: '0 auto 12px', opacity: 0.5 }} />
          <p style={{ fontSize: '14px', fontWeight: 500 }}>Waiting for consolidation layer to output profile...</p>
        </div>
      </div>
    )
  }

  const latest = history[history.length - 1]
  const pct = Math.round(confidenceScore * 100)

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {passed ? (
            <ShieldCheck style={{ color: 'var(--success)', width: '28px', height: '28px' }} />
          ) : (
            <ShieldAlert style={{ color: 'var(--warning)', width: '28px', height: '28px' }} />
          )}
          <div>
            <h3 style={{ fontFamily: 'var(--font-title)', fontWeight: 700, fontSize: '18px' }}>Quality Guard Auditing</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Rule check execution summary</p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <div className="glass-panel" style={{ padding: '8px 16px', borderRadius: '10px', textAlign: 'center', minWidth: '80px', background: 'rgba(0,0,0,0.15)' }}>
            <span style={{ fontSize: '18px', fontWeight: 800, color: passed ? 'var(--success)' : 'var(--warning)' }}>{pct}%</span>
            <p style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 600 }}>CONFIDENCE</p>
          </div>
          <div className="glass-panel" style={{ padding: '8px 16px', borderRadius: '10px', textAlign: 'center', minWidth: '80px', background: 'rgba(0,0,0,0.15)' }}>
            <span style={{ fontSize: '18px', fontWeight: 800, color: 'var(--cyan-neon)' }}>{history.length}</span>
            <p style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 600 }}>ATTEMPTS</p>
          </div>
        </div>
      </div>

      {/* Main Status Callout */}
      {!passed ? (
        <div style={{ 
          background: 'rgba(245, 158, 11, 0.05)', 
          borderLeft: '4px solid var(--warning)', 
          padding: '16px', 
          borderRadius: '0 8px 8px 0', 
          marginBottom: '20px',
          display: 'flex',
          gap: '12px',
          alignItems: 'flex-start'
        }}>
          <AlertTriangle style={{ color: 'var(--warning)', width: '20px', flexShrink: 0, marginTop: '2px' }} />
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#ffb020', marginBottom: '4px' }}>Regeneration Loop Activated</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              {confidenceScore * 100 < thresholdPct ? (
                <>Consolidated details fail to satisfy the {thresholdPct}% confidence threshold.</>
              ) : (
                <>The confidence score is above the target threshold, but there are still missing or conflicting parameters.</>
              )} The pipeline is triggering targeted repairs for the following fields: 
              <strong style={{ color: 'var(--text-primary)', marginLeft: '4px' }}>{failedFields.join(', ')}</strong>.
            </p>
          </div>
        </div>
      ) : (
        <div style={{ 
          background: 'rgba(16, 185, 129, 0.05)', 
          borderLeft: '4px solid var(--success)', 
          padding: '16px', 
          borderRadius: '0 8px 8px 0', 
          marginBottom: '20px',
          display: 'flex',
          gap: '12px',
          alignItems: 'flex-start'
        }}>
          <CheckCircle2 style={{ color: 'var(--success)', width: '20px', flexShrink: 0, marginTop: '2px' }} />
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#14e19c', marginBottom: '4px' }}>Quality Guard Approved</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              All critical research items have successfully passed verification audits. Compiling final deliverables.
            </p>
          </div>
        </div>
      )}

      {/* Attempt History Logs */}
      <div>
        <h4 style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.5px', marginBottom: '12px' }}>EXECUTION LOG AUDIT TRAIL</h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {history.map((h, i) => (
            <div 
              key={i} 
              style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center', 
                padding: '10px 14px', 
                borderRadius: '8px', 
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--border-subtle)',
                fontSize: '13px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <RefreshCw style={{ 
                  color: h.passed ? 'var(--success)' : 'var(--warning)', 
                  width: '14px', 
                  animation: !h.passed && i === history.length - 1 ? 'spin 3s infinite linear' : 'none' 
                }} />
                <span>Attempt #{h.attempt} Validation Report</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Score: <strong style={{ color: h.passed ? 'var(--success)' : 'var(--warning)' }}>{Math.round(h.overall_confidence * 100)}%</strong></span>
                {h.passed ? (
                  <span style={{ color: 'var(--success)', fontWeight: 600 }}>PASSED</span>
                ) : (
                  <span style={{ color: 'var(--warning)', fontWeight: 600 }}>REGEN LOOP</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
