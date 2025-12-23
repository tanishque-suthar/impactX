import './Header.css'

function Header() {
    return (
        <header className="header">
            <div className="header-content">
                <div className="logo-container">
                    <div className="logo-icon">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                            <path d="M13 10V3L4 14h7v7l9-11h-7z" fill="currentColor" />
                        </svg>
                    </div>
                    <div className="logo-text">
                        <span className="logo-name">Phoenix</span>
                        <span className="logo-subtitle">AGENT</span>
                    </div>
                </div>

                <div className="status-indicator">
                    <div className="status-dot"></div>
                    <span className="status-text">SYSTEM ONLINE</span>
                </div>
            </div>
        </header>
    )
}

export default Header
