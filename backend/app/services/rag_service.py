from typing import List, Dict
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings
from app.utils.logger import logger


class RAGService:
    """Service for RAG operations using ChromaDB"""
    
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
        
        # Text splitter with 15% overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        logger.info("RAGService initialized with ChromaDB")
    
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
        Create embeddings for repository files
        
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
            
            # Split content into chunks
            chunks = self.text_splitter.split_text(content)
            
            # Prepare documents for this file
            for chunk_idx, chunk in enumerate(chunks):
                all_documents.append(chunk)
                all_metadatas.append({
                    "file_path": file_path,
                    "chunk_index": chunk_idx,
                    "language": extension,
                    "total_chunks": len(chunks)
                })
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
    
    def get_collection_stats(self, collection_name: str) -> Dict:
        """
        Get statistics about a collection
        
        Args:
            collection_name: Collection name
            
        Returns:
            Dictionary with collection statistics
        """
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            count = collection.count()
            
            return {
                "name": collection_name,
                "total_chunks": count,
                "metadata": collection.metadata
            }
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
