import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application configuration"""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./phoenix_agent.db")
    
    # Google Gemini API Keys (for rotation)
    GOOGLE_API_KEYS: List[str] = []
    
    # GitHub Token
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # File whitelist for code analysis
    # Local embedding model (sentence-transformers)
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # Fast, efficient, good quality
    
    ALLOWED_EXTENSIONS: List[str] = [
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".java", ".go", ".rs", ".cpp", ".c", ".h", ".hpp",
        ".md", ".txt", ".json", ".yaml", ".yml", ".xml",
        ".html", ".css", ".sql", ".sh", ".bash"
    ]
    
    # Directories to skip during repo analysis
    SKIP_DIRECTORIES: List[str] = [
        ".git", "node_modules", "venv", ".venv", "env", ".env",
        "build", "dist", "__pycache__", ".pytest_cache",
        "target", "bin", "obj", ".idea", ".vscode"
    ]
    
    # ChromaDB settings
    CHROMA_PERSIST_DIR: str = "chroma_db"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120  # 15% of chunk size
    
    # RAG settings
    TOP_K_RESULTS: int = 10  # Number of similar chunks to retrieve
    
    # Batch update settings
    BATCH_UPDATE_INTERVAL: int = 10  # Update progress every N files
    
    def __init__(self):
        """Load and validate configuration"""
        # Load all Google API keys
        i = 1
        while True:
            key = os.getenv(f"GOOGLE_API_KEY_{i}")
            if key:
                self.GOOGLE_API_KEYS.append(key)
                i += 1
            else:
                break
        
        # Fallback to single key if numbered keys not found
        if not self.GOOGLE_API_KEYS:
            single_key = os.getenv("GOOGLE_API_KEY")
            if single_key:
                self.GOOGLE_API_KEYS.append(single_key)
        
        if not self.GOOGLE_API_KEYS:
            raise ValueError("No Google API keys found. Set GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, etc. in .env")


# Global settings instance
settings = Settings()
