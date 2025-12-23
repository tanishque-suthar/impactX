from typing import List, Dict, Optional
from pathlib import Path
import re
import ast
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from app.config import settings
from app.utils.logger import logger


class RAGService:
    """Service for RAG operations using ChromaDB with code-aware processing"""
    
    def __init__(self):
        """Initialize ChromaDB client and embeddings"""
        # Initialize persistent ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # Initialize local embeddings using sentence-transformers
        logger.info(f"Loading local embedding model: {settings.EMBEDDING_MODEL}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},  # Use 'cuda' if GPU available
            encode_kwargs={'normalize_embeddings': True}  # Better for similarity search
        )
        
        # Default text splitter (fallback)
        self.default_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Language-specific splitters
        self.language_splitters = self._initialize_language_splitters()
        
        logger.info("RAGService initialized with ChromaDB and code-aware splitting")
    
    def _initialize_language_splitters(self) -> Dict[str, RecursiveCharacterTextSplitter]:
        """Initialize language-specific text splitters"""
        splitters = {}
        
        # Language mapping for supported languages
        language_map = {
            '.py': Language.PYTHON,
            '.js': Language.JS,
            '.jsx': Language.JS,
            '.ts': Language.TS,
            '.tsx': Language.TS,
            '.java': Language.JAVA,
            '.cpp': Language.CPP,
            '.c': Language.CPP,
            '.cc': Language.CPP,
            '.cxx': Language.CPP,
            '.go': Language.GO,
            '.rs': Language.RUST,
            '.php': Language.PHP,
            '.rb': Language.RUBY,
            '.swift': Language.SWIFT,
            '.kt': Language.KOTLIN,
            '.scala': Language.SCALA,
            '.cs': Language.CSHARP,
            '.html': Language.HTML,
            '.md': Language.MARKDOWN
        }
        
        for ext, lang in language_map.items():
            try:
                splitters[ext] = RecursiveCharacterTextSplitter.from_language(
                    language=lang,
                    chunk_size=settings.CHUNK_SIZE,
                    chunk_overlap=settings.CHUNK_OVERLAP
                )
            except Exception as e:
                logger.warning(f"Failed to create splitter for {ext}: {e}")
                splitters[ext] = self.default_splitter
        
        return splitters
    
    def _get_splitter_for_file(self, extension: str) -> RecursiveCharacterTextSplitter:
        """Get appropriate text splitter for file extension"""
        return self.language_splitters.get(extension, self.default_splitter)
    
    def _extract_code_metadata(self, content: str, extension: str, file_path: str) -> Dict:
        """Extract code-specific metadata from file content"""
        metadata = {
            "functions": [],
            "classes": [],
            "imports": [],
            "complexity_score": 0,
            "lines_of_code": len([line for line in content.split('\n') if line.strip()]),
            "total_lines": len(content.split('\n'))
        }
        
        try:
            if extension == '.py':
                metadata.update(self._extract_python_metadata(content))
            elif extension in ['.js', '.jsx', '.ts', '.tsx']:
                metadata.update(self._extract_javascript_metadata(content))
            elif extension == '.java':
                metadata.update(self._extract_java_metadata(content))
            # Add more language-specific extractors as needed
            
        except Exception as e:
            logger.warning(f"Failed to extract metadata for {file_path}: {e}")
        
        return metadata
    
    def _extract_python_metadata(self, content: str) -> Dict:
        """Extract Python-specific metadata using AST"""
        metadata = {"functions": [], "classes": [], "imports": [], "complexity_score": 0}
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metadata["functions"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "is_async": isinstance(node, ast.AsyncFunctionDef)
                    })
                elif isinstance(node, ast.ClassDef):
                    metadata["classes"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "bases": [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases]
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            metadata["imports"].append(alias.name)
                    else:  # ImportFrom
                        module = node.module or ""
                        for alias in node.names:
                            metadata["imports"].append(f"{module}.{alias.name}" if module else alias.name)
            
            # Simple complexity score based on control flow nodes
            complexity_nodes = (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.AsyncWith)
            metadata["complexity_score"] = sum(1 for node in ast.walk(tree) if isinstance(node, complexity_nodes))
            
        except SyntaxError as e:
            logger.warning(f"Python syntax error during metadata extraction: {e}")
        except Exception as e:
            logger.warning(f"Error extracting Python metadata: {e}")
        
        return metadata
    
    def _extract_javascript_metadata(self, content: str) -> Dict:
        """Extract JavaScript/TypeScript metadata using regex patterns"""
        metadata = {"functions": [], "classes": [], "imports": [], "complexity_score": 0}
        
        try:
            # Function patterns
            func_patterns = [
                r'function\s+(\w+)\s*\(',
                r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>',
                r'(\w+)\s*:\s*function\s*\(',
                r'async\s+function\s+(\w+)\s*\('
            ]
            
            for pattern in func_patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    metadata["functions"].append({
                        "name": match.group(1),
                        "line": content[:match.start()].count('\n') + 1
                    })
            
            # Class patterns
            class_matches = re.finditer(r'class\s+(\w+)', content, re.MULTILINE)
            for match in class_matches:
                metadata["classes"].append({
                    "name": match.group(1),
                    "line": content[:match.start()].count('\n') + 1
                })
            
            # Import patterns
            import_patterns = [
                r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]',
                r'import\s+[\'"]([^\'"]+)[\'"]',
                r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
            ]
            
            for pattern in import_patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    metadata["imports"].append(match.group(1))
            
            # Simple complexity score
            complexity_patterns = [r'\bif\b', r'\bfor\b', r'\bwhile\b', r'\btry\b', r'\bcatch\b']
            metadata["complexity_score"] = sum(
                len(re.findall(pattern, content, re.IGNORECASE)) for pattern in complexity_patterns
            )
            
        except Exception as e:
            logger.warning(f"Error extracting JavaScript metadata: {e}")
        
        return metadata
    
    def _extract_java_metadata(self, content: str) -> Dict:
        """Extract Java metadata using regex patterns"""
        metadata = {"functions": [], "classes": [], "imports": [], "complexity_score": 0}
        
        try:
            # Method patterns
            method_matches = re.finditer(
                r'(?:public|private|protected|static|\s)*\s+\w+\s+(\w+)\s*\([^)]*\)\s*\{',
                content, re.MULTILINE
            )
            for match in method_matches:
                metadata["functions"].append({
                    "name": match.group(1),
                    "line": content[:match.start()].count('\n') + 1
                })
            
            # Class patterns
            class_matches = re.finditer(
                r'(?:public|private|protected|\s)*\s*class\s+(\w+)',
                content, re.MULTILINE
            )
            for match in class_matches:
                metadata["classes"].append({
                    "name": match.group(1),
                    "line": content[:match.start()].count('\n') + 1
                })
            
            # Import patterns
            import_matches = re.finditer(r'import\s+([^;]+);', content, re.MULTILINE)
            for match in import_matches:
                metadata["imports"].append(match.group(1).strip())
            
            # Complexity score
            complexity_patterns = [r'\bif\b', r'\bfor\b', r'\bwhile\b', r'\btry\b', r'\bcatch\b']
            metadata["complexity_score"] = sum(
                len(re.findall(pattern, content, re.IGNORECASE)) for pattern in complexity_patterns
            )
            
        except Exception as e:
            logger.warning(f"Error extracting Java metadata: {e}")
        
        return metadata
    
    def _sanitize_collection_name(self, repo_url: str, job_id: int) -> str:
        """
        Create a valid ChromaDB collection name
        
        Args:
            repo_url: Repository URL
            job_id: Job ID
            
        Returns:
            Sanitized collection name
        """
        # Extract owner/repo from URL
        parts = repo_url.rstrip('/').split('/')
        if len(parts) >= 2:
            owner = parts[-2]
            repo = parts[-1].replace('.git', '')
            name = f"{owner}_{repo}_{job_id}"
        else:
            name = f"repo_{job_id}"
        
        # Sanitize: only alphanumeric, underscores, hyphens
        name = ''.join(c if c.isalnum() or c in ['_', '-'] else '_' for c in name)
        return name.lower()[:63]  # ChromaDB has 63 char limit
    
    def create_embeddings(
        self,
        files_data: List[Dict],
        repo_url: str,
        job_id: int,
        progress_callback=None
    ) -> str:
        """
        Create embeddings for repository files with code-aware processing
        
        Args:
            files_data: List of file metadata with content
            repo_url: Repository URL
            job_id: Job ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Collection name
        """
        collection_name = self._sanitize_collection_name(repo_url, job_id)
        
        logger.info(f"Creating collection: {collection_name}")
        
        # Create or get collection
        try:
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"job_id": str(job_id), "repo_url": repo_url}
            )
        except Exception as e:
            # Collection might already exist, get it
            logger.warning(f"Collection exists, getting it: {e}")
            collection = self.chroma_client.get_collection(name=collection_name)
        
        # Process files in batches
        total_files = len(files_data)
        chunk_id = 0
        
        # Collect all documents, embeddings, metadatas, and ids first
        all_documents = []
        all_metadatas = []
        all_ids = []
        
        for idx, file_data in enumerate(files_data):
            file_path = file_data["path"]
            content = file_data["content"]
            extension = file_data["extension"]
            
            # Skip empty files
            if not content.strip():
                continue
            
            # Extract code metadata for the entire file
            code_metadata = self._extract_code_metadata(content, extension, file_path)
            
            # Get appropriate splitter for this file type
            splitter = self._get_splitter_for_file(extension)
            
            # Split content into chunks using code-aware splitter
            chunks = splitter.split_text(content)
            
            # Prepare documents for this file
            for chunk_idx, chunk in enumerate(chunks):
                all_documents.append(chunk)
                
                # Enhanced metadata with code information
                chunk_metadata = {
                    "file_path": file_path,
                    "chunk_index": chunk_idx,
                    "language": extension,
                    "total_chunks": len(chunks),
                    # File-level metadata
                    "file_functions_count": len(code_metadata.get("functions", [])),
                    "file_classes_count": len(code_metadata.get("classes", [])),
                    "file_imports_count": len(code_metadata.get("imports", [])),
                    "file_complexity_score": code_metadata.get("complexity_score", 0),
                    "file_lines_of_code": code_metadata.get("lines_of_code", 0),
                    "file_total_lines": code_metadata.get("total_lines", 0),
                }
                
                # Add chunk-specific code elements if they exist in this chunk
                chunk_functions = self._extract_chunk_functions(chunk, extension)
                chunk_classes = self._extract_chunk_classes(chunk, extension)
                chunk_imports = self._extract_chunk_imports(chunk, extension)
                
                # Convert lists to comma-separated strings for ChromaDB compatibility
                if chunk_functions:
                    chunk_metadata["chunk_functions"] = ",".join(chunk_functions)
                if chunk_classes:
                    chunk_metadata["chunk_classes"] = ",".join(chunk_classes)
                if chunk_imports:
                    chunk_metadata["chunk_imports"] = ",".join(chunk_imports)
                
                # Add all file-level functions, classes, imports as searchable metadata
                if code_metadata.get("functions"):
                    chunk_metadata["all_functions"] = ",".join([f["name"] for f in code_metadata["functions"]])
                if code_metadata.get("classes"):
                    chunk_metadata["all_classes"] = ",".join([c["name"] for c in code_metadata["classes"]])
                if code_metadata.get("imports"):
                    chunk_metadata["all_imports"] = ",".join(code_metadata["imports"])
                
                all_metadatas.append(chunk_metadata)
                all_ids.append(f"chunk_{chunk_id}")
                chunk_id += 1
            
            # Progress callback (batch updates every N files)
            if progress_callback and (idx + 1) % settings.BATCH_UPDATE_INTERVAL == 0:
                progress_callback(f"Embedding files ({idx + 1}/{total_files})")
        
        # Generate all embeddings at once
        if all_documents:
            logger.info(f"Generating embeddings for {len(all_documents)} chunks...")
            try:
                all_embeddings = self.embeddings.embed_documents(all_documents)
                
                # Add everything to collection in one batch
                logger.info(f"Adding {len(all_documents)} chunks to collection...")
                collection.add(
                    embeddings=all_embeddings,
                    documents=all_documents,
                    metadatas=all_metadatas,
                    ids=all_ids
                )
            except Exception as e:
                logger.error(f"Failed to create embeddings: {e}")
                raise
        
        # Verify the data was actually added
        final_count = collection.count()
        logger.info(f"Created {chunk_id} embeddings in collection {collection_name}")
        logger.info(f"Collection now contains {final_count} items (verification)")
        
        if final_count == 0:
            logger.error(f"WARNING: Collection {collection_name} is empty after adding {chunk_id} chunks!")
        
        return collection_name
    
    def _extract_chunk_functions(self, chunk: str, extension: str) -> List[str]:
        """Extract function names that appear in this specific chunk"""
        functions = []
        try:
            if extension == '.py':
                # Look for function definitions in this chunk
                matches = re.finditer(r'def\s+(\w+)\s*\(', chunk, re.MULTILINE)
                functions = [match.group(1) for match in matches]
            elif extension in ['.js', '.jsx', '.ts', '.tsx']:
                patterns = [
                    r'function\s+(\w+)\s*\(',
                    r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>',
                    r'(\w+)\s*:\s*function\s*\('
                ]
                for pattern in patterns:
                    matches = re.finditer(pattern, chunk, re.MULTILINE)
                    functions.extend([match.group(1) for match in matches])
            elif extension == '.java':
                matches = re.finditer(
                    r'(?:public|private|protected|static|\s)*\s+\w+\s+(\w+)\s*\([^)]*\)\s*\{',
                    chunk, re.MULTILINE
                )
                functions = [match.group(1) for match in matches]
        except Exception as e:
            logger.warning(f"Error extracting chunk functions: {e}")
        
        return functions
    
    def _extract_chunk_classes(self, chunk: str, extension: str) -> List[str]:
        """Extract class names that appear in this specific chunk"""
        classes = []
        try:
            if extension == '.py':
                matches = re.finditer(r'class\s+(\w+)', chunk, re.MULTILINE)
                classes = [match.group(1) for match in matches]
            elif extension in ['.js', '.jsx', '.ts', '.tsx']:
                matches = re.finditer(r'class\s+(\w+)', chunk, re.MULTILINE)
                classes = [match.group(1) for match in matches]
            elif extension == '.java':
                matches = re.finditer(
                    r'(?:public|private|protected|\s)*\s*class\s+(\w+)',
                    chunk, re.MULTILINE
                )
                classes = [match.group(1) for match in matches]
        except Exception as e:
            logger.warning(f"Error extracting chunk classes: {e}")
        
        return classes
    
    def _extract_chunk_imports(self, chunk: str, extension: str) -> List[str]:
        """Extract import statements that appear in this specific chunk"""
        imports = []
        try:
            if extension == '.py':
                # Python imports
                import_matches = re.finditer(r'(?:from\s+(\S+)\s+)?import\s+([^\n]+)', chunk, re.MULTILINE)
                for match in import_matches:
                    if match.group(1):  # from ... import
                        imports.append(f"{match.group(1)}.{match.group(2).split(',')[0].strip()}")
                    else:  # import
                        imports.append(match.group(2).split(',')[0].strip())
            elif extension in ['.js', '.jsx', '.ts', '.tsx']:
                patterns = [
                    r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]',
                    r'import\s+[\'"]([^\'"]+)[\'"]',
                    r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
                ]
                for pattern in patterns:
                    matches = re.finditer(pattern, chunk, re.MULTILINE)
                    imports.extend([match.group(1) for match in matches])
            elif extension == '.java':
                matches = re.finditer(r'import\s+([^;]+);', chunk, re.MULTILINE)
                imports = [match.group(1).strip() for match in matches]
        except Exception as e:
            logger.warning(f"Error extracting chunk imports: {e}")
        
        return imports
    
    def query_similar_code(
        self,
        collection_name: str,
        query: str,
        top_k: int = None
    ) -> List[Dict]:
        """
        Query for similar code snippets
        
        Args:
            collection_name: ChromaDB collection name
            query: Query string
            top_k: Number of results to return
            
        Returns:
            List of similar code snippets with metadata
        """
        if top_k is None:
            top_k = settings.TOP_K_RESULTS
        
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Query collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results and results["documents"]:
                for idx in range(len(results["documents"][0])):
                    formatted_results.append({
                        "content": results["documents"][0][idx],
                        "metadata": results["metadatas"][0][idx],
                        "distance": results["distances"][0][idx] if "distances" in results else None
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to query collection {collection_name}: {e}")
            return []
    
    def query_code_by_function(
        self,
        collection_name: str,
        function_name: str,
        top_k: int = None
    ) -> List[Dict]:
        """
        Query for code chunks containing specific function names
        
        Args:
            collection_name: ChromaDB collection name
            function_name: Function name to search for
            top_k: Number of results to return
            
        Returns:
            List of code chunks containing the function
        """
        if top_k is None:
            top_k = settings.TOP_K_RESULTS
        
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            
            # Get all documents and filter in Python (ChromaDB string contains doesn't work as expected)
            all_results = collection.get(
                limit=top_k * 10,  # Get more results to filter
                include=["documents", "metadatas"]
            )
            
            # Filter results that contain the function name
            filtered_docs = []
            filtered_metas = []
            
            if all_results and all_results["documents"]:
                for idx, metadata in enumerate(all_results["metadatas"]):
                    chunk_funcs = metadata.get("chunk_functions", "")
                    all_funcs = metadata.get("all_functions", "")
                    
                    # Check if function name appears in comma-separated strings
                    if function_name in chunk_funcs.split(",") or function_name in all_funcs.split(","):
                        filtered_docs.append(all_results["documents"][idx])
                        filtered_metas.append(metadata)
                        if len(filtered_docs) >= top_k:
                            break
            
            results = {"documents": filtered_docs, "metadatas": filtered_metas}
            
            # Format results
            formatted_results = []
            for idx in range(len(results["documents"])):
                formatted_results.append({
                    "content": results["documents"][idx],
                    "metadata": results["metadatas"][idx],
                    "distance": None  # No distance for metadata-based queries
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to query by function {function_name}: {e}")
            return []
    
    def query_code_by_class(
        self,
        collection_name: str,
        class_name: str,
        top_k: int = None
    ) -> List[Dict]:
        """
        Query for code chunks containing specific class names
        
        Args:
            collection_name: ChromaDB collection name
            class_name: Class name to search for
            top_k: Number of results to return
            
        Returns:
            List of code chunks containing the class
        """
        if top_k is None:
            top_k = settings.TOP_K_RESULTS
        
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            
            # Get all documents and filter in Python
            all_results = collection.get(
                limit=top_k * 10,  # Get more results to filter
                include=["documents", "metadatas"]
            )
            
            # Filter results that contain the class name
            filtered_docs = []
            filtered_metas = []
            
            if all_results and all_results["documents"]:
                for idx, metadata in enumerate(all_results["metadatas"]):
                    chunk_classes = metadata.get("chunk_classes", "")
                    all_classes = metadata.get("all_classes", "")
                    
                    # Check if class name appears in comma-separated strings
                    if class_name in chunk_classes.split(",") or class_name in all_classes.split(","):
                        filtered_docs.append(all_results["documents"][idx])
                        filtered_metas.append(metadata)
                        if len(filtered_docs) >= top_k:
                            break
            
            results = {"documents": filtered_docs, "metadatas": filtered_metas}
            
            # Format results
            formatted_results = []
            for idx in range(len(results["documents"])):
                formatted_results.append({
                    "content": results["documents"][idx],
                    "metadata": results["metadatas"][idx],
                    "distance": None
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to query by class {class_name}: {e}")
            return []
    
    def query_code_by_language(
        self,
        collection_name: str,
        language: str,
        query: str = None,
        top_k: int = None
    ) -> List[Dict]:
        """
        Query for code chunks in a specific programming language
        
        Args:
            collection_name: ChromaDB collection name
            language: File extension (e.g., '.py', '.js')
            query: Optional semantic query within the language
            top_k: Number of results to return
            
        Returns:
            List of code chunks in the specified language
        """
        if top_k is None:
            top_k = settings.TOP_K_RESULTS
        
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            
            if query:
                # Semantic search within language
                query_embedding = self.embeddings.embed_query(query)
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where={"language": language},
                    include=["documents", "metadatas", "distances"]
                )
                
                formatted_results = []
                if results and results["documents"]:
                    for idx in range(len(results["documents"][0])):
                        formatted_results.append({
                            "content": results["documents"][0][idx],
                            "metadata": results["metadatas"][0][idx],
                            "distance": results["distances"][0][idx] if "distances" in results else None
                        })
            else:
                # Just filter by language
                results = collection.get(
                    where={"language": language},
                    limit=top_k,
                    include=["documents", "metadatas"]
                )
                
                formatted_results = []
                if results and results["documents"]:
                    for idx in range(len(results["documents"])):
                        formatted_results.append({
                            "content": results["documents"][idx],
                            "metadata": results["metadatas"][idx],
                            "distance": None
                        })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to query by language {language}: {e}")
            return []
    
    def get_collection_stats(self, collection_name: str) -> Dict:
        """
        Get enhanced statistics about a collection including code metadata
        
        Args:
            collection_name: Collection name
            
        Returns:
            Dictionary with comprehensive collection statistics
        """
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            count = collection.count()
            
            # Get sample of metadata to analyze
            sample_data = collection.get(
                limit=min(100, count),  # Sample up to 100 items
                include=["metadatas"]
            )
            
            stats = {
                "name": collection_name,
                "total_chunks": count,
                "metadata": collection.metadata
            }
            
            if sample_data and sample_data["metadatas"]:
                # Analyze languages
                languages = {}
                total_functions = 0
                total_classes = 0
                total_complexity = 0
                files_analyzed = set()
                
                for metadata in sample_data["metadatas"]:
                    lang = metadata.get("language", "unknown")
                    languages[lang] = languages.get(lang, 0) + 1
                    
                    # Count file-level stats only once per file
                    file_path = metadata.get("file_path")
                    if file_path and file_path not in files_analyzed:
                        files_analyzed.add(file_path)
                        total_functions += metadata.get("file_functions_count", 0)
                        total_classes += metadata.get("file_classes_count", 0)
                        total_complexity += metadata.get("file_complexity_score", 0)
                
                stats.update({
                    "languages": languages,
                    "unique_files_sampled": len(files_analyzed),
                    "total_functions_sampled": total_functions,
                    "total_classes_sampled": total_classes,
                    "avg_complexity_sampled": total_complexity / len(files_analyzed) if files_analyzed else 0
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}
    
    def delete_collection(self, collection_name: str):
        """
        Delete a ChromaDB collection
        
        Args:
            collection_name: Collection to delete
        """
        try:
            self.chroma_client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
    
    def get_representative_samples(self, collection_name: str, max_samples: int = 25) -> List[Dict]:
        """
        Get diverse, representative code samples using intelligent sampling strategy
        
        Prioritizes:
        - Important files (main, index, app, config files)
        - Diverse file paths (different directories)
        - Variety across languages
        - Meaningful chunks (first chunk per file preferred)
        
        Args:
            collection_name: Collection name
            max_samples: Maximum number of samples to return
            
        Returns:
            List of representative code samples
        """
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            
            # Get total count first
            total_count = collection.count()
            logger.info(f"Collection {collection_name} has {total_count} total chunks")
            
            if total_count == 0:
                logger.warning(f"Collection {collection_name} is empty!")
                return []
            
            # Get all data with explicit limit (ChromaDB defaults to small limit)
            all_data = collection.get(
                limit=total_count,  # Get ALL items, not just default 10
                include=["documents", "metadatas"]
            )
            
            if not all_data or not all_data["documents"]:
                logger.warning(f"Failed to retrieve documents from collection {collection_name}")
                return []
            
            logger.info(f"Retrieved {len(all_data['documents'])} documents from collection")
            
            # Organize by file path and chunk index
            file_chunks = {}
            for idx, metadata in enumerate(all_data["metadatas"]):
                file_path = metadata.get("file_path", "unknown")
                chunk_index = metadata.get("chunk_index", 0)
                
                if file_path not in file_chunks:
                    file_chunks[file_path] = []
                
                file_chunks[file_path].append({
                    "content": all_data["documents"][idx],
                    "metadata": metadata,
                    "chunk_index": chunk_index
                })
            
            # Define important file patterns (prioritize these)
            important_patterns = [
                'main', 'index', 'app', 'server', 'client',
                'config', 'setup', 'init', 'routes', 'api',
                'controller', 'service', 'model', 'handler'
            ]
            
            # Score and sort files by importance
            scored_files = []
            for file_path, chunks in file_chunks.items():
                score = 0
                file_lower = file_path.lower()
                
                # Prioritize important file names
                for pattern in important_patterns:
                    if pattern in file_lower:
                        score += 10
                
                # Prioritize root-level files
                if file_path.count('/') <= 1 and file_path.count('\\') <= 1:
                    score += 5
                
                # Prioritize source directories
                if any(src in file_lower for src in ['src/', 'lib/', 'app/', 'server/', 'client/']):
                    score += 3
                
                scored_files.append((score, file_path, chunks))
            
            # Sort by score (highest first)
            scored_files.sort(key=lambda x: x[0], reverse=True)
            
            # Collect diverse samples
            samples = []
            seen_directories = set()
            
            for score, file_path, chunks in scored_files:
                if len(samples) >= max_samples:
                    break
                
                # Get directory for diversity
                directory = str(Path(file_path).parent)
                
                # Prioritize first chunk (usually has imports, class/function definitions)
                chunks_sorted = sorted(chunks, key=lambda x: x["chunk_index"])
                
                # Take first chunk from this file
                if chunks_sorted:
                    sample = chunks_sorted[0]
                    samples.append(sample)
                    seen_directories.add(directory)
                    
                    # If this is an important file, also include second chunk for more context
                    if score >= 10 and len(chunks_sorted) > 1 and len(samples) < max_samples:
                        samples.append(chunks_sorted[1])
            
            # If we still have room, add more diverse samples from different directories
            if len(samples) < max_samples:
                for score, file_path, chunks in scored_files:
                    if len(samples) >= max_samples:
                        break
                    
                    directory = str(Path(file_path).parent)
                    
                    # Skip if we already have samples from this directory
                    if directory in seen_directories:
                        continue
                    
                    # Add middle chunk for variety
                    if len(chunks) > 2:
                        mid_chunk = chunks[len(chunks) // 2]
                        samples.append(mid_chunk)
                        seen_directories.add(directory)
            
            logger.info(f"Selected {len(samples)} diverse samples from {len(file_chunks)} files")
            
            # Log sample details for debugging
            if samples:
                sample_files = [s.get('metadata', {}).get('file_path', 'unknown') for s in samples[:10]]
                logger.info(f"Sample files (first 10): {sample_files}")
            
            return samples
            
        except Exception as e:
            logger.error(f"Failed to get representative samples: {e}")
            return []
