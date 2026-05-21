import React, { useEffect, useState } from 'react'

export default function AllocatedParameters({ sessionId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!sessionId) return
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        const resp = await fetch(`/api/session/${sessionId}/allocated_parameters`)
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
        const j = await resp.json()
        setData(j.allocated_parameters)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [sessionId])

  if (loading) return <div className="glass-panel" style={{ padding: 12 }}>Loading allocated parameters…</div>
  if (error) return <div className="glass-panel" style={{ padding: 12, color: 'var(--danger)' }}>Error: {error}</div>
  if (!data) return <div className="glass-panel" style={{ padding: 12 }}>No allocated parameters found for this session.</div>

  return (
    <div className="glass-panel" style={{ padding: 12, maxHeight: '480px', overflow: 'auto' }}>
      <h4 style={{ marginBottom: 8, fontWeight: 700 }}>Allocated Parameters (persisted)</h4>
      <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 12 }}>{JSON.stringify(data, null, 2)}</pre>
    </div>
  )
}
