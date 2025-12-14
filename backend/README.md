# Phoenix Agent - Backend MVP

Autonomous AI DevOps tool for analyzing and modernizing legacy codebases.

## Features

- **Repository Ingestion**: Clone and analyze GitHub repositories
- **Local RAG Embeddings**: ChromaDB vector storage with HuggingFace sentence-transformers (offline, cost-free)
- **AI-Powered Analysis**: Gemini 2.0 Flash generates detailed health reports with specific code insights
- **Intelligent Code Sampling**: Smart file prioritization for comprehensive analysis
- **Health Reports**: Code quality scores, vulnerabilities, technical debt, and modernization suggestions
- **Background Processing**: Async job handling with granular status tracking
- **Repository Retention**: Cloned repos preserved for future modernization workflows

## Setup

### Prerequisites

- Python 3.10+
- Google Gemini API keys (for LLM analysis only - embeddings are local)
- GitHub token (optional, for private repos)
- ~500MB disk space for embedding model (one-time download)
- Sufficient disk space for cloned repositories (retained for modernization)

### Installation

1. **Clone the repository**
```bash
cd backend
```

2. **Create virtual environment**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
copy .env.example .env
# Edit .env with your API keys
```

Required environment variables:
- `GOOGLE_API_KEY_1`, `GOOGLE_API_KEY_2`, `GOOGLE_API_KEY_3`: Google Gemini API keys for LLM analysis (rotation enabled)
- `GITHUB_TOKEN`: GitHub personal access token (optional for public repos, required for private)
- `DATABASE_URL`: SQLite database path (default: `sqlite:///./phoenix_agent.db`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

**Note:** First run will download the `all-MiniLM-L6-v2` embedding model (~80MB) to `~/.cache/huggingface/`. Subsequent runs are fully offline for embeddings.

### Running the Application

```bash
# Development mode with auto-reload
python -m app.main

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

## API Endpoints

### POST /api/analyze
Initiate repository analysis

**Request:**
```json
{
  "repo_url": "https://github.com/owner/repo",
  "branch": "main"  // optional
}
```

**Response:**
```json
{
  "job_id": 1,
  "repo_url": "https://github.com/owner/repo",
  "status": "pending",
  "progress_detail": "Analysis queued",
  "created_at": "2025-12-14T10:00:00Z",
  "updated_at": "2025-12-14T10:00:00Z"
}
```

### GET /api/status/{job_id}
Get job status

**Response:**
```json
{
  "job_id": 1,
  "status": "processing",
  "progress_detail": "Embedding files (45/100)",
  ...
}
```

Statuses: `pending`, `processing`, `completed`, `failed`

### GET /api/report/{job_id}
Get health report (only for completed jobs)

**Response:**
```json
{
  "job_id": 1,
  "report": {
    "code_quality_score": 75.5,
    "vulnerabilities": [...],
    "tech_debt_items": [...],
    "modernization_suggestions": [...],
    "overall_summary": "..."
  },
  "created_at": "2025-12-14T10:05:00Z"
}
```

## Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── models/
│   │   ├── database.py      # SQLAlchemy models
│   │   └── schemas.py       # Pydantic schemas
│   ├── services/
│   │   ├── github_service.py    # GitHub repo operations
│   │   ├── rag_service.py       # ChromaDB RAG
│   │   └── llm_service.py       # Gemini LLM integration
│   ├── api/
│   │   ├── routes.py        # API endpoints
│   │   └── dependencies.py  # FastAPI dependencies
│   └── utils/
│       └── logger.py        # Logging utilities
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables
```
`temp_repos/{job_id}/`
2. **Parse Files**: Filter by whitelisted extensions (`.py`, `.js`, `.java`, etc.), skip excluded directories (node_modules, .git)
3. **Chunk Code**: RecursiveCharacterTextSplitter creates 800-char chunks with 15% overlap
4. **Generate Embeddings**: HuggingFace `all-MiniLM-L6-v2` model creates vector embeddings locally (no API calls)
5. **Store in ChromaDB**: Batch insert all embeddings into persistent collection
6. **Detect Languages & Dependencies**: Parse file extensions and dependency manifests
7. **Intelligent Sampling**: Select 25 diverse, representative code samples prioritizing:
   - Important files (main, index, app, config)
   - First chunks (imports, definitions)
   - Directory diversity
8. **AI Analysis**: Gemini 2.0 Flash analyzes samples with detailed prompt for specific insights
9. **Generate Report**: Structured health report with vulnerabilities, tech debt, modernization suggestions
10. **Cleanup**: Delete ChromaDB collection (embeddings), **keep cloned repo** for future modernization
11. **Persist**: Save report to SQLite for retrieval 15% overlap
**Embedding Model:**
- `EMBEDDING_MODEL`: `"all-MiniLM-L6-v2"` - Local HuggingFace model (384-dim vectors)

