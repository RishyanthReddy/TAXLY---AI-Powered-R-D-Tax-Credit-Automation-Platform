"""
Example usage of the configuration management system.

This demonstrates how to use the Config module throughout the application.
"""

from utils.config import get_config, ConfigurationError

def main():
    """Demonstrate configuration usage."""
    
    try:
        # Get configuration (singleton pattern - same instance everywhere)
        config = get_config()
        
        print("Configuration loaded successfully!")
        print("\n" + "="*60)
        print("Application Configuration")
        print("="*60)
        
        # Access application settings
        print(f"\nApplication Settings:")
        print(f"  Log Level: {config.log_level}")
        print(f"  Max Retries: {config.max_retries}")
        print(f"  Timeout: {config.timeout_seconds} seconds")
        
        # Access RAG configuration
        print(f"\nRAG Configuration:")
        print(f"  Chunk Size: {config.chunk_size} tokens")
        print(f"  Chunk Overlap: {config.chunk_overlap} tokens")
        print(f"  Top K Results: {config.top_k_results}")
        
        # Access confidence thresholds
        print(f"\nConfidence Thresholds:")
        print(f"  Low: {config.confidence_threshold_low}")
        print(f"  Medium: {config.confidence_threshold_medium}")
        print(f"  High: {config.confidence_threshold_high}")
        
        # Access paths
        print(f"\nPaths:")
        print(f"  Knowledge Base: {config.knowledge_base_path}")
        print(f"  Logs: {config.log_dir}")
        print(f"  Outputs: {config.output_dir}")
        
        # Example: Using config in API connector
        print(f"\n" + "="*60)
        print("Example: Using Config in API Connector")
        print("="*60)
        print(f"""
class ClockifyConnector:
    def __init__(self):
        config = get_config()
        self.api_key = config.clockify_api_key
        self.workspace_id = config.clockify_workspace_id
        self.timeout = config.timeout_seconds
        self.max_retries = config.max_retries
        
    def fetch_data(self):
        # Use configuration values
        pass
""")
        
        # Example: Using config in RAG tool
        print(f"\n" + "="*60)
        print("Example: Using Config in RAG Tool")
        print("="*60)
        print(f"""
class RD_Knowledge_Tool:
    def __init__(self):
        config = get_config()
        self.kb_path = config.knowledge_base_path
        self.chunk_size = config.chunk_size
        self.chunk_overlap = config.chunk_overlap
        self.top_k = config.top_k_results
        
    def query(self, question: str):
        # Use configuration values
        pass
""")
        
    except ConfigurationError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease check your .env file and ensure all required values are set.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
