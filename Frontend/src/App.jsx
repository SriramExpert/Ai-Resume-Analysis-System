import { useState, useEffect, useRef } from 'react'
import './index.css'
import { StatsVisualization } from './components/Visualizations'

function App() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'ai',
      text: 'Hello! I am your AI Resume Assistant. Upload some resumes and ask me anything like "What are the common skills?" or "Compare Sriram and Raju".',
      timestamp: new Date().toLocaleTimeString()
    }
  ])
  // Add session state
  const [sessionId, setSessionId] = useState(null)

  // State for file upload and candidates
  const [uploading, setUploading] = useState(false)
  const [candidates, setCandidates] = useState([])
  const [processing, setProcessing] = useState(false)

  const fileInputRef = useRef(null)
  const chatEndRef = useRef(null)

  useEffect(() => {
    fetchCandidates()
    initSession()
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const initSession = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/chat/new-session', { method: 'POST' })
      const data = await res.json()
      setSessionId(data.session_id)
      console.log("New session created:", data.session_id)
    } catch (err) {
      console.error("Failed to init session", err)
    }
  }

  const fetchCandidates = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/candidates')
      if (res.ok) {
        const data = await res.json()
        setCandidates(data.candidates || [])
      }
    } catch (err) {
      console.error("Failed to fetch candidates", err)
    }
  }

  const handleUpload = async (e) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploading(true)
    const formData = new FormData()
    Array.from(files).forEach(file => {
      formData.append('files', file)
    })

    try {
      const res = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData
      })

      const data = await res.json()

      if (!res.ok) throw new Error(data.detail || 'Upload failed')

      setMessages(prev => [...prev, {
        role: 'ai',
        text: `✅ Processed ${data.details ? data.details.length : 'files'} successfully.`,
        timestamp: new Date().toLocaleTimeString()
      }])

      fetchCandidates()
    } catch (err) {
      console.error("Upload error", err)
      setMessages(prev => [...prev, {
        role: 'ai',
        text: `❌ Upload failed: ${err.message}`,
        timestamp: new Date().toLocaleTimeString()
      }])
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const transformStatsData = (metrics, insights) => {
    // metrics is expected to be an array of candidate objects with scores
    const candidateData = metrics || []

    // Calculate summary statistics
    const summary = {
      average_scores: {},
      top_candidate: null,
      recommendations: [] // Placeholder, as real recommendations come from LLM text which needs parsing
    }

    if (candidateData.length > 0) {
      // Calculate averages and find top candidate
      const totals = {}
      const counts = {}
      let maxScore = -1

      candidateData.forEach(c => {
        if (c.scores) {
          Object.entries(c.scores).forEach(([cat, score]) => {
            totals[cat] = (totals[cat] || 0) + score
            counts[cat] = (counts[cat] || 0) + 1
          })

          // Calculate overall score if missing
          const overall = c.overall_score || (Object.values(c.scores).reduce((a, b) => a + b, 0) / Object.values(c.scores).length)
          c.overall_score = overall

          if (overall > maxScore) {
            maxScore = overall
            summary.top_candidate = { name: c.name, overall_score: overall }
          }
        }
      })

      Object.keys(totals).forEach(cat => {
        summary.average_scores[cat] = totals[cat] / counts[cat]
      })
    }

    return {
      visualization_data: {
        candidates: candidateData,
        summary: summary
      }
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim() || processing) return

    const userMsg = query.trim()
    setQuery('')

    // Add user message
    setMessages(prev => [...prev, {
      role: 'user',
      text: userMsg,
      timestamp: new Date().toLocaleTimeString()
    }])

    setProcessing(true)

    try {
      // Use chat endpoint for context awareness
      const endpoint = sessionId ? 'http://localhost:8000/api/chat/query' : 'http://localhost:8000/api/process'
      const payload = sessionId ? { query: userMsg, session_id: sessionId } : { query: userMsg }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        const errorText = await res.text()
        let errorMessage = `HTTP ${res.status}`

        try {
          const errorData = JSON.parse(errorText)
          errorMessage = errorData.detail || errorData.message || errorMessage
        } catch {
          errorMessage = `Backend error: ${res.status} ${res.statusText}`
        }

        throw new Error(errorMessage)
      }

      const data = await res.json()

      let aiResponse = ''
      let visualizationData = null

      switch (data.tool_detected) {
        case 'ask':
          aiResponse = data.response
          break

        case 'stats':
          aiResponse = "📊 **Statistics Analysis Complete**\n\nI've analyzed the candidate data. Here are the insights:"
          visualizationData = transformStatsData(data.performance_metrics, data.ai_insights)
          break

        case 'compare':
          aiResponse = "⚖️ **Comparison Completed**\n\nI've compared the selected candidates."
          if (data.data) {
            aiResponse += `\n\nComparison results are available.`
          }
          break

        case 'blog':
          aiResponse = "✍️ **Blog Report Generated**\n\n" + (data.content || "No content generated.")
          break

        default:
          aiResponse = "I've processed your request. How else can I help?"
      }

      setMessages(prev => [...prev, {
        role: 'ai',
        text: aiResponse,
        tool: data.tool_detected,
        visualizationData,
        timestamp: new Date().toLocaleTimeString()
      }])

    } catch (err) {
      console.error("Error in handleSubmit:", err)
      setMessages(prev => [...prev, {
        role: 'ai',
        text: `❌ Error: ${err.message}`,
        timestamp: new Date().toLocaleTimeString()
      }])
    } finally {
      setProcessing(false)
    }
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="app-container">
      <div className="sidebar">
        <div className="glass-panel header-panel">
          <h1>Resume AI Suite</h1>
          <p>Unified AI Resume Analysis</p>
        </div>

        <div className="glass-panel">
          <h3>📤 Upload Resumes</h3>
          <div className="upload-area" onClick={handleUploadClick}>
            <div className="upload-icon">
              {uploading ? '⏳' : '📁'}
            </div>
            <p className="upload-text">
              {uploading ? 'Processing...' : 'Click or drop files here'}
            </p>
            <p className="upload-hint">Supports .pdf, .docx, .txt</p>
            {uploading && <div className="upload-progress">
              <div className="upload-progress-bar"></div>
            </div>}
            <input
              ref={fileInputRef}
              type="file"
              id="fileInput"
              multiple
              hidden
              onChange={handleUpload}
              accept=".pdf,.docx,.txt"
            />
          </div>
        </div>

        <div className="glass-panel candidates-section">
          <div className="candidates-header">
            <h3>👥 Database Candidates</h3>
            <span className="candidates-count">{candidates.length}</span>
          </div>
          <div className="candidates-list">
            {candidates.length > 0 ? (
              candidates.map((name, i) => (
                <div key={i} className="candidate-item">
                  <div className="candidate-avatar">
                    {name.charAt(0).toUpperCase()}
                  </div>
                  <div className="candidate-info">
                    <div className="candidate-name">{name}</div>
                    <div className="candidate-status">
                      <div className="status-dot"></div>
                      <span className="status-text">Stored</span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <div className="empty-icon">📭</div>
                <p>No candidates found</p>
                <p className="empty-subtext">Upload resumes to get started</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="main-content">
        <div className="chat-container">
          <div className="chat-header">
            <div className="chat-title">
              <span>💬 Resume Analysis Chat</span>
            </div>
            <div className="chat-subtitle">
              Ask questions, compare candidates, or generate reports
            </div>
          </div>

          <div className="chat-messages">
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="message-header">
                  <div className="message-avatar">
                    {msg.role === 'ai' ? 'AI' : 'U'}
                  </div>
                  <div className="message-info">
                    <span className="message-author">
                      {msg.role === 'ai' ? 'AI Assistant' : 'You'}
                    </span>
                    <span className="message-time">{msg.timestamp}</span>
                  </div>
                </div>
                <div className="message-content">
                  {msg.text}
                </div>
                {msg.tool && (
                  <div className="message-tag">
                    {msg.tool.toUpperCase()} MODE
                  </div>
                )}
                {msg.visualizationData && (
                  <div className="visualization-container">
                    <StatsVisualization data={msg.visualizationData} />
                  </div>
                )}
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <form className="chat-input" onSubmit={handleSubmit}>
            <div className="input-container">
              <div className="input-wrapper">
                <div className="input-icon">💭</div>
                <input
                  type="text"
                  className="chat-input-field"
                  placeholder="Ask anything (e.g., 'Show me stats', 'Compare resumes')..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  disabled={processing}
                  autoFocus
                />
              </div>
              <button
                type="submit"
                className="send-button"
                disabled={processing || !query.trim()}
              >
                {processing ? (
                  <>
                    <span className="loading-spinner"></span>
                    Processing...
                  </>
                ) : (
                  <>
                    Send
                    <span className="send-icon">➤</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default App