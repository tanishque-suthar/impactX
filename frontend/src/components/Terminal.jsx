import { useEffect, useRef } from 'react'
import './Terminal.css'

function Terminal({ logs = [] }) {
    const terminalRef = useRef(null)

    useEffect(() => {
        if (terminalRef.current) {
            terminalRef.current.scrollTop = terminalRef.current.scrollHeight
        }
    }, [logs])

    return (
        <div className="terminal">
            <div className="terminal-header">
                <div className="terminal-controls">
                    <div className="terminal-button close"></div>
                    <div className="terminal-button minimize"></div>
                    <div className="terminal-button maximize"></div>
                </div>
                <div className="terminal-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <polyline points="4 17 10 11 4 5"></polyline>
                        <line x1="12" y1="19" x2="20" y2="19"></line>
                    </svg>
                    <span>phoenix-agent-cli</span>
                </div>
                <div className="terminal-spacer"></div>
            </div>

            <div className="terminal-body" ref={terminalRef}>
                {logs.length === 0 ? (
                    <div className="terminal-empty">
                        <p>Terminal ready. Start an analysis to see output...</p>
                    </div>
                ) : (
                    <div className="terminal-content">
                        {logs.map((log, index) => (
                            <div key={index} className="terminal-line">
                                <span className="line-prefix">{'>'}</span>
                                <span className="line-content">{log}</span>
                            </div>
                        ))}
                        <div className="terminal-cursor">_</div>
                    </div>
                )}
            </div>
        </div>
    )
}

export default Terminal
