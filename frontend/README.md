# ImpactX Frontend

Modern React frontend for the ImpactX Code Analysis Agent.

## Features

- 🎨 Modern dark UI with gradient accents
- 📊 Real-time analysis progress tracking
- 🔍 Detailed health reports with visualizations
- 🚀 Built with Vite for fast development
- 📱 Responsive design

## Getting Started

### Prerequisites

- Node.js 16+ and npm

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

Create a `.env` file in the frontend root:

```env
VITE_API_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── Header.jsx
│   │   ├── AgentState.jsx
│   │   └── Terminal.jsx
│   ├── pages/           # Page components
│   │   ├── HomePage.jsx
│   │   └── ReportPage.jsx
│   ├── services/        # API integration
│   │   └── api.js
│   ├── App.jsx          # Main app component
│   ├── main.jsx         # Entry point
│   └── index.css        # Global styles
├── index.html
├── vite.config.js
└── package.json
```

## Usage

1. Enter a GitHub repository URL
2. Click "Start Analysis"
3. Monitor progress in the Agent State panel
4. View terminal output in real-time
5. Access detailed health report upon completion

## Tech Stack

- **React 18** - UI library
- **Vite** - Build tool
- **React Router** - Routing
- **Axios** - HTTP client
- **CSS3** - Styling with custom properties

## Available Scripts

- `npm run dev` - Start development server on port 3000
- `npm run build` - Build for production
- `npm run preview` - Preview production build

## API Integration

The frontend connects to the backend API with the following endpoints:

- `POST /api/analyze` - Start repository analysis
- `GET /api/status/{job_id}` - Get job status
- `GET /api/report/{job_id}` - Get health report

## License

MIT
