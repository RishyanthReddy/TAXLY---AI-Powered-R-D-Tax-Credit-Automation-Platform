"""
Audit Trail Agent for R&D Tax Credit Automation.

This agent is responsible for generating comprehensive audit-ready documentation
including R&D project narratives, compliance reviews, and PDF reports.

The agent uses PydanticAI for structured agent workflows, You.com APIs for
narrative generation and compliance review, GLM 4.5 Air via OpenRouter for
agent reasoning, and ReportLab/xhtml2pdf for PDF generation.

Requirements: 4.1, 8.1
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from models.tax_models import QualifiedProject, AuditReport
from models.websocket_models import StatusUpdateMessage, AgentStage, AgentStatus
from utils.logger import get_audit_trail_logger
from utils.exceptions import APIConnectionError

# Get logger for audit trail agent
logger = get_audit_trail_logger()


class AuditTrailState(BaseModel):
    """
    State model for tracking Audit Trail Agent progress.
    
    This model maintains the current state of the audit trail generation workflow,
    including progress tracking, narrative generation, and report status.
    
    Attributes:
        stage: Current stage of audit trail generation (initializing, generating_narratives, etc.)
        status: Current execution status (pending, in_progress, completed, error)
        projects_to_process: Total number of projects to process
        narratives_generated: Number of narratives successfully generated
        narratives_reviewed: Number of narratives reviewed for compliance
        current_project: Name of project currently being processed
        report_generated: Whether PDF report has been generated
        start_time: Timestamp when generation started
        end_time: Timestamp when generation completed (None if in progress)
        error_message: Error message if generation failed
    """
    
    stage: str = Field(
        default="initializing",
        description="Current stage of audit trail generation workflow"
    )
    
    status: AgentStatus = Field(
        default=AgentStatus.PENDING,
        description="Current execution status"
    )
    
    projects_to_process: int = Field(
        default=0,
        description="Total number of projects to process"
    )
    
    narratives_generated: int = Field(
        default=0,
        description="Number of narratives successfully generated"
    )
    
    narratives_reviewed: int = Field(
        default=0,
        description="Number of narratives reviewed for compliance"
    )
    
    current_project: Optional[str] = Field(
        default=None,
        description="Name of project currently being processed"
    )
    
    report_generated: bool = Field(
        default=False,
        description="Whether PDF report has been generated"
    )
    
    start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when generation started"
    )
    
    end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when generation completed"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if generation failed"
    )
    
    def to_status_message(self) -> StatusUpdateMessage:
        """
        Convert current state to a WebSocket status update message.
        
        Returns:
            StatusUpdateMessage for broadcasting to frontend
        """
        details = f"{self.stage}: "
        
        if self.status == AgentStatus.IN_PROGRESS:
            if self.current_project:
                details += f"Processing project '{self.current_project}' ({self.narratives_generated}/{self.projects_to_process})"
            elif self.report_generated:
                details += "Finalizing PDF report"
            else:
                details += f"Generated {self.narratives_generated}/{self.projects_to_process} narratives"
        elif self.status == AgentStatus.COMPLETED:
            details += f"Successfully generated audit report for {self.projects_to_process} projects"
        elif self.status == AgentStatus.ERROR:
            details += f"Error: {self.error_message}"
        else:
            details += "Waiting to start"
        
        return StatusUpdateMessage(
            stage=AgentStage.AUDIT_TRAIL,
            status=self.status,
            details=details,
            timestamp=datetime.now()
        )


class AuditTrailResult(BaseModel):
    """
    Result model for Audit Trail Agent execution.
    
    Contains the generated audit report along with metadata about the
    generation process.
    
    Attributes:
        report: AuditReport object with all report data
        pdf_path: Path to generated PDF file
        narratives: Dictionary mapping project names to generated narratives
        compliance_rev