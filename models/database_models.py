"""
Database Models

This module defines SQLAlchemy ORM models for persistence layer.
These models support:
- Workflow state persistence (resume capability)
- Audit logging for compliance tracking
- Session management

Requirements: 8.5
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import json

# Create declarative base for all models
Base = declarative_base()


class WorkflowStage(str, Enum):
    """Enumeration of workflow stages"""
    DATA_INGESTION = "data_ingestion"
    QUALIFICATION = "qualification"
    AUDIT_TRAIL = "audit_trail"
    COMPLETED = "completed"


class WorkflowStatus(str, Enum):
    """Enumeration of workflow execution statuses"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    PAUSED = "paused"


class SessionState(Base):
    """
    Model for workflow state persistence.
    
    Stores the current state of a user's R&D tax credit workflow session,
    enabling resume capability if the process is interrupted.
    
    Requirements: 8.5
    
    Attributes:
        session_id: Unique identifier for the workflow session
        user_id: Identifier for the user/client
        tax_year: Tax year for the R&D credit claim
        current_stage: Current workflow stage (data_ingestion, qualification, audit_trail)
        status: Current execution status
        created_at: Session creation timestamp
        updated_at: Last update timestamp
        data_ingestion_completed: Whether data ingestion stage is complete
        qualification_completed: Whether qualification stage is complete
        audit_trail_completed: Whether audit trail generation is complete
        ingested_data_count: Number of records ingested
        qualified_projects_count: Number of projects qualified
        report_id: Generated report identifier (if completed)
        state_data: JSON field for storing intermediate results
        error_message: Last error message (if status is ERROR)
    
    Example:
        session = SessionState(
            session_id="sess_123abc",
            user_id="user_456",
            tax_year=2024,
            current_stage=WorkflowStage.QUALIFICATION,
            status=WorkflowStatus.IN_PROGRESS
        )
    """
    __tablename__ = 'session_states'
    
    # Primary key
    session_id = Column(String(255), primary_key=True, index=True)
    
    # User and context information
    user_id = Column(String(255), nullable=False, index=True)
    tax_year = Column(Integer, nullable=False)
    
    # Workflow tracking
    current_stage = Column(SQLEnum(WorkflowStage), nullable=False, default=WorkflowStage.DATA_INGESTION)
    status = Column(SQLEnum(WorkflowStatus), nullable=False, default=WorkflowStatus.PENDING)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Stage completion flags
    data_ingestion_completed = Column(Boolean, default=False, nullable=False)
    qualification_completed = Column(Boolean, default=False, nullable=False)
    audit_trail_completed = Column(Boolean, default=False, nullable=False)
    
    # Progress metrics
    ingested_data_count = Column(Integer, default=0, nullable=False)
    qualified_projects_count = Column(Integer, default=0, nullable=False)
    report_id = Column(String(255), nullable=True, index=True)
    
    # State persistence (JSON field for flexibility)
    state_data = Column(JSON, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return (
            f"<SessionState(session_id='{self.session_id}', "
            f"user_id='{self.user_id}', "
            f"tax_year={self.tax_year}, "
            f"current_stage='{self.current_stage.value}', "
            f"status='{self.status.value}')>"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary for JSON serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the session state
        """
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'tax_year': self.tax_year,
            'current_stage': self.current_stage.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'data_ingestion_completed': self.data_ingestion_completed,
            'qualification_completed': self.qualification_completed,
            'audit_trail_completed': self.audit_trail_completed,
            'ingested_data_count': self.ingested_data_count,
            'qualified_projects_count': self.qualified_projects_count,
            'report_id': self.report_id,
            'state_data': self.state_data,
            'error_message': self.error_message
        }
    
    def update_stage(self, stage: WorkflowStage, status: WorkflowStatus = WorkflowStatus.IN_PROGRESS):
        """
        Update the current workflow stage and status.
        
        Args:
            stage: New workflow stage
            status: New workflow status (default: IN_PROGRESS)
        """
        self.current_stage = stage
        self.status = status
        self.updated_at = datetime.now()
    
    def mark_stage_completed(self, stage: WorkflowStage):
        """
        Mark a specific stage as completed.
        
        Args:
            stage: Stage to mark as completed
        """
        if stage == WorkflowStage.DATA_INGESTION:
            self.data_ingestion_completed = True
        elif stage == WorkflowStage.QUALIFICATION:
            self.qualification_completed = True
        elif stage == WorkflowStage.AUDIT_TRAIL:
            self.audit_trail_completed = True
        
        self.updated_at = datetime.now()
    
    def set_error(self, error_message: str):
        """
        Set error status and message.
        
        Args:
            error_message: Error description
        """
        self.status = WorkflowStatus.ERROR
        self.error_message = error_message
        self.updated_at = datetime.now()
    
    def is_resumable(self) -> bool:
        """
        Check if the session can be resumed.
        
        Returns:
            bool: True if session is in a resumable state
        """
        return self.status in [WorkflowStatus.PAUSED, WorkflowStatus.ERROR, WorkflowStatus.IN_PROGRESS]


class AuditLogAction(str, Enum):
    """Enumeration of audit log action types"""
    SESSION_CREATED = "session_created"
    DATA_INGESTION_STARTED = "data_ingestion_started"
    DATA_INGESTION_COMPLETED = "data_ingestion_completed"
    QUALIFICATION_STARTED = "qualification_started"
    QUALIFICATION_COMPLETED = "qualification_completed"
    AUDIT_TRAIL_STARTED = "audit_trail_started"
    AUDIT_TRAIL_COMPLETED = "audit_trail_completed"
    REPORT_GENERATED = "report_generated"
    REPORT_DOWNLOADED = "report_downloaded"
    USER_CLASSIFICATION = "user_classification"
    ERROR_OCCURRED = "error_occurred"
    API_CALL = "api_call"
    RAG_QUERY = "rag_query"
    LLM_INFERENCE = "llm_inference"


class AuditLog(Base):
    """
    Model for compliance audit logging.
    
    Maintains an immutable record of all system actions, user decisions,
    and data transformations for IRS audit defense and compliance tracking.
    
    Requirements: 8.5
    
    Attributes:
        log_id: Unique identifier for the log entry
        session_id: Associated workflow session
        user_id: User who performed the action
        action: Type of action performed
        timestamp: When the action occurred
        stage: Workflow stage when action occurred
        details: JSON field with action-specific details
        ip_address: Client IP address (for security tracking)
        user_agent: Client user agent string
        success: Whether the action completed successfully
        error_message: Error details if action failed
    
    Example:
        log = AuditLog(
            session_id="sess_123abc",
            user_id="user_456",
            action=AuditLogAction.QUALIFICATION_COMPLETED,
            stage=WorkflowStage.QUALIFICATION,
            details={"qualified_projects": 15, "total_credit": 125000.00}
        )
    """
    __tablename__ = 'audit_logs'
    
    # Primary key
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Session and user tracking
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Action information
    action = Column(SQLEnum(AuditLogAction), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    stage = Column(SQLEnum(WorkflowStage), nullable=True)
    
    # Action details (flexible JSON storage)
    details = Column(JSON, nullable=True)
    
    # Security tracking
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(String(500), nullable=True)
    
    # Result tracking
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return (
            f"<AuditLog(log_id={self.log_id}, "
            f"session_id='{self.session_id}', "
            f"action='{self.action.value}', "
            f"timestamp='{self.timestamp}', "
            f"success={self.success})>"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary for JSON serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the audit log
        """
        return {
            'log_id': self.log_id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'action': self.action.value,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'stage': self.stage.value if self.stage else None,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'success': self.success,
            'error_message': self.error_message
        }
    
    @staticmethod
    def create_log(
        session_id: str,
        user_id: str,
        action: AuditLogAction,
        stage: Optional[WorkflowStage] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> 'AuditLog':
        """
        Factory method to create an audit log entry.
        
        Args:
            session_id: Workflow session identifier
            user_id: User identifier
            action: Action type
            stage: Current workflow stage
            details: Action-specific details
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether action succeeded
            error_message: Error details if failed
        
        Returns:
            AuditLog: New audit log instance
        """
        return AuditLog(
            session_id=session_id,
            user_id=user_id,
            action=action,
            stage=stage,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )


# Database configuration and session management utilities

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator


class DatabaseConfig:
    """
    Database configuration and connection management.
    
    Provides utilities for creating database engines, sessions,
    and managing database lifecycle.
    
    Requirements: 8.5
    """
    
    def __init__(self, database_url: str = "sqlite:///./rd_tax_agent.db", echo: bool = False):
        """
        Initialize database configuration.
        
        Args:
            database_url: SQLAlchemy database URL
                         Default: SQLite file in current directory
                         Production: Use PostgreSQL or MySQL
            echo: Whether to log SQL statements (useful for debugging)
        
        Examples:
            # SQLite (development)
            config = DatabaseConfig("sqlite:///./rd_tax_agent.db")
            
            # PostgreSQL (production)
            config = DatabaseConfig("postgresql://user:pass@localhost/rd_tax_agent")
            
            # MySQL (production)
            config = DatabaseConfig("mysql+pymysql://user:pass@localhost/rd_tax_agent")
        """
        self.database_url = database_url
        self.echo = echo
        self.engine = create_engine(database_url, echo=echo)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """
        Create all database tables.
        
        Should be called during application initialization.
        """
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """
        Drop all database tables.
        
        WARNING: This will delete all data. Use only for testing or reset.
        """
        Base.metadata.drop_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        
        Automatically handles session lifecycle and rollback on errors.
        
        Yields:
            Session: SQLAlchemy database session
        
        Example:
            with db_config.get_session() as session:
                session_state = SessionState(session_id="test", user_id="user1")
                session.add(session_state)
                session.commit()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """
        Get a database session directly (without context manager).
        
        Caller is responsible for closing the session.
        
        Returns:
            Session: SQLAlchemy database session
        """
        return self.SessionLocal()


# Example usage and helper functions

def initialize_database(database_url: str = "sqlite:///./rd_tax_agent.db") -> DatabaseConfig:
    """
    Initialize database with tables.
    
    Args:
        database_url: SQLAlchemy database URL
    
    Returns:
        DatabaseConfig: Configured database instance
    
    Example:
        db = initialize_database()
        # Database is now ready for use
    """
    config = DatabaseConfig(database_url)
    config.create_tables()
    return config


def create_session_state(
    session: Session,
    session_id: str,
    user_id: str,
    tax_year: int
) -> SessionState:
    """
    Create and persist a new session state.
    
    Args:
        session: Database session
        session_id: Unique session identifier
        user_id: User identifier
        tax_year: Tax year for the claim
    
    Returns:
        SessionState: Created session state
    
    Example:
        with db.get_session() as session:
            state = create_session_state(session, "sess_123", "user_456", 2024)
    """
    session_state = SessionState(
        session_id=session_id,
        user_id=user_id,
        tax_year=tax_year,
        current_stage=WorkflowStage.DATA_INGESTION,
        status=WorkflowStatus.PENDING
    )
    session.add(session_state)
    session.commit()
    session.refresh(session_state)
    return session_state


def log_action(
    session: Session,
    session_id: str,
    user_id: str,
    action: AuditLogAction,
    stage: Optional[WorkflowStage] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> AuditLog:
    """
    Create and persist an audit log entry.
    
    Args:
        session: Database session
        session_id: Workflow session identifier
        user_id: User identifier
        action: Action type
        stage: Current workflow stage
        details: Action-specific details
        success: Whether action succeeded
        error_message: Error details if failed
    
    Returns:
        AuditLog: Created audit log entry
    
    Example:
        with db.get_session() as session:
            log = log_action(
                session,
                "sess_123",
                "user_456",
                AuditLogAction.QUALIFICATION_COMPLETED,
                stage=WorkflowStage.QUALIFICATION,
                details={"qualified_projects": 15}
            )
    """
    audit_log = AuditLog.create_log(
        session_id=session_id,
        user_id=user_id,
        action=action,
        stage=stage,
        details=details,
        success=success,
        error_message=error_message
    )
    session.add(audit_log)
    session.commit()
    session.refresh(audit_log)
    return audit_log
