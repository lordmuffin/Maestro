"""Local-first RAG system for Obsidian vault using LlamaIndex."""
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)


class ObsidianRAG:
    """
    Privacy-preserving RAG system for local Obsidian vault.
    
    This system:
    1. Parses Obsidian vault preserving graph context (wikilinks, backlinks, tags)
    2. Creates vector embeddings using local Ollama
    3. Performs semantic search without data leaving local machine
    4. Generates responses using local LLM
    
    Note: This is a Phase 1 implementation. Full LlamaIndex integration 
    will be added when dependencies are properly installed.
    """
    
    def __init__(
        self,
        vault_path: str = None,
        storage_path: str = "./storage/obsidian_index",
        ollama_host: str = None,
        model_name: str = None
    ):
        """
        Initialize Obsidian RAG system.
        
        Args:
            vault_path: Path to Obsidian vault
            storage_path: Path to store vector index
            ollama_host: Ollama server URL
            model_name: LLM model name
        """
        from core.config import settings
        
        self.vault_path = Path(vault_path or settings.obsidian_vault_path)
        self.storage_path = Path(storage_path)
        self.ollama_host = ollama_host or settings.ollama_host
        self.model_name = model_name or settings.ollama_model
        
        # Index storage
        self.index = None
        self.documents = []
        
        logger.info(f"Initialized ObsidianRAG with vault: {self.vault_path}")
    
    def _setup_llm(self) -> None:
        """Configure LlamaIndex with Ollama models."""
        # This will be implemented when LlamaIndex is properly set up
        logger.info(f"Setting up LLM with model: {self.model_name}")
        pass
    
    def load_vault(self, force_reload: bool = False) -> None:
        """
        Load and index Obsidian vault.
        
        Args:
            force_reload: Force re-indexing even if index exists
        """
        logger.info(f"Loading vault from: {self.vault_path}")
        
        # Check if vault path exists
        if not self.vault_path.exists():
            logger.warning(f"Vault path does not exist: {self.vault_path}")
            logger.info("Creating empty vault directory")
            self.vault_path.mkdir(parents=True, exist_ok=True)
            return
        
        # Scan markdown files
        md_files = list(self.vault_path.rglob("*.md"))
        logger.info(f"Found {len(md_files)} markdown files in vault")
        
        # Load file contents
        self.documents = []
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.documents.append({
                        'path': str(md_file.relative_to(self.vault_path)),
                        'content': content,
                        'file_name': md_file.name
                    })
            except Exception as e:
                logger.error(f"Failed to read {md_file}: {e}")
        
        logger.info(f"Loaded {len(self.documents)} documents")
    
    def query(
        self,
        query_text: str,
        similarity_top_k: int = 5,
        response_mode: str = "compact"
    ) -> Dict[str, Any]:
        """
        Query the vault using semantic search.
        
        Args:
            query_text: User query
            similarity_top_k: Number of similar chunks to retrieve
            response_mode: Response synthesis mode
            
        Returns:
            Dictionary with response and source nodes
        """
        logger.info(f"Processing query: {query_text}")
        
        if not self.documents:
            return {
                "response": "No documents loaded. Please load vault first.",
                "sources": [],
                "query": query_text
            }
        
        # Simple keyword search for Phase 1
        # Full semantic search will be implemented with LlamaIndex
        results = []
        query_lower = query_text.lower()
        
        for doc in self.documents:
            content_lower = doc['content'].lower()
            if any(word in content_lower for word in query_lower.split()):
                # Calculate simple relevance score
                score = sum(1 for word in query_lower.split() if word in content_lower)
                results.append({
                    'document': doc,
                    'score': score
                })
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        top_results = results[:similarity_top_k]
        
        # Format sources
        sources = []
        for result in top_results:
            doc = result['document']
            # Get snippet
            content = doc['content']
            snippet = content[:200] + "..." if len(content) > 200 else content
            
            sources.append({
                "text": snippet,
                "score": result['score'],
                "metadata": {
                    "file_path": doc['path'],
                    "file_name": doc['file_name']
                },
                "file_path": doc['path']
            })
        
        # Generate simple response
        if sources:
            response = f"Found {len(sources)} relevant documents:\n\n"
            for i, source in enumerate(sources, 1):
                response += f"{i}. {source['metadata']['file_name']}\n"
                response += f"   {source['text']}\n\n"
        else:
            response = "No relevant documents found in vault."
        
        return {
            "response": response,
            "sources": sources,
            "query": query_text
        }
    
    def get_graph_context(self, file_path: str) -> Dict[str, Any]:
        """
        Get graph context for a specific file (backlinks, outlinks, tags).
        
        Args:
            file_path: Path to file relative to vault
            
        Returns:
            Dictionary with graph metadata
        """
        logger.info(f"Retrieving graph context for: {file_path}")
        
        full_path = self.vault_path / file_path
        if not full_path.exists():
            return {
                "file_path": file_path,
                "error": "File not found",
                "backlinks": [],
                "outlinks": [],
                "tags": []
            }
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract wikilinks [[...]]
            import re
            outlinks = re.findall(r'\[\[(.*?)\]\]', content)
            
            # Extract tags #...
            tags = re.findall(r'#(\w+)', content)
            
            # Find backlinks (files that link to this file)
            file_name = Path(file_path).stem
            backlinks = []
            for doc in self.documents:
                if f'[[{file_name}]]' in doc['content']:
                    backlinks.append(doc['file_name'])
            
            return {
                "file_path": file_path,
                "backlinks": backlinks,
                "outlinks": outlinks,
                "tags": tags
            }
        except Exception as e:
            logger.error(f"Failed to get graph context: {e}")
            return {
                "file_path": file_path,
                "error": str(e),
                "backlinks": [],
                "outlinks": [],
                "tags": []
            }
    
    def search_by_tag(self, tag: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search vault by tag.
        
        Args:
            tag: Tag to search for (without #)
            limit: Maximum number of results
            
        Returns:
            List of matching documents
        """
        logger.info(f"Searching for tag: #{tag}")
        
        results = []
        for doc in self.documents:
            if f'#{tag}' in doc['content']:
                results.append({
                    "file_path": doc['path'],
                    "file_name": doc['file_name'],
                    "text": doc['content'][:200] + "..."
                })
                
                if len(results) >= limit:
                    break
        
        return results
