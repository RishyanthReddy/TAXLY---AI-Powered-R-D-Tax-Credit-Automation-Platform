"""
Tax-related data models for R&D Tax Credit Automation Agent.

This module contains Pydantic models for tax qualification results, audit reports,
and RAG context. These models ensure data validation and type safety for the
qualification and audit trail agents.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, computed_field, model_validator
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class QualifiedProject(BaseModel):
    """
    Represents a project that has been evaluated for R&D tax credit qualification.
    
    This model captures the results of the Qualification Agent's analysis, including
    the qualification percentage, confidence score, IRS citations, and supporting
    reasoning. It is used to track which projects qualify for R&D tax credits and
    to what extent.
    
    Attributes:
        project_name: Name of the project being evaluated
        qualified_hours: Total hours that qualify for R&D tax credit
        qualified_cost: Total cost that qualifies for R&D tax credit (in dollars)
        confidence_score: AI confidence in the qualification decision (0-1 range)
        qualification_percentage: Percentage of project that qualifies as R&D (0-100)
        supporting_citation: IRS document excerpt supporting the qualification
        reasoning: Detailed explanation of why the project qualifies
        irs_source: Reference to specific IRS document and section
        flagged_for_review: Whether this project needs manual review (auto-set for low confidence)
        technical_details: Optional dictionary containing detailed technical information
    
    Example:
        >>> project = QualifiedProject(
        ...     project_name="Alpha Development",
        ...     qualified_hours=14.5,
        ...     qualified_cost=1045.74,
        ...     confidence_score=0.92,
        ...     qualification_percentage=95.0,
        ...     supporting_citation="The project involves developing a new authentication algorithm...",
        ...     reasoning="This project clearly meets the four-part test...",
        ...     irs_source="CFR Title 26 § 1.41-4(a)(1) - Four-Part Test for Qualified Research",
        ...     technical_details={
        ...         "technological_uncertainty": "Uncertainty existed regarding...",
        ...         "experimentation_process": "Team evaluated multiple encryption standards...",
        ...         "business_component": "User Authentication System"
        ...     }
        ... )
        >>> print(project.estimated_credit)
        209.15
        >>> print(project.flagged_for_review)
        False
    """
    
    project_name: str = Field(
        ...,
        description="Name of the project being evaluated",
        min_length=1
    )
    
    qualified_hours: float = Field(
        ...,
        description="Total hours that qualify for R&D tax credit",
        ge=0
    )
    
    qualified_cost: float = Field(
        ...,
        description="Total cost that qualifies for R&D tax credit (in dollars)",
        ge=0
    )
    
    confidence_score: float = Field(
        ...,
        description="AI confidence in the qualification decision (0-1 range)",
        ge=0,
        le=1
    )
    
    qualification_percentage: float = Field(
        ...,
        description="Percentage of project that qualifies as R&D (0-100)",
        ge=0,
        le=100
    )
    
    supporting_citation: str = Field(
        ...,
        description="IRS document excerpt supporting the qualification",
        min_length=1
    )
    
    reasoning: str = Field(
        ...,
        description="Detailed explanation of why the project qualifies",
        min_length=1
    )
    
    irs_source: str = Field(
        ...,
        description="Reference to specific IRS document and section",
        min_length=1
    )
    
    flagged_for_review: bool = Field(
        default=False,
        description="Whether this project needs manual review (auto-set for low confidence)"
    )
    
    technical_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional technical information (e.g., technological_uncertainty, experimentation_process)"
    )
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, v: float) -> float:
        """
        Validate that confidence_score is within valid range (0-1).
        
        Args:
            v: The confidence_score value to validate
            
        Returns:
            The validated confidence_score value
            
        Raises:
            ValueError: If confidence_score is not between 0 and 1
        """
        if v < 0 or v > 1:
            raise ValueError("confidence_score must be between 0 and 1")
        return v
    
    @field_validator('qualification_percentage')
    @classmethod
    def validate_qualification_percentage(cls, v: float) -> float:
        """
        Validate that qualification_percentage is within valid range (0-100).
        
        Args:
            v: The qualification_percentage value to validate
            
        Returns:
            The validated qualification_percentage value
            
        Raises:
            ValueError: If qualification_percentage is not between 0 and 100
        """
        if v < 0 or v > 100:
            raise ValueError("qualification_percentage must be between 0 and 100")
        return v
    
    @model_validator(mode='after')
    def auto_flag_low_confidence(self) -> 'QualifiedProject':
        """
        Automatically flag projects with low confidence scores for review.
        
        Projects with confidence_score < 0.7 are automatically flagged for manual review
        to ensure quality control and reduce risk of incorrect qualification decisions.
        This validator runs after all fields are validated and can access all field values.
        
        Returns:
            The model instance with flagged_for_review potentially updated
        """
        # If not explicitly flagged but confidence is low, auto-flag
        if not self.flagged_for_review and self.confidence_score < 0.7:
            self.flagged_for_review = True
        
        return self
    
    @computed_field
    @property
    def estimated_credit(self) -> float:
        """
        Calculate estimated R&D tax credit for this project.
        
        The R&D tax credit is typically 20% of qualified research expenditures (QREs)
        for the regular credit under IRC Section 41. This is a simplified calculation
        that assumes the regular credit rate.
        
        Returns:
            Estimated tax credit amount rounded to 2 decimal places
            
        Example:
            >>> project = QualifiedProject(
            ...     project_name="Test Project",
            ...     qualified_hours=10.0,
            ...     qualified_cost=1000.00,
            ...     confidence_score=0.85,
            ...     qualification_percentage=90.0,
            ...     supporting_citation="Test citation",
            ...     reasoning="Test reasoning",
            ...     irs_source="Test source"
            ... )
            >>> project.estimated_credit
            200.0
        """
        # Standard R&D tax credit rate is 20% of QREs
        credit_rate = 0.20
        return round(self.qualified_cost * credit_rate, 2)
    
    def __str__(self) -> str:
        """
        Return a human-readable string representation of the qualified project.
        
        Returns:
            Formatted string with key information about the qualification
        """
        flag_indicator = " [FLAGGED FOR REVIEW]" if self.flagged_for_review else ""
        return (
            f"{self.project_name}: {self.qualified_hours} hours, "
            f"${self.qualified_cost:.2f} qualified cost, "
            f"{self.qualification_percentage}% qualified, "
            f"confidence: {self.confidence_score:.2f}"
            f"{flag_indicator}"
        )
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "project_name": "Alpha Development",
                "qualified_hours": 14.5,
                "qualified_cost": 1045.74,
                "confidence_score": 0.92,
                "qualification_percentage": 95.0,
                "supporting_citation": "The project involves developing a new authentication algorithm with encryption, which constitutes qualified research under IRC Section 41. The work addresses technological uncertainty regarding secure authentication methods and involves a process of experimentation to evaluate alternatives.",
                "reasoning": "This project clearly meets the four-part test: (1) Technological in nature - involves computer science and cryptography; (2) Qualified purpose - developing new functionality; (3) Technological uncertainty - uncertainty about optimal encryption approach; (4) Process of experimentation - systematic evaluation of different authentication methods.",
                "irs_source": "CFR Title 26 § 1.41-4(a)(1) - Four-Part Test for Qualified Research",
                "flagged_for_review": False,
                "technical_details": {
                    "technological_uncertainty": "Uncertainty existed regarding the most secure and performant authentication algorithm that could handle high-volume concurrent requests while maintaining cryptographic integrity.",
                    "experimentation_process": "Team evaluated multiple encryption standards (AES-256, RSA-4096, ECC) and authentication protocols (OAuth 2.0, JWT, SAML) through systematic testing and benchmarking.",
                    "business_component": "User Authentication System",
                    "qualified_activities": [
                        "Algorithm design and prototyping",
                        "Security vulnerability testing",
                        "Performance optimization experiments",
                        "Integration testing with existing systems"
                    ]
                }
            }
        }



class AuditReport(BaseModel):
    """
    Represents the final audit-ready R&D tax credit report.
    
    This model captures the complete results of the R&D tax credit qualification
    process, including all qualified projects, aggregated totals, and metadata
    needed for IRS audit defense. Generated by the Audit Trail Agent.
    
    Attributes:
        report_id: Unique identifier for this report
        generation_date: Timestamp when the report was generated
        tax_year: Tax year for which this report applies (e.g., 2024)
        total_qualified_hours: Sum of all qualified hours across all projects
        total_qualified_cost: Sum of all qualified costs across all projects (in dollars)
        estimated_credit: Total estimated R&D tax credit amount (typically 20% of QREs)
        projects: List of all qualified projects included in this report
        company_name: Optional company name for the report
        report_notes: Optional additional notes or disclaimers
    
    Example:
        >>> from datetime import datetime
        >>> project1 = QualifiedProject(
        ...     project_name="Alpha Development",
        ...     qualified_hours=14.5,
        ...     qualified_cost=1045.74,
        ...     confidence_score=0.92,
        ...     qualification_percentage=95.0,
        ...     supporting_citation="Test citation",
        ...     reasoning="Test reasoning",
        ...     irs_source="CFR Title 26 § 1.41-4"
        ... )
        >>> report = AuditReport(
        ...     report_id="RPT-2024-001",
        ...     generation_date=datetime(2024, 12, 15),
        ...     tax_year=2024,
        ...     total_qualified_hours=14.5,
        ...     total_qualified_cost=1045.74,
        ...     estimated_credit=209.15,
        ...     projects=[project1],
        ...     company_name="Acme Corp"
        ... )
        >>> print(report.project_count)
        1
        >>> print(report.average_confidence)
        0.92
    """
    
    report_id: str = Field(
        ...,
        description="Unique identifier for this report",
        min_length=1
    )
    
    generation_date: datetime = Field(
        ...,
        description="Timestamp when the report was generated"
    )
    
    tax_year: int = Field(
        ...,
        description="Tax year for which this report applies (e.g., 2024)",
        ge=1900,
        le=2100
    )
    
    total_qualified_hours: float = Field(
        ...,
        description="Sum of all qualified hours across all projects",
        ge=0
    )
    
    total_qualified_cost: float = Field(
        ...,
        description="Sum of all qualified costs across all projects (in dollars)",
        ge=0
    )
    
    estimated_credit: float = Field(
        ...,
        description="Total estimated R&D tax credit amount (typically 20% of QREs)",
        ge=0
    )
    
    projects: List[QualifiedProject] = Field(
        ...,
        description="List of all qualified projects included in this report",
        min_length=0
    )
    
    company_name: Optional[str] = Field(
        default=None,
        description="Company name for the report"
    )
    
    report_notes: Optional[str] = Field(
        default=None,
        description="Additional notes or disclaimers for the report"
    )
    
    @field_validator('tax_year')
    @classmethod
    def validate_tax_year(cls, v: int) -> int:
        """
        Validate that tax_year is a reasonable year value.
        
        Tax year must be between 1900 and 2100 to be considered valid.
        This prevents obvious data entry errors while allowing historical
        and future year reporting.
        
        Args:
            v: The tax_year value to validate
            
        Returns:
            The validated tax_year value
            
        Raises:
            ValueError: If tax_year is not between 1900 and 2100
        """
        current_year = datetime.now().year
        
        if v < 1900 or v > 2100:
            raise ValueError("tax_year must be between 1900 and 2100")
        
        # Warning for future years (but don't reject)
        if v > current_year + 1:
            # This is just a logical check, we don't raise an error
            # as the field validator already enforces the range
            pass
        
        return v
    
    @model_validator(mode='after')
    def validate_aggregations(self) -> 'AuditReport':
        """
        Validate that aggregated totals match the sum of project values.
        
        This validator ensures data consistency by checking that the
        total_qualified_hours and total_qualified_cost fields match
        the sum of the corresponding fields in the projects list.
        
        Returns:
            The model instance after validation
            
        Raises:
            ValueError: If aggregated totals don't match project sums
        """
        if self.projects:
            # Calculate sums from projects
            calculated_hours = sum(p.qualified_hours for p in self.projects)
            calculated_cost = sum(p.qualified_cost for p in self.projects)
            
            # Allow small floating point differences (0.01)
            hours_diff = abs(self.total_qualified_hours - calculated_hours)
            cost_diff = abs(self.total_qualified_cost - calculated_cost)
            
            if hours_diff > 0.01:
                raise ValueError(
                    f"total_qualified_hours ({self.total_qualified_hours}) does not match "
                    f"sum of project hours ({calculated_hours})"
                )
            
            if cost_diff > 0.01:
                raise ValueError(
                    f"total_qualified_cost ({self.total_qualified_cost}) does not match "
                    f"sum of project costs ({calculated_cost})"
                )
        
        return self
    
    @computed_field
    @property
    def project_count(self) -> int:
        """
        Get the total number of qualified projects in this report.
        
        Returns:
            Number of projects in the report
        """
        return len(self.projects)
    
    @computed_field
    @property
    def average_confidence(self) -> float:
        """
        Calculate the average confidence score across all projects.
        
        Returns:
            Average confidence score (0-1), or 0.0 if no projects
        """
        if not self.projects:
            return 0.0
        
        total_confidence = sum(p.confidence_score for p in self.projects)
        return round(total_confidence / len(self.projects), 2)
    
    @computed_field
    @property
    def flagged_project_count(self) -> int:
        """
        Count how many projects are flagged for review.
        
        Returns:
            Number of projects flagged for manual review
        """
        return sum(1 for p in self.projects if p.flagged_for_review)
    
    def __str__(self) -> str:
        """
        Return a human-readable string representation of the audit report.
        
        Returns:
            Formatted string with key report information
        """
        return (
            f"Audit Report {self.report_id} (Tax Year {self.tax_year}): "
            f"{self.project_count} projects, "
            f"{self.total_qualified_hours:.1f} hours, "
            f"${self.total_qualified_cost:.2f} qualified cost, "
            f"${self.estimated_credit:.2f} estimated credit"
        )
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "report_id": "RPT-2024-001",
                "generation_date": "2024-12-15T10:30:00",
                "tax_year": 2024,
                "total_qualified_hours": 145.5,
                "total_qualified_cost": 10457.40,
                "estimated_credit": 2091.48,
                "projects": [
                    {
                        "project_name": "Alpha Development",
                        "qualified_hours": 14.5,
                        "qualified_cost": 1045.74,
                        "confidence_score": 0.92,
                        "qualification_percentage": 95.0,
                        "supporting_citation": "Test citation",
                        "reasoning": "Test reasoning",
                        "irs_source": "CFR Title 26 § 1.41-4"
                    }
                ],
                "company_name": "Acme Corporation",
                "report_notes": "This report covers R&D activities for the 2024 tax year."
            }
        }


class RAGContext(BaseModel):
    """
    Represents retrieved context from the RAG Knowledge Tool for R&D qualification decisions.
    
    This model captures the results of RAG (Retrieval-Augmented Generation) queries against
    the local IRS document knowledge base. It stores retrieved text chunks with their metadata
    and provides methods to format context for LLM prompts and extract citations for audit trails.
    
    Attributes:
        query: The original query used to retrieve this context
        chunks: List of retrieved text chunks with metadata (text, source, page, relevance_score)
        retrieval_timestamp: When this context was retrieved
        total_chunks_available: Total number of chunks available in the knowledge base
        retrieval_method: Method used for retrieval (e.g., "semantic_search", "keyword_search")
    
    Example:
        >>> context = RAGContext(
        ...     query="What are the requirements for qualified research under IRC Section 41?",
        ...     chunks=[
        ...         {
        ...             "text": "Qualified research must meet the four-part test...",
        ...             "source": "CFR Title 26 § 1.41-4",
        ...             "page": 3,
        ...             "relevance_score": 0.92
        ...         }
        ...     ],
        ...     retrieval_timestamp=datetime.now(),
        ...     total_chunks_available=150,
        ...     retrieval_method="semantic_search"
        ... )
        >>> print(context.format_for_llm_prompt())
        >>> print(context.extract_citations())
    """
    
    query: str = Field(
        ...,
        description="The original query used to retrieve this context",
        min_length=1
    )
    
    chunks: List[Dict[str, Any]] = Field(
        ...,
        description="List of retrieved text chunks with metadata",
        min_length=0
    )
    
    retrieval_timestamp: datetime = Field(
        ...,
        description="When this context was retrieved"
    )
    
    total_chunks_available: int = Field(
        ...,
        description="Total number of chunks available in the knowledge base",
        ge=0
    )
    
    retrieval_method: str = Field(
        default="semantic_search",
        description="Method used for retrieval (e.g., semantic_search, keyword_search)"
    )
    
    @field_validator('chunks')
    @classmethod
    def validate_chunks(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate that each chunk contains required fields.
        
        Each chunk must have: text, source, page, and relevance_score.
        
        Args:
            v: The chunks list to validate
            
        Returns:
            The validated chunks list
            
        Raises:
            ValueError: If any chunk is missing required fields
        """
        required_fields = {'text', 'source', 'page', 'relevance_score'}
        
        for i, chunk in enumerate(v):
            missing_fields = required_fields - set(chunk.keys())
            if missing_fields:
                raise ValueError(
                    f"Chunk {i} is missing required fields: {missing_fields}"
                )
            
            # Validate field types
            if not isinstance(chunk['text'], str) or len(chunk['text']) == 0:
                raise ValueError(f"Chunk {i} 'text' must be a non-empty string")
            
            if not isinstance(chunk['source'], str) or len(chunk['source']) == 0:
                raise ValueError(f"Chunk {i} 'source' must be a non-empty string")
            
            if not isinstance(chunk['page'], int) or chunk['page'] < 1:
                raise ValueError(f"Chunk {i} 'page' must be a positive integer")
            
            if not isinstance(chunk['relevance_score'], (int, float)):
                raise ValueError(f"Chunk {i} 'relevance_score' must be a number")
            
            if chunk['relevance_score'] < 0 or chunk['relevance_score'] > 1:
                raise ValueError(f"Chunk {i} 'relevance_score' must be between 0 and 1")
        
        return v
    
    @computed_field
    @property
    def chunk_count(self) -> int:
        """
        Get the number of chunks retrieved.
        
        Returns:
            Number of chunks in this context
        """
        return len(self.chunks)
    
    @computed_field
    @property
    def average_relevance(self) -> float:
        """
        Calculate the average relevance score across all chunks.
        
        Returns:
            Average relevance score (0-1), or 0.0 if no chunks
        """
        if not self.chunks:
            return 0.0
        
        total_relevance = sum(chunk['relevance_score'] for chunk in self.chunks)
        return round(total_relevance / len(self.chunks), 2)
    
    def format_for_llm_prompt(self, max_chunks: Optional[int] = None) -> str:
        """
        Format the retrieved context for inclusion in an LLM prompt.
        
        This method creates a formatted string containing all retrieved chunks
        with their source citations, suitable for providing context to an LLM
        for R&D qualification decisions.
        
        Args:
            max_chunks: Optional limit on number of chunks to include (uses top-ranked)
            
        Returns:
            Formatted string with context and citations
            
        Example:
            >>> context = RAGContext(
            ...     query="What is the four-part test?",
            ...     chunks=[
            ...         {
            ...             "text": "Qualified research must meet four criteria...",
            ...             "source": "CFR Title 26 § 1.41-4",
            ...             "page": 3,
            ...             "relevance_score": 0.95
            ...         }
            ...     ],
            ...     retrieval_timestamp=datetime.now(),
            ...     total_chunks_available=100
            ... )
            >>> print(context.format_for_llm_prompt())
            === IRS GUIDANCE CONTEXT ===
            
            [Source: CFR Title 26 § 1.41-4, Page 3]
            Qualified research must meet four criteria...
            
            === END CONTEXT ===
        """
        if not self.chunks:
            return "No relevant IRS guidance found for this query."
        
        # Sort chunks by relevance score (highest first)
        sorted_chunks = sorted(
            self.chunks,
            key=lambda x: x['relevance_score'],
            reverse=True
        )
        
        # Limit chunks if specified
        if max_chunks:
            sorted_chunks = sorted_chunks[:max_chunks]
        
        # Build formatted context
        formatted_parts = ["=== IRS GUIDANCE CONTEXT ===\n"]
        
        for i, chunk in enumerate(sorted_chunks, 1):
            formatted_parts.append(
                f"[Source: {chunk['source']}, Page {chunk['page']}]\n"
                f"{chunk['text']}\n"
            )
        
        formatted_parts.append("=== END CONTEXT ===")
        
        return "\n".join(formatted_parts)
    
    def extract_citations(self) -> List[str]:
        """
        Extract unique source citations from all retrieved chunks.
        
        This method creates a list of unique citations that can be included
        in audit reports to support R&D qualification decisions.
        
        Returns:
            List of unique citation strings (e.g., "CFR Title 26 § 1.41-4, Page 3")
            
        Example:
            >>> context = RAGContext(
            ...     query="What is qualified research?",
            ...     chunks=[
            ...         {
            ...             "text": "Text 1...",
            ...             "source": "CFR Title 26 § 1.41-4",
            ...             "page": 3,
            ...             "relevance_score": 0.95
            ...         },
            ...         {
            ...             "text": "Text 2...",
            ...             "source": "CFR Title 26 § 1.41-4",
            ...             "page": 5,
            ...             "relevance_score": 0.88
            ...         },
            ...         {
            ...             "text": "Text 3...",
            ...             "source": "Form 6765 Instructions",
            ...             "page": 2,
            ...             "relevance_score": 0.82
            ...         }
            ...     ],
            ...     retrieval_timestamp=datetime.now(),
            ...     total_chunks_available=100
            ... )
            >>> citations = context.extract_citations()
            >>> print(citations)
            ['CFR Title 26 § 1.41-4, Page 3', 'CFR Title 26 § 1.41-4, Page 5', 'Form 6765 Instructions, Page 2']
        """
        citations = []
        seen = set()
        
        for chunk in self.chunks:
            citation = f"{chunk['source']}, Page {chunk['page']}"
            if citation not in seen:
                citations.append(citation)
                seen.add(citation)
        
        return citations
    
    def __str__(self) -> str:
        """
        Return a human-readable string representation of the RAG context.
        
        Returns:
            Formatted string with key information about the retrieved context
        """
        return (
            f"RAG Context: {self.chunk_count} chunks retrieved "
            f"(avg relevance: {self.average_relevance:.2f}) "
            f"for query: '{self.query[:50]}...'"
        )
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "query": "What are the requirements for qualified research under IRC Section 41?",
                "chunks": [
                    {
                        "text": "Qualified research must meet the four-part test: (1) The research must be technological in nature, meaning it relies on principles of physical or biological sciences, engineering, or computer science. (2) The research must be undertaken for the purpose of discovering information that is technological in nature and the application of which is intended to be useful in the development of a new or improved business component. (3) Substantially all of the activities must constitute elements of a process of experimentation. (4) The process of experimentation must relate to a new or improved function, performance, reliability, or quality.",
                        "source": "CFR Title 26 § 1.41-4(a)(1)",
                        "page": 3,
                        "relevance_score": 0.95
                    },
                    {
                        "text": "A process of experimentation is a process designed to evaluate one or more alternatives to achieve a result where the capability or the method of achieving that result, or the appropriate design of that result, is uncertain as of the beginning of the taxpayer's research activities. A process of experimentation must fundamentally rely on the principles of the physical or biological sciences, engineering, or computer science and involves the identification of uncertainty concerning the development or improvement of a business component.",
                        "source": "CFR Title 26 § 1.41-4(a)(5)",
                        "page": 5,
                        "relevance_score": 0.88
                    },
                    {
                        "text": "Qualified research expenses (QREs) include in-house research expenses and contract research expenses. In-house research expenses consist of wages paid to employees for qualified services, supplies used in the conduct of qualified research, and amounts paid for the use of computers in the conduct of qualified research. The wage component is subject to certain limitations and must be properly allocated to qualified research activities.",
                        "source": "Form 6765 Instructions",
                        "page": 2,
                        "relevance_score": 0.82
                    }
                ],
                "retrieval_timestamp": "2024-03-15T14:30:00",
                "total_chunks_available": 150,
                "retrieval_method": "semantic_search"
            }
        }
