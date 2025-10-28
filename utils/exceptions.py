"""
Custom exception hierarchy for the R&D Tax Credit Automation Agent.

This module defines all custom exceptions used throughout the application,
providing clear error categorization and informative error messages for
debugging and user feedback.
"""


class RDTaxAgentError(Exception):
    """
    Base exception class for all R&D Tax Agent errors.
    
    All custom exceptions in the application inherit from this base class,
    allowing for easy catching of all agent-related errors.
    """
    
    def __init__(self, message: str, details: dict = None):
        """
        Initialize the base exception.
        
        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self):
        """Return string representation of the exception."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class APIConnectionError(RDTaxAgentError):
    """
    Exception raised when external API connections fail.
    
    This exception is used for all external API communication failures,
    including connection timeouts, authentication failures, rate limiting,
    and server errors from services like Clockify, Unified.to, OpenRouter,
    You.com, and Playwright MCP.
    
    Attributes:
        api_name: Name of the API that failed (e.g., 'Clockify', 'OpenRouter')
        status_code: HTTP status code if applicable
        endpoint: API endpoint that was called
        retry_count: Number of retry attempts made
    """
    
    def __init__(
        self,
        message: str,
        api_name: str = None,
        status_code: int = None,
        endpoint: str = None,
        retry_count: int = 0,
        details: dict = None
    ):
        """
        Initialize API connection error.
        
        Args:
            message: Human-readable error message
            api_name: Name of the API service
            status_code: HTTP status code from the failed request
            endpoint: API endpoint that was called
            retry_count: Number of retry attempts made
            details: Additional error context
        """
        error_details = details or {}
        error_details.update({
            'api_name': api_name,
            'status_code': status_code,
            'endpoint': endpoint,
            'retry_count': retry_count
        })
        super().__init__(message, error_details)
        self.api_name = api_name
        self.status_code = status_code
        self.endpoint = endpoint
        self.retry_count = retry_count


class ValidationError(RDTaxAgentError):
    """
    Exception raised when data validation fails.
    
    This exception is used when Pydantic model validation fails, input data
    is malformed, or business logic validation rules are violated.
    
    Attributes:
        field_name: Name of the field that failed validation
        invalid_value: The value that failed validation
        validation_rule: Description of the validation rule that was violated
    """
    
    def __init__(
        self,
        message: str,
        field_name: str = None,
        invalid_value: any = None,
        validation_rule: str = None,
        details: dict = None
    ):
        """
        Initialize validation error.
        
        Args:
            message: Human-readable error message
            field_name: Name of the field that failed validation
            invalid_value: The value that failed validation
            validation_rule: Description of the validation rule
            details: Additional error context
        """
        error_details = details or {}
        error_details.update({
            'field_name': field_name,
            'invalid_value': str(invalid_value) if invalid_value is not None else None,
            'validation_rule': validation_rule
        })
        super().__init__(message, error_details)
        self.field_name = field_name
        self.invalid_value = invalid_value
        self.validation_rule = validation_rule


class RAGRetrievalError(RDTaxAgentError):
    """
    Exception raised when RAG knowledge base retrieval fails.
    
    This exception is used when the RAG system encounters errors during
    document indexing, embedding generation, vector database queries,
    or when no relevant documents are found.
    
    Attributes:
        query: The query that failed to retrieve results
        knowledge_base_path: Path to the knowledge base directory
        error_type: Type of RAG error (e.g., 'indexing', 'query', 'embedding')
    """
    
    def __init__(
        self,
        message: str,
        query: str = None,
        knowledge_base_path: str = None,
        error_type: str = None,
        details: dict = None
    ):
        """
        Initialize RAG retrieval error.
        
        Args:
            message: Human-readable error message
            query: The query that failed
            knowledge_base_path: Path to the knowledge base
            error_type: Type of RAG error
            details: Additional error context
        """
        error_details = details or {}
        error_details.update({
            'query': query,
            'knowledge_base_path': knowledge_base_path,
            'error_type': error_type
        })
        super().__init__(message, error_details)
        self.query = query
        self.knowledge_base_path = knowledge_base_path
        self.error_type = error_type


class AgentExecutionError(RDTaxAgentError):
    """
    Exception raised when agent runtime execution fails.
    
    This exception is used when PydanticAI agents encounter errors during
    execution, including tool invocation failures, state management issues,
    workflow orchestration problems, or unexpected runtime errors.
    
    Attributes:
        agent_name: Name of the agent that failed (e.g., 'DataIngestionAgent')
        stage: Current execution stage when error occurred
        tool_name: Name of the tool that failed (if applicable)
        state: Agent state at time of failure
    """
    
    def __init__(
        self,
        message: str,
        agent_name: str = None,
        stage: str = None,
        tool_name: str = None,
        state: dict = None,
        details: dict = None
    ):
        """
        Initialize agent execution error.
        
        Args:
            message: Human-readable error message
            agent_name: Name of the agent that failed
            stage: Current execution stage
            tool_name: Name of the tool that failed
            state: Agent state at time of failure
            details: Additional error context
        """
        error_details = details or {}
        error_details.update({
            'agent_name': agent_name,
            'stage': stage,
            'tool_name': tool_name,
            'state': state
        })
        super().__init__(message, error_details)
        self.agent_name = agent_name
        self.stage = stage
        self.tool_name = tool_name
        self.state = state
