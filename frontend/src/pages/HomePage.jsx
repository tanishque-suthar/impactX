import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import AgentState from '../components/AgentState'
import Terminal from '../components/Terminal'
import { analyzeRepository, getJobStatus } from '../services/api'
import './HomePage.css'

function HomePage() {
    const [repoUrl, setRepoUrl] = useState('')
    const [loading, setLoading] = useState(false)
    const [currentJob, setCurrentJob] = useState(null)
    const [jobStatus, setJobStatus] = useState(null)
    const [terminalLogs, setTerminalLogs] = useState([])
    const navigate = useNavigate()

    useEffect(() => {
        let interval
        if (currentJob && jobStatus?.status !== 'completed' && jobStatus?.status !== 'failed') {
            interval = setInterval(async () => {
                try {
                    const status = await getJobStatus(currentJob)
                    setJobStatus(status)

                    // Add to terminal logs
                    if (status.progress_detail) {
                        setTerminalLogs(prev => {
                            const lastLog = prev[prev.length - 1]
                            if (!lastLog || lastLog !== `# ${status.progress_detail}`) {
                                return [...prev, `# ${status.progress_detail}`]
                            }
                            return prev
                        })
                    }

                    if (status.status === 'completed') {
                        setTerminalLogs(prev => [...prev, '# Analysis completed successfully!', `# Redirecting to report...`])
                        setTimeout(() => {
                            navigate(`/report/${currentJob}`)
                        }, 2000)
                    } else if (status.status === 'failed') {
                        setTerminalLogs(prev => [...prev, `# Error: ${status.error_message || 'Analysis failed'}`])
                        setLoading(false)
                    }
                } catch (error) {
                    console.error('Error fetching status:', error)
                }
            }, 2000)
        }

        return () => {
            if (interval) clearInterval(interval)
        }
    }, [currentJob, jobStatus, navigate])

    const handleSubmit = async (e) => {
        e.preventDefault()

        if (!repoUrl.trim()) return

        setLoading(true)
        setTerminalLogs(['# Initializing connection to Analysis Agent...'])

        try {
            const result = await analyzeRepository(repoUrl)
            setCurrentJob(result.job_id)
            setJobStatus(result)
            setTerminalLogs(prev => [...prev, `# Job ID: ${result.job_id}`, `# Status: ${result.status}`, `# ${result.progress_detail}`])
        } catch (error) {
            console.error('Error starting analysis:', error)
            setTerminalLogs(prev => [...prev, `# Error: ${error.response?.data?.detail || error.message}`])
            setLoading(false)
        }
    }

    const getAgentStatus = () => {
        if (!jobStatus) return 'IDLE'

        switch (jobStatus.status) {
            case 'pending':
                return 'INITIALIZING'
            case 'processing':
                return 'ANALYZING'
            case 'completed':
                return 'COMPLETED'
            case 'failed':
                return 'ERROR'
            default:
                return 'IDLE'
        }
    }

    return (
        <div className="home-page">
            <Header />

            <main className="main-content">
                <div className="hero-section">
                    <h1 className="hero-title">
                        Automated <span className="gradient-text">Code Analysis</span>
                    </h1>
                    <p className="hero-subtitle">
                        Intelligent AI agent that analyzes, modernizes, and generates health reports for
                        codebases using advanced LLM and RAG technologies.
                    </p>

                    <form className="analysis-form" onSubmit={handleSubmit}>
                        <div className="input-group">
                            <svg className="input-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                            </svg>
                            <input
                                type="text"
                                className="repo-input"
                                placeholder="Paste GitHub Repository URL (e.g., github.com/user/repo)"
                                value={repoUrl}
                                onChange={(e) => setRepoUrl(e.target.value)}
                                disabled={loading}
                            />
                        </div>
                        <button
                            type="submit"
                            className={`analyze-button ${loading ? 'loading' : ''}`}
                            disabled={loading || !repoUrl.trim()}
                        >
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            {loading ? 'Analyzing...' : 'Start Analysis'}
                        </button>
                    </form>

                    {repoUrl && (
                        <div className="demo-hint">
                            <p>Try demo: <span className="demo-link" onClick={() => setRepoUrl('github.com/octocat/Hello-World')}>github.com/octocat/Hello-World</span></p>
                        </div>
                    )}
                </div>

                <div className="dashboard-grid">
                    <AgentState status={getAgentStatus()} message={jobStatus?.progress_detail} />
                    <Terminal logs={terminalLogs} />
                </div>
            </main>
        </div>
    )
}

export default HomePage
