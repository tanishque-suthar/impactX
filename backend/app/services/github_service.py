import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from git import Repo
from github import Github
from app.config import settings
from app.utils.logger import logger


class GitHubService:
    """Service for GitHub repository operations"""
    
    def __init__(self):
        self.github_token = settings.GITHUB_TOKEN
        self.temp_base_dir = Path("temp_repos")
        self.temp_base_dir.mkdir(exist_ok=True)
    
    def clone_repository(self, repo_url: str, job_id: int, branch: Optional[str] = None) -> Path:
        """
        Clone a GitHub repository to temporary directory
        
        Args:
            repo_url: GitHub repository URL
            job_id: Analysis job ID (used for directory naming)
            branch: Optional branch name
            
        Returns:
            Path to cloned repository
        """
        clone_path = self.temp_base_dir / str(job_id)
        
        # Clean up if exists
        if clone_path.exists():
            shutil.rmtree(clone_path)
        
        try:
            logger.info(f"Cloning repository {repo_url} to {clone_path}")
            
            # Clone with depth=1 for faster cloning
            if branch:
                Repo.clone_from(repo_url, clone_path, branch=branch, depth=1)
            else:
                Repo.clone_from(repo_url, clone_path, depth=1)
            
            logger.info(f"Successfully cloned repository to {clone_path}")
            return clone_path
            
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            raise
    
    def get_repository_files(self, repo_path: Path) -> List[Dict[str, any]]:
        """
        Get all text files from repository with content
        
        Args:
            repo_path: Path to cloned repository
            
        Returns:
            List of dicts with file metadata and content
        """
        files_data = []
        
        for file_path in repo_path.rglob("*"):
            # Skip directories
            if file_path.is_dir():
                continue
            
            # Skip if in excluded directories
            if any(skip_dir in file_path.parts for skip_dir in settings.SKIP_DIRECTORIES):
                continue
            
            # Check file extension
            if file_path.suffix.lower() not in settings.ALLOWED_EXTENSIONS:
                continue
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Get relative path
                relative_path = file_path.relative_to(repo_path)
                
                files_data.append({
                    "path": str(relative_path),
                    "content": content,
                    "extension": file_path.suffix.lower(),
                    "size": len(content)
                })
                
            except Exception as e:
                logger.warning(f"Could not read file {file_path}: {e}")
                continue
        
        logger.info(f"Found {len(files_data)} text files in repository")
        return files_data
    
    def detect_languages(self, files_data: List[Dict[str, any]]) -> Dict[str, int]:
        """
        Detect programming languages from file extensions
        
        Args:
            files_data: List of file metadata dicts
            
        Returns:
            Dictionary mapping language to file count
        """
        language_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript (React)",
            ".tsx": "TypeScript (React)",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".cpp": "C++",
            ".c": "C",
            ".h": "C/C++ Header",
            ".hpp": "C++ Header",
            ".cs": "C#",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
        }
        
        languages = {}
        for file_data in files_data:
            ext = file_data["extension"]
            lang = language_map.get(ext, f"Other ({ext})")
            languages[lang] = languages.get(lang, 0) + 1
        
        return dict(sorted(languages.items(), key=lambda x: x[1], reverse=True))
    
    def parse_dependencies(self, repo_path: Path) -> Dict[str, List[str]]:
        """
        Parse dependency files to extract dependencies
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Dictionary mapping ecosystem to list of dependencies
        """
        dependencies = {}
        
        # Python - requirements.txt
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    deps = []
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Extract package name (before ==, >=, etc.)
                            pkg = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].strip()
                            deps.append(pkg)
                    dependencies["Python"] = deps
            except Exception as e:
                logger.warning(f"Could not parse requirements.txt: {e}")
        
        # JavaScript/Node - package.json
        pkg_file = repo_path / "package.json"
        if pkg_file.exists():
            try:
                import json
                with open(pkg_file, 'r', encoding='utf-8') as f:
                    pkg_json = json.load(f)
                    deps = []
                    if "dependencies" in pkg_json:
                        deps.extend(pkg_json["dependencies"].keys())
                    if "devDependencies" in pkg_json:
                        deps.extend(pkg_json["devDependencies"].keys())
                    dependencies["JavaScript/Node"] = deps
            except Exception as e:
                logger.warning(f"Could not parse package.json: {e}")
        
        # Java - pom.xml (simplified - just check existence)
        pom_file = repo_path / "pom.xml"
        if pom_file.exists():
            dependencies["Java (Maven)"] = ["See pom.xml"]
        
        # Go - go.mod
        go_file = repo_path / "go.mod"
        if go_file.exists():
            try:
                with open(go_file, 'r', encoding='utf-8') as f:
                    deps = []
                    for line in f:
                        line = line.strip()
                        if line.startswith("require "):
                            pkg = line.replace("require ", "").split()[0]
                            deps.append(pkg)
                    dependencies["Go"] = deps
            except Exception as e:
                logger.warning(f"Could not parse go.mod: {e}")
        
        # Rust - Cargo.toml
        cargo_file = repo_path / "Cargo.toml"
        if cargo_file.exists():
            dependencies["Rust"] = ["See Cargo.toml"]
        
        return dependencies
    
    def cleanup_repository(self, job_id: int):
        """
        Delete cloned repository directory
        
        Args:
            job_id: Analysis job ID
        """
        clone_path = self.temp_base_dir / str(job_id)
        
        if clone_path.exists():
            try:
                # Windows fix: Make .git files writable before deletion
                import stat
                def handle_remove_readonly(func, path, exc):
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                
                shutil.rmtree(clone_path, onerror=handle_remove_readonly)
                logger.info(f"Cleaned up repository directory: {clone_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup repository {clone_path}: {e}")
    
    def analyze_repository(self, repo_url: str, job_id: int, branch: Optional[str] = None) -> Tuple[List[Dict], Dict[str, int], Dict[str, List[str]]]:
        """
        Complete repository analysis workflow
        
        Args:
            repo_url: GitHub repository URL
            job_id: Analysis job ID
            branch: Optional branch name
            
        Returns:
            Tuple of (files_data, languages, dependencies)
        """
        # Clone repository
        repo_path = self.clone_repository(repo_url, job_id, branch)
        
        # Get files
        files_data = self.get_repository_files(repo_path)
        
        # Detect languages
        languages = self.detect_languages(files_data)
        
        # Parse dependencies
        dependencies = self.parse_dependencies(repo_path)
        
        return files_data, languages, dependencies
