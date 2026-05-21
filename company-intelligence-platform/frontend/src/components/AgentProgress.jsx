// AgentProgress.jsx
import React from 'react'
import { Globe, Linkedin, FileText, DollarSign, Cpu, Users, ArrowRight } from 'lucide-react'

export default function AgentProgress({ agentStatus, stage }) {
  const agents = [
    { key: 'website', name: 'Domain 1: Corporate Identity & Governance', desc: 'Overview, structure, locations & leadership', icon: Globe, color: 'var(--cyan-neon)' },
    { key: 'news', name: 'Domain 2: Market Dynamics & Strategic Position', desc: 'Strategic moves, market position & competitors', icon: FileText, color: 'var(--violet-neon)' },
    { key: 'funding', name: 'Domain 3: Financial Health & Investment Profile', desc: 'Capital raised, stage, backers & valuation', icon: DollarSign, color: 'var(--success)' },
    { key: 'product', name: 'Domain 4: Product & Technology Intelligence', desc: 'Software niche, platforms & tech stack', icon: Cpu, color: 'var(--info)' },
    { key: 'social', name: 'Domain 5: Brand, Media & Public Sentiment', desc: 'Public perception, media presence & sentiment', icon: Users, color: '#f91880' },
    { key: 'linkedin', name: 'Domain 6: Talent, Hiring & Organizational Intelligence', desc: 'Employee distribution, hiring trends & structure', icon: Linkedin, color: '#0077b5' }
  ]

  const getStatusBadge = (status) => {
    switch (status) {
      case 'running':
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--indigo-neon)', letterSpacing: '0.5px' }}>RUNNING</span>
            <div className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }}></div>
          </div>
        )
      case 'completed':
        return (
          <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--success)', letterSpacing: '0.5px', background: 'rgba(16, 185, 129, 0.1)', padding: '4px 10px', borderRadius: '20px' }}>
            COMPLETED ✓
          </span>
        )
      case 'failed':
        return (
          <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--danger)', letterSpacing: '0.5px', background: 'rgba(239, 68, 68, 0.1)', padding: '4px 10px', borderRadius: '20px' }}>
            FAILED ✗
          </span>
        )
      case 'regenerating':
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--warning)', letterSpacing: '0.5px' }}>REPAIRING</span>
            <div className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px', borderTopColor: 'var(--warning)' }}></div>
          </div>
        )
      default:
        return <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>IDLE</span>
    }
  }

  // Calculate percentage of complete agents
  const total = agents.length
  const completedCount = Object.values(agentStatus).filter(s => s === 'completed').length
  const pct = Math.round((completedCount / total) * 100)

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ fontFamily: 'var(--font-title)', fontWeight: 700, fontSize: '18px' }}>Parallel Extraction Matrix</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Current Pipeline Stage: <strong style={{ color: 'var(--indigo-neon)' }}>{stage.toUpperCase()}</strong></p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '20px', fontWeight: 800, color: 'var(--cyan-neon)' }}>{pct}%</span>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>RESEARCH PROGRESS</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div style={{ height: '6px', width: '100%', background: 'rgba(255,255,255,0.05)', borderRadius: '10px', overflow: 'hidden', marginBottom: '24px' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg, var(--cyan-neon) 0%, var(--indigo-neon) 100%)', borderRadius: '10px', transition: 'width 0.4s ease' }}></div>
      </div>

      {/* Agents Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {agents.map((agent) => {
          const Icon = agent.icon
          const status = agentStatus[agent.key] || 'pending'
          const isActive = status === 'running' || status === 'regenerating'
          const isDone = status === 'completed'
          
          return (
            <div 
              key={agent.key} 
              className="glass-panel" 
              style={{ 
                padding: '16px', 
                background: isActive ? 'rgba(99, 102, 241, 0.05)' : 'var(--bg-surface)', 
                borderColor: isActive ? 'var(--indigo-neon)' : isDone ? 'rgba(16, 185, 129, 0.2)' : 'var(--border-subtle)',
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'space-between',
                borderRadius: '12px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div 
                  className={isActive ? 'pulse-ring-active' : ''} 
                  style={{ 
                    width: '42px', 
                    height: '42px', 
                    borderRadius: '10px', 
                    background: `rgba(${isDone ? '16, 185, 129' : isActive ? '99, 102, 241' : '148, 163, 184'}, 0.1)`, 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    border: `1px solid ${isActive ? 'var(--indigo-neon)' : 'transparent'}`
                  }}
                >
                  <Icon style={{ color: isDone ? 'var(--success)' : isActive ? 'var(--indigo-neon)' : 'var(--text-secondary)', width: '20px' }} />
                </div>
                <div>
                  <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>{agent.name}</h4>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{agent.desc}</p>
                </div>
              </div>
              <div>
                {getStatusBadge(status)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
