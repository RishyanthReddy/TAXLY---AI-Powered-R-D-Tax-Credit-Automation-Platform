"""Agent modules for R&D Tax Credit Automation."""

from agents.data_ingestion_agent import (
    DataIngestionAgent,
    DataIngestionState,
    DataIngestionResult
)

from agents.qualification_agent import (
    QualificationAgent,
    QualificationState,
    QualificationResult
)

from agents.audit_trail_agent import (
    AuditTrailAgent,
    AuditTrailState,
    AuditTrailResult
)

__all__ = [
    'DataIngestionAgent',
    'DataIngestionState',
    'DataIngestionResult',
    'QualificationAgent',
    'QualificationState',
    'QualificationResult',
    'AuditTrailAgent',
    'AuditTrailState',
    'AuditTrailResult'
]