**File Processing:**
- `ALLOWED_EXTENSIONS`: Whitelisted text file extensions (18 types)
- `SKIP_DIRECTORIES`: Excluded directories (node_modules, .git, build, dist, etc.)

**Chunking:**
- `CHUNK_SIZE`: 800 characters
- `CHUNK_OVERLAP`: 120 characters (15%)

**RAG Sampling:**
- `TOP_K_RESULTS`: 10 similar chunks for query-based retrieval
- `BATCH_UPDATE_INTERVAL`: Progress update frequency (every 10 files)
**Current Implementation:**
- **Single-threaded**: Simple job locking for one analysis at a time (MVP)
- **API Key Rotation**: Round-robin across Gemini API keys to avoid rate limits
- **Local Embeddings**: Sentence-transformers run on CPU (GPU optional for speed)
- **Repository Retention**: Cloned repos kept in `temp_repos/` for modernization features
- **ChromaDB Cleanup**: Embedding collections deleted after analysis (not needed for modernization)
- **Batch Processing**: All embeddings generated in single batch for performance
- **Batch Updates**: Job progress updated every 10 files to reduce DB I/O

**Planned Features:**
- **Automatic Cleanup**: Time-based retention policy (delete repos after X hours/days)
- **Modernization Endpoints**: Dockerfile generation, dependency upgrades, PR creation
- **Security Scanning**: OWASP ZAP integration for runtime vulnerability testing
- *Roadmap

### Phase 1: Core Analysis (✅ Complete)
- [x] Repository cloning and ingestion
- [x] Local embedding generation (sentence-transformers)
- [x] Intelligent code sampling (25 diverse samples)
- [x] ChromaDB vector storage
- [x] Gemini-powered health reports
- [x] SQLite job persistence
- [x] Background task processing

### Phase 2: Modernization Engine (🚧 In Progress)
- [ ] Time-based repository retention (delete after 24-48 hours)
- [ ] Dockerfile generation from detected tech stack
- [ ] Dependency upgrade recommendations
- [ ] GitHub PR creation with automated fixes
- [ ] Code refactoring suggestions

### Phase 3: Frontend & UX (📋 Planned)
- [ ] React + Vite dashboard
- [ ] Real-time job progress (WebSocket/SSE)
- [ ] Visual health report rendering
- [Storage & Cleanup

**Disk Usage:**
- Embedding model: ~80MB (cached in `~/.cache/huggingface/`)
- ChromaDB collections: Deleted after analysis (temporary)
- Cloned repositories: Kept in `temp_repos/` until manual cleanup
- Database: Grows with job history (~50KB per job)

**Manual Cleanup:**
```bash
# Delete specific repo
rm -rf temp_repos/1/

# Delete all repos
rm -rf temp_repos/

# Reset database
rm phoenix_agent.db
```

**Automatic Cleanup (Coming Soon):**
Repositories will auto-delete after 24-48 hours (configurable retention period).

## Troubleshooting

**Import errors:**
- Ensure virtual environment is activated: `.venv\Scripts\activate`
- Reinstall dependencies: `pip install -r requirements.txt`

**Embedding model download fails:**
- Check internet connection (first run only)
- Ensure ~500MB disk space available
- Model caches in `~/.cache/huggingface/hub/`

**Database errors:**
- Delete `phoenix_agent.db` and restart to reset database
- Check SQLite version: `sqlite3 --version`

**ChromaDB errors:**
- Delete `chroma_db/` directory
- Check disk space for embeddings storage
- Ensure write permissions

**API rate limits (Gemini):**
- Add more API keys to `.env` (GOOGLE_API_KEY_1, _2, _3, etc.)
- Currently uses round-robin rotation automatically
- Free tier: 15 RPM, 1M TPM, 1500 RPD per key

**Out of disk space:**
- Check `temp_repos/` size: `du -sh temp_repos/`
- Manually delete old analysis jobs
- Implement retention cleanup (see Roadmap)
## Testing

```bash
pytest tests/ -v
```

## Development Notes

- **Single-threaded**: MVP uses simple locking for one analysis at a time
- **API Key Rotation**: Round-robin across configured Gemini API keys
- **ChromaDB Cleanup**: Collections deleted after analysis to save disk space
- **Batch Updates**: Job progress updated every 10 files to reduce DB writes

## Next Steps

- Add frontend (React + Vite)
- Implement Path A: Modernization (Dockerfile generation, PR creation)
- Implement Path B: Chaos Mode (OWASP ZAP security testing)
- Add containerization (Docker, docker-compose)
- CI/CD with GitHub Actions
- Multi-threading support
- User authentication

## Troubleshooting

**Import errors:**
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

**Database errors:**
- Delete `phoenix_agent.db` and restart to reset database

**ChromaDB errors:**
- Delete `chroma_db/` directory
- Check disk space

**API rate limits:**
- Add more API keys to `.env` (GOOGLE_API_KEY_1, _2, _3, etc.)
- Reduce concurrent analysis

## License

MIT
