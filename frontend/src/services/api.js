import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

export const analyzeRepository = async (repoUrl, branch = null) => {
    const response = await api.post('/api/analyze', {
        repo_url: repoUrl,
        branch: branch,
    })
    return response.data
}

export const getJobStatus = async (jobId) => {
    const response = await api.get(`/api/status/${jobId}`)
    return response.data
}

export const getHealthReport = async (jobId) => {
    const response = await api.get(`/api/report/${jobId}`)
    return response.data
}

export default api
