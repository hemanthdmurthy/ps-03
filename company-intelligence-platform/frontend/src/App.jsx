// App.jsx
import React, { useState, useEffect } from 'react'
import CompanyForm from './components/CompanyForm'
import AgentProgress from './components/AgentProgress'
import ValidationReport from './components/ValidationReport'
import ReportDashboard from './components/ReportDashboard'
import ValidationAnalytics from './components/ValidationAnalytics'
import TokenDashboard from './components/TokenDashboard'
import AllocatedParameters from './components/AllocatedParameters'
import { Compass, RefreshCw, AlertCircle, FileCheck, ArrowLeft, Terminal, BarChart3 } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Utility for tailwind classes
function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export default function App() {
  const [viewMode, setViewMode] = useState('orchestrator') // orchestrator, quality_control, token_intelligence
  const [screen, setScreen] = useState('search') // search, pipeline, result
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  // Active session context
  const [sessionId, setSessionId] = useState(null)
  const [companyName, setCompanyName] = useState('')
  const [stage, setStage] = useState('initiated') // initiated, researching, validating, completed, failed
  
  // Real-time tracking vectors
  const [agentStatus, setAgentStatus] = useState({})
  const [tokenUsage, setTokenUsage] = useState({ input_tokens: 0, output_tokens: 0, total_tokens: 0 })
  const [validationHistory, setValidationHistory] = useState([])
  const [failedFields, setFailedFields] = useState([])
  const [confidenceScore, setConfidenceScore] = useState(0.0)
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.85)
  
  // Final payload
  const [finalReport, setFinalReport] = useState(null)
  const [rawOutputs, setRawOutputs] = useState(null)
  const [showAllocated, setShowAllocated] = useState(false)

  const handleStartResearch = async (payload) => {
    setLoading(true)
    setError(null)
    setCompanyName(payload.company_name)
    setAgentStatus({
      website: 'pending',
      linkedin: 'pending',
      news: 'pending',
      funding: 'pending',
      product: 'pending',
      social: 'pending'
    })
    setValidationHistory([])
    setFailedFields([])
    setConfidenceScore(0.0)
    setTokenUsage({ input_tokens: 0, output_tokens: 0, total_tokens: 0 })
    setFinalReport(null)

    try {
      setConfidenceThreshold(payload.confidence_threshold)
      // POST research request to launch background LangGraph workflow
      const resp = await fetch('/api/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        json: false, // flag for custom configurations if needed
        body: JSON.stringify(payload)
      })

      if (!resp.ok) {
        throw new Error(`Server returned code ${resp.status}: ${await resp.text()}`)
      }

      const data = await resp.json()
      setSessionId(data.session_id)
      setScreen('pipeline')
      setStage(data.status === 'queued' ? 'queued' : 'researching')
    } catch (err) {
      console.error("Submission failed: ", err)
      setError(`Failed to trigger research orchestrator: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  // Connect Server Sent Events (SSE) for active real-time graph updates
  useEffect(() => {
    if (!sessionId || screen !== 'pipeline') return

    const sseUrl = `/api/session/${sessionId}/stream`
    console.log(`[SSE] Connecting stream listener for session: ${sessionId}`)
    const eventSource = new EventSource(sseUrl)

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        const { event: eventName, data } = payload
        console.log(`[SSE Event] Recieved '${eventName}':`, data)

        switch (eventName) {
          case 'connected':
            console.log("Stream synchronization established with backend.")
            break

          case 'input_normalized':
            setStage('researching')
            break

          case 'agent_status_updated':
            setAgentStatus(data.agent_status)
            if (data.token_usage) {
              const normalizedTokenUsage = data.token_usage.total_tokens !== undefined
                ? data.token_usage
                : {
                    input_tokens: data.token_usage.prompt || 0,
                    output_tokens: data.token_usage.completion || 0,
                    total_tokens: data.token_usage.total || 0
                  }
              setTokenUsage(normalizedTokenUsage)
            }
            break

          case 'research_completed':
            setAgentStatus(data.agent_status)
            if (data.token_usage) {
              const normalizedTokenUsage = data.token_usage.total_tokens !== undefined
                ? data.token_usage
                : {
                    input_tokens: data.token_usage.prompt || 0,
                    output_tokens: data.token_usage.completion || 0,
                    total_tokens: data.token_usage.total || 0
                  }
              setTokenUsage(normalizedTokenUsage)
            }
            break

          case 'consolidation_completed':
            setStage('validating')
            break

          case 'validation_completed':
            setConfidenceScore(data.confidence_score)
            setFailedFields(data.failed_fields)
            setValidationHistory(data.validation_history)
            break

          case 'regeneration_triggered':
            setStage('regenerating')
            // Set any re-triggered agents to running status
            const updated = { ...agentStatus }
            data.failed_fields?.forEach(field => {
              // Map field to appropriate re-running indicator
              if (['company_overview', 'mission_statement', 'headquarters_city', 'founder_or_ceo'].includes(field)) updated.website = 'regenerating'
              if (['approximate_headcount', 'key_executives'].includes(field)) updated.linkedin = 'regenerating'
              if (['total_funding_usd'].includes(field)) updated.funding = 'regenerating'
              if (['technological_stack'].includes(field)) updated.product = 'regenerating'
            })
            setAgentStatus(updated)
            break

          case 'report_compiled':
            setFinalReport(data.final_report)
            break

          case 'storage_completed':
            setStage('completed')
            setScreen('result')
            eventSource.close()
            // Make one final detailed get-fetch to retrieve intermediate raw tables
            fetchSessionData(sessionId)
            break

          case 'workflow_ended':
            eventSource.close()
            break

          case 'workflow_failed':
            setError(`Workflow execution failed: ${data.error}`)
            setStage('failed')
            eventSource.close()
            break

          default:
            break
        }
      } catch (err) {
        console.error("Error parsing stream event: ", err)
      }
    }

    eventSource.onerror = (err) => {
      console.error("[SSE Connection Error]", err)
      // SSE auto-reconnects, but we provide an audit log
    }

    return () => {
      console.log(`[SSE] Closing stream listener for session: ${sessionId}`)
      eventSource.close()
    }
  }, [sessionId, screen])

  const fetchSessionData = async (sid) => {
    try {
      const resp = await fetch(`/api/session/${sid}`)
      if (resp.ok) {
        const fullDetails = await resp.json()
        setFinalReport(fullDetails.final_report)
        setRawOutputs(fullDetails.agent_outputs)
      }
    } catch (err) {
      console.error("Failed to sync final structures: ", err)
    }
  }

  return (
    <div className="max-w-[1600px] mx-auto px-6 py-10 min-h-screen">
      {/* Brand Header */}
      <header className="flex flex-col md:flex-row justify-between items-center mb-12 gap-6">
        <div className="flex items-center gap-4">
          <div className="bg-gradient-to-br from-indigo-500 to-violet-600 w-12 h-12 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Compass className="text-white w-6 h-6" />
          </div>
          <div>
            <h1 className="font-['Outfit'] text-2xl font-black tracking-tight text-white uppercase">
              PLACEMENT<span className="text-cyan-400">INTEL</span>
            </h1>
            <p className="text-[10px] text-slate-500 font-bold tracking-[0.2em] uppercase">
              Enterprise AI Orchestrator
            </p>
          </div>
        </div>
        
        {/* Navigation Tabs */}
        <div className="flex gap-1.5 bg-slate-900/40 backdrop-blur-md border border-white/5 p-1.5 rounded-2xl shadow-xl">
          <button 
            onClick={() => setViewMode('orchestrator')}
            className={cn(
              "flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition-all duration-300",
              viewMode === 'orchestrator' 
                ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-lg shadow-indigo-500/5" 
                : "text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent"
            )}
          >
            <Compass className={cn("w-4 h-4", viewMode === 'orchestrator' ? "text-indigo-400" : "text-slate-500")} />
            Orchestrator
          </button>
          
          <button 
            onClick={() => setViewMode('quality_control')}
            className={cn(
              "flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition-all duration-300",
              viewMode === 'quality_control' 
                ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-lg shadow-cyan-500/5" 
                : "text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent"
            )}
          >
            <FileCheck className={cn("w-4 h-4", viewMode === 'quality_control' ? "text-cyan-400" : "text-slate-500")} />
            Quality Control
          </button>
          
          <button 
            onClick={() => setViewMode('token_intelligence')}
            className={cn(
              "flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition-all duration-300",
              viewMode === 'token_intelligence' 
                ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-lg shadow-amber-500/5" 
                : "text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent"
            )}
          >
            <BarChart3 className={cn("w-4 h-4", viewMode === 'token_intelligence' ? "text-amber-400" : "text-slate-500")} />
            Token Intelligence
          </button>
        </div>
      </header>


      {/* Main Panel Router */}
      <main>
        {error && (
          <div className="glass-panel" style={{ padding: '20px', borderColor: 'var(--danger)', background: 'rgba(239, 68, 68, 0.05)', borderRadius: '12px', marginBottom: '30px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <AlertCircle style={{ color: 'var(--danger)', width: '20px' }} />
            <span style={{ fontSize: '14px', color: 'rgba(255,255,255,0.9)', fontWeight: 500 }}>{error}</span>
          </div>
        )}

        {viewMode === 'quality_control' ? (
          <ValidationAnalytics />
        ) : viewMode === 'token_intelligence' ? (
          <TokenDashboard />
        ) : (
          <>
            {screen === 'search' && (
              <CompanyForm onSubmit={handleStartResearch} loading={loading} />
            )}

            {screen === 'pipeline' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                {/* Stage title */}
                <div className="glass-panel" style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <RefreshCw className="pulse-ring-active" style={{ color: 'var(--indigo-neon)', width: '20px', animation: 'spin 4s infinite linear' }} />
                    <div>
                      <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Orchestrating Research on: <span className="text-gradient" style={{ fontSize: '18px' }}>{companyName}</span></h3>
                      <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Executing LangGraph concurrent workflow. Tracking intermediates...</p>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '16px', fontSize: '13px', alignItems: 'center' }}>
                    <span>Budget Consumed: <strong style={{ color: 'var(--cyan-neon)' }}>{(tokenUsage?.total_tokens ?? tokenUsage?.total ?? 0).toLocaleString()} tokens</strong></span>
                    <button
                      onClick={() => setShowAllocated(s => !s)}
                      style={{
                        background: 'transparent',
                        border: '1px solid rgba(255,255,255,0.14)',
                        color: 'var(--text-secondary)',
                        padding: '8px 12px',
                        borderRadius: '999px',
                        cursor: 'pointer',
                        fontSize: '12px',
                        fontWeight: 700
                      }}
                    >
                      {showAllocated ? 'Hide Allocated Parameters' : 'View Allocated Parameters'}
                    </button>
                  </div>
                </div>

                {/* Matrix details */}
                <div style={{ display: 'grid', gridTemplateColumns: '5fr 3fr', gap: '24px' }}>
                  <AgentProgress agentStatus={agentStatus} stage={stage} />
                  <ValidationReport 
                    history={validationHistory} 
                    failedFields={failedFields} 
                    confidenceScore={confidenceScore} 
                    threshold={confidenceThreshold}
                    passed={stage === 'completed'} 
                  />
                </div>

                {showAllocated && (
                  <div style={{ marginTop: '18px' }}>
                    <AllocatedParameters sessionId={sessionId} />
                  </div>
                )}
              </div>
            )}

            {screen === 'result' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                {/* Header control */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <button 
                    onClick={() => setScreen('search')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      fontWeight: 600,
                      fontSize: '14px'
                    }}
                  >
                    <ArrowLeft style={{ width: '16px' }} />
                    Search Another Target
                  </button>
                  <div style={{ display: 'flex', gap: 12 }}>
                    <button
                      onClick={() => setShowAllocated(s => !s)}
                      style={{
                        background: 'none',
                        border: '1px solid rgba(255,255,255,0.04)',
                        color: 'var(--text-secondary)',
                        cursor: 'pointer',
                        padding: '8px 12px',
                        borderRadius: 8,
                        fontWeight: 600,
                        fontSize: '13px'
                      }}
                    >
                      {showAllocated ? 'Hide Allocated Parameters' : 'View Allocated Parameters'}
                    </button>
                  </div>
                  <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    Session ID: <strong style={{ color: 'var(--text-secondary)' }}>{sessionId}</strong>
                  </span>
                </div>

                {/* Dashboard */}
                <ReportDashboard report={finalReport} rawOutputs={rawOutputs} sessionId={sessionId} />
                {showAllocated && <AllocatedParameters sessionId={sessionId} />}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
