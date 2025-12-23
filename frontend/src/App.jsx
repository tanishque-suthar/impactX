import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import ReportPage from './pages/ReportPage'
import './App.css'

function App() {
    return (
        <div className="app">
            <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/report/:jobId" element={<ReportPage />} />
            </Routes>
        </div>
    )
}

export default App
