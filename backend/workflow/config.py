import os
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)
class WorkflowConfig:
    """Centralized configuration for the workflow"""
    
    # API Keys (loaded from .env file)
    LLAMA_PARSE_API_KEY = os.getenv("LLAMA_PARSE_API_KEY", "")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
    QDRANT_CLUSTER_ENDPOINT = os.getenv("QDRANT_CLUSTER_ENDPOINT", "")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    api_key = os.getenv("AZURE_API_KEY", "")
    azure_endpoint = os.getenv("AZURE_ENDPOINT", "")
    embed_azure_endpoint = os.getenv("AZURE_EMBED_ENDPOINT", "")
    embed_api_key = os.getenv("AZURE_EMBED_API_KEY", "")
    # Model configurations
    LLM_MODEL = "gpt-4.1"  # Using more cost-effective model
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSION = 1536

    # LLM_MODEL="gemini-2.5-flash"
    # EMBEDDING_MODEL = "text-embedding-004"
    # EMBEDDING_DIMENSION = 768
    
    # Vector store settings
    # PINECONE_INDEX_NAME = "resume-application-matcher"
    # PINECONE_CLOUD = "aws"
    # PINECONE_REGION = "us-east-1"
    QDRANT_INDEX_NAME = "resume-application-matcher"

    
    # Processing parameters
    CHUNK_SIZE = 20
    CHUNK_OVERLAP = 0
    SIMILARITY_TOP_K = 3
    LLM_TEMPERATURE = 0.0
    TIMEOUT = None
    MAX_RETRIES = 3
    MIN_CONFIDENCE_THRESHOLD = 0.5

class EnhancedWorkflowConfig:
    """Enhanced configuration with profile support"""
    
    def __init__(self, **kwargs):
        """Initialize configuration with optional parameters"""
        self.load_configuration(**kwargs)
    
    def load_configuration(self, **kwargs):
        """Load configuration from environment, defaults, and provided parameters"""
        default_config = self._get_default_config()
        
        # Set attributes from default config
        for key, value in default_config.items():
            setattr(self, key, value)
        
        # Override with any provided parameters
        for key, value in kwargs.items():
            if value is not None:
                setattr(self, key, value)
        
        # Auto-detect and set embedding dimension based on embedding model
        self._set_embedding_dimension()
        
        logger.info(f"✅ Configuration loaded successfully with model: {self.LLM_MODEL}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Default configuration settings"""
        return {
            "GOOGLE_API_KEY": self._get_env_var("GOOGLE_API_KEY", WorkflowConfig.GOOGLE_API_KEY),
            "api_key": self._get_env_var("AZURE_API_KEY", WorkflowConfig.api_key),
            "azure_endpoint": self._get_env_var("AZURE_ENDPOINT", WorkflowConfig.azure_endpoint),
            "embed_azure_endpoint": self._get_env_var("AZURE_EMBED_ENDPOINT", WorkflowConfig.embed_azure_endpoint),
            "embed_api_key": self._get_env_var("AZURE_EMBED_API_KEY", WorkflowConfig.embed_api_key),
            "LLAMA_PARSE_API_KEY": self._get_env_var("LLAMA_PARSE_API_KEY", WorkflowConfig.LLAMA_PARSE_API_KEY),
            # "PINECONE_API_KEY": self._get_env_var("PINECONE_API_KEY", WorkflowConfig.PINECONE_API_KEY),
            "QDRANT_API_KEY": self._get_env_var("QDRANT_API_KEY", WorkflowConfig.QDRANT_API_KEY),
            "QDRANT_CLUSTER_ENDPOINT": self._get_env_var("QDRANT_CLUSTER_ENDPOINT", WorkflowConfig.QDRANT_CLUSTER_ENDPOINT),
            "LLM_MODEL": "o4-mini",
            "EMBEDDING_MODEL": "text-embedding-3-small",
            "EMBEDDING_DIMENSION": 1536,
            # "PINECONE_INDEX_NAME": "resume-application-matcher",
            "QDRANT_INDEX_NAME": "resume-application-matcher",
            # "PINECONE_CLOUD": "aws",
            # "PINECONE_REGION": "us-east-1",
            "CHUNK_SIZE": 20,
            "CHUNK_OVERLAP": 0,
            "SIMILARITY_TOP_K": 3,
            "LLM_TEMPERATURE": 0.0,
            "MAX_RETRIES": 3,
            "TIMEOUT": None,
            "MIN_CONFIDENCE_THRESHOLD": 0.6
        }
    
    def _get_env_var(self, var_name: str, default: str = None) -> Optional[str]:
        """Safely get environment variable"""
        return os.getenv(var_name, default)
    
    def _set_embedding_dimension(self):
        """Auto-detect and set embedding dimension based on embedding model"""
        embedding_model = getattr(self, 'EMBEDDING_MODEL', '')
        
        # OpenAI embedding dimensions
        if 'text-embedding-3-large' in embedding_model:
            self.EMBEDDING_DIMENSION = 3072
        elif 'text-embedding-3-small' in embedding_model:
            self.EMBEDDING_DIMENSION = 1536
        elif 'text-embedding-ada' in embedding_model:
            self.EMBEDDING_DIMENSION = 1536
        # Google embedding dimensions
        elif 'text-embedding-004' in embedding_model or 'text-embedding-005' in embedding_model:
            self.EMBEDDING_DIMENSION = 768
        # Default fallback
        else:
            self.EMBEDDING_DIMENSION = 1536
        
        logger.info(f"Embedding dimension set to {self.EMBEDDING_DIMENSION} for model {embedding_model}")
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return any issues"""
        issues = []
        
        required_keys = ["LLAMA_PARSE_API_KEY", "QDRANT_API_KEY"]
        for key in required_keys:
            if not getattr(self, key, None):
                issues.append(f"Missing required configuration: {key}")
        
        if hasattr(self, 'LLM_TEMPERATURE'):
            if not (0 <= self.LLM_TEMPERATURE <= 1):
                issues.append("LLM_TEMPERATURE must be between 0 and 1")
        
        if hasattr(self, 'CHUNK_SIZE'):
            if self.CHUNK_SIZE < 0:
                issues.append("CHUNK_SIZE must be greater than 0")
        
        return issues

# ================================================================================
# MONITORING CLASSES

