import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import { getHealthReport } from '../services/api'
import './ReportPage.css'

function ReportPage() {
    const { jobId } = useParams()
    const navigate = useNavigate()
    const [report, setReport] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        const fetchReport = async () => {
            try {
                setLoading(true)
                const data = await getHealthReport(jobId)
                setReport(data)
            } catch (err) {
                console.error('Error fetching report:', err)
                setError(err.response?.data?.detail || 'Failed to load report')
            } finally {
                setLoading(false)
            }
        }

        fetchReport()
    }, [jobId])

    const getSeverityColor = (severity) => {
        const colors = {
            critical: 'severity-critical',
            high: 'severity-high',
            medium: 'severity-medium',
            low: 'severity-low',
        }
        return colors[severity?.toLowerCase()] || 'severity-medium'
    }

    const getScoreColor = (score) => {
        if (score >= 80) return 'score-excellent'
        if (score >= 60) return 'score-good'
        if (score >= 40) return 'score-fair'
        return 'score-poor'
    }

    if (loading) {
        return (
            <div className="report-page">
                <Header />
                <div className="loading-container">
                    <div className="spinner"></div>
                    <p>Loading health report...</p>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="report-page">
                <Header />
                <div className="error-container">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <h2>Error Loading Report</h2>
                    <p>{error}</p>
                    <button className="back-button" onClick={() => navigate('/')}>
                        Back to Home
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="report-page">
            <Header />

            <main className="report-content">
                <div className="report-header">
                    <button className="back-link" onClick={() => navigate('/')}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                        Back to Analysis
                    </button>
                    <h1 className="report-title">Health Report</h1>
                    <p className="report-meta">Job ID: {jobId}</p>
                </div>

                <div className="report-grid">
                    {/* Summary Card */}
                    <div className="report-card summary-card">
                        <h2 className="card-title">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Summary
                        </h2>
                        <div className="summary-content">
                            <p>{report.report.summary}</p>
                        </div>
                    </div>

                    {/* Overall Score Card */}
                    <div className="report-card score-card">
                        <h2 className="card-title">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                            Overall Score
                        </h2>
                        <div className="score-display">
                            <div className={`score-value ${getScoreColor(report.report.overall_score)}`}>
                                {report.report.overall_score}
                                <span className="score-max">/100</span>
                            </div>
                        </div>
                    </div>

                    {/* Vulnerabilities Card */}
                    <div className="report-card">
                        <h2 className="card-title">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            Security Vulnerabilities
                            <span className="count-badge">{report.report.vulnerabilities?.length || 0}</span>
                        </h2>
                        <div className="card-content">
                            {report.report.vulnerabilities && report.report.vulnerabilities.length > 0 ? (
                                <div className="items-list">
                                    {report.report.vulnerabilities.map((vuln, idx) => (
                                        <div key={idx} className="item vulnerability-item">
                                            <div className="item-header">
                                                <span className={`severity-badge ${getSeverityColor(vuln.severity)}`}>
                                                    {vuln.severity}
                                                </span>
                                                {vuln.affected_component && (
                                                    <span className="component-tag">{vuln.affected_component}</span>
                                                )}
                                            </div>
                                            <p className="item-description">{vuln.description}</p>
                                            {vuln.recommendation && (
                                                <p className="item-recommendation">
                                                    <strong>Recommendation:</strong> {vuln.recommendation}
                                                </p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="empty-state">No vulnerabilities detected</p>
                            )}
                        </div>
                    </div>

                    {/* Technical Debt Card */}
                    <div className="report-card">
                        <h2 className="card-title">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                            </svg>
                            Technical Debt
                            <span className="count-badge">{report.report.tech_debt?.length || 0}</span>
                        </h2>
                        <div className="card-content">
                            {report.report.tech_debt && report.report.tech_debt.length > 0 ? (
                                <div className="items-list">
                                    {report.report.tech_debt.map((debt, idx) => (
                                        <div key={idx} className="item debt-item">
                                            <div className="item-header">
                                                <span className="category-tag">{debt.category}</span>
                                                {debt.priority && (
                                                    <span className={`priority-badge priority-${debt.priority.toLowerCase()}`}>
                                                        {debt.priority}
                                                    </span>
                                                )}
                                            </div>
                                            <p className="item-description">{debt.description}</p>
                                            {debt.file_path && (
                                                <p className="item-file">
                                                    <code>{debt.file_path}</code>
                                                </p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="empty-state">No technical debt identified</p>
                            )}
                        </div>
                    </div>

                    {/* Modernization Suggestions Card */}
                    <div className="report-card">
                        <h2 className="card-title">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            Modernization Suggestions
                            <span className="count-badge">{report.report.modernization_suggestions?.length || 0}</span>
                        </h2>
                        <div className="card-content">
                            {report.report.modernization_suggestions && report.report.modernization_suggestions.length > 0 ? (
                                <div className="items-list">
                                    {report.report.modernization_suggestions.map((suggestion, idx) => (
                                        <div key={idx} className="item suggestion-item">
                                            <div className="item-header">
                                                <span className="type-tag">{suggestion.type}</span>
                                                {suggestion.effort_estimate && (
                                                    <span className="effort-tag">{suggestion.effort_estimate}</span>
                                                )}
                                            </div>
                                            <p className="item-description">{suggestion.description}</p>
                                            {suggestion.rationale && (
                                                <p className="item-rationale">
                                                    <strong>Rationale:</strong> {suggestion.rationale}
                                                </p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="empty-state">No modernization suggestions</p>
                            )}
                        </div>
                    </div>

                    {/* Recommendations Card */}
                    <div className="report-card full-width">
                        <h2 className="card-title">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                            </svg>
                            Recommendations
                        </h2>
                        <div className="card-content">
                            {report.report.recommendations && report.report.recommendations.length > 0 ? (
                                <ul className="recommendations-list">
                                    {report.report.recommendations.map((rec, idx) => (
                                        <li key={idx} className="recommendation-item">
                                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                            </svg>
                                            {rec}
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="empty-state">No recommendations available</p>
                            )}
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}

export default ReportPage
