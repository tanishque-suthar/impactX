import './AgentState.css'

function AgentState({ status = 'IDLE', message = 'Waiting for repository...' }) {
    const getStatusColor = () => {
        switch (status) {
            case 'ANALYZING':
                return 'status-analyzing'
            case 'COMPLETED':
                return 'status-completed'
            case 'ERROR':
                return 'status-error'
            case 'INITIALIZING':
                return 'status-initializing'
            default:
                return 'status-idle'
        }
    }

    return (
        <div className="agent-state">
            <div className="agent-state-header">
                <div className="header-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                </div>
                <h3 className="agent-state-title">Agent State</h3>
                <div className={`status-badge ${getStatusColor()}`}>
                    <span className="status-label">STATUS: {status}</span>
                </div>
            </div>

            <div className="agent-state-body">
                <div className="agent-visual">
                    {status === 'ANALYZING' || status === 'INITIALIZING' ? (
                        <div className="pulse-animation">
                            <div className="pulse-ring"></div>
                            <div className="pulse-ring"></div>
                            <div className="pulse-ring"></div>
                            <div className="pulse-core"></div>
                        </div>
                    ) : status === 'COMPLETED' ? (
                        <div className="check-animation">
                            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                        </div>
                    ) : status === 'ERROR' ? (
                        <div className="error-animation">
                            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </div>
                    ) : (
                        <div className="idle-animation">
                            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                    )}
                </div>

                <div className="agent-message">
                    <p>{message}</p>
                </div>
            </div>
        </div>
    )
}

export default AgentState
