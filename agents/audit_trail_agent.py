"""
Audit Trail Agent for R&D Tax Credit Automation.

This agent is responsible for generating comprehensive audit-ready documentation
including R&D project narratives, compliance reviews, and PDF reports.

The agent uses PydanticAI for structured agent workflows, You.com APIs for
narrative generation and compliance review, GLM 4.5 Air via OpenRouter for
agent reasoning, and ReportLab/xhtml2pdf for PDF generation.

Requirements: 4.1, 8.1
"""

import asyncio
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
        compliance_reviews: Dictionary mapping project names to compliance review results
        execution_time_seconds: Total execution time
        summary: Human-readable summary of generation results
    """
    
    report: Optional[AuditReport] = Field(
        default=None,
        description="Generated audit report"
    )
    
    pdf_path: Optional[str] = Field(
        default=None,
        description="Path to generated PDF file"
    )
    
    narratives: Dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary mapping project names to generated narratives"
    )
    
    compliance_reviews: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Dictionary mapping project names to compliance review results"
    )
    
    execution_time_seconds: float = Field(
        default=0.0,
        description="Total execution time in seconds"
    )
    
    summary: str = Field(
        default="",
        description="Human-readable summary of generation results"
    )
    
    aggregated_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Aggregated report data including totals, statistics, and DataFrames"
    )


class AuditTrailAgent:
    """
    PydanticAI-based agent for audit trail generation and PDF report creation.
    
    This agent generates comprehensive audit-ready documentation by:
    1. Generating technical narratives for each qualified project using You.com Agent API
    2. Reviewing narratives for compliance completeness using You.com Express Agent
    3. Aggregating all data and generating a professional PDF report
    
    The agent uses:
    - You.com Agent API for narrative generation
    - You.com Express Agent for compliance review
    - GLM 4.5 Air via OpenRouter for agent reasoning and decision-making
    - PDFGenerator (to be implemented) for PDF creation
    
    The agent maintains state throughout execution and can send real-time
    status updates via WebSocket for frontend visualization.
    
    Example:
        >>> from tools.you_com_client import YouComClient
        >>> from tools.glm_reasoner import GLMReasoner
        >>> 
        >>> # Initialize agent with tools
        >>> youcom_client = YouComClient(api_key="...")
        >>> glm_reasoner = GLMReasoner(api_key="...")
        >>> 
        >>> agent = AuditTrailAgent(
        ...     youcom_client=youcom_client,
        ...     glm_reasoner=glm_reasoner
        ... )
        >>> 
        >>> # Run audit trail generation
        >>> result = agent.run(
        ...     qualified_projects=qualified_projects,
        ...     tax_year=2024
        ... )
        >>> 
        >>> print(f"Generated report at: {result.pdf_path}")
        >>> print(f"Processed {len(result.narratives)} projects")
    
    Requirements: 4.1, 8.1
    """
    
    def __init__(
        self,
        youcom_client: YouComClient,
        glm_reasoner: GLMReasoner,
        pdf_generator: Optional[Any] = None,
        status_callback: Optional[callable] = None
    ):
        """
        Initialize Audit Trail Agent.
        
        Args:
            youcom_client: Initialized YouComClient for Agent and Express Agent APIs
            glm_reasoner: Initialized GLMReasoner for GLM 4.5 Air reasoning via OpenRouter
            pdf_generator: Optional PDFGenerator instance (to be implemented in task 118)
            status_callback: Optional callback function for status updates
                            (receives StatusUpdateMessage objects)
        
        Raises:
            ValueError: If required tools are None
        """
        if youcom_client is None:
            raise ValueError("youcom_client cannot be None")
        if glm_reasoner is None:
            raise ValueError("glm_reasoner cannot be None")
        
        self.youcom_client = youcom_client
        self.glm_reasoner = glm_reasoner
        self.pdf_generator = pdf_generator
        self.status_callback = status_callback
        
        # Initialize agent state
        self.state = AuditTrailState()
        
        logger.info(
            "Initialized Audit Trail Agent with YouComClient and GLMReasoner "
            "(GLM 4.5 Air via OpenRouter)"
        )
        
        if pdf_generator:
            logger.info("PDF generator provided and ready")
        else:
            logger.warning(
                "PDF generator not provided - PDF generation will be unavailable "
                "(will be implemented in task 118)"
            )
    
    def _update_status(
        self,
        stage: str,
        status: AgentStatus,
        current_project: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Update agent state and send status update via callback.
        
        Args:
            stage: Current stage description
            status: Current execution status
            current_project: Optional name of project currently being processed
            error_message: Optional error message if status is ERROR
        """
        self.state.stage = stage
        self.state.status = status
        
        if current_project:
            self.state.current_project = current_project
        
        if error_message:
            self.state.error_message = error_message
        
        # Log status update
        log_level = logging.ERROR if status == AgentStatus.ERROR else logging.INFO
        logger.log(
            log_level,
            f"Status update: {stage} - {status.value}"
            + (f" - {current_project}" if current_project else "")
            + (f" - {error_message}" if error_message else "")
        )
        
        # Send status update via callback if provided
        if self.status_callback:
            try:
                status_message = self.state.to_status_message()
                self.status_callback(status_message)
            except Exception as e:
                logger.error(f"Failed to send status update: {e}")
    
    async def _generate_narrative_async(
        self,
        project: QualifiedProject,
        template_url: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Async wrapper for narrative generation to enable concurrent processing.
        
        Args:
            project: QualifiedProject object with qualification results
            template_url: Optional URL to fetch narrative template from
        
        Returns:
            Tuple of (project_name, narrative_text)
        
        Raises:
            APIConnectionError: If You.com API calls fail
        """
        try:
            # Update status for this project
            self._update_status(
                stage="generating_narratives",
                status=AgentStatus.IN_PROGRESS,
                current_project=project.project_name
            )
            
            # Generate narrative (synchronous call wrapped in async)
            narrative = await asyncio.to_thread(
                self._generate_narrative,
                project,
                template_url
            )
            
            # Increment counter
            self.state.narratives_generated += 1
            
            # Log progress
            logger.info(
                f"Generated narrative {self.state.narratives_generated}/"
                f"{self.state.projects_to_process} for project: {project.project_name}"
            )
            
            # Send progress update
            self._update_status(
                stage="generating_narratives",
                status=AgentStatus.IN_PROGRESS,
                current_project=project.project_name
            )
            
            return (project.project_name, narrative)
            
        except Exception as e:
            logger.error(
                f"Failed to generate narrative for {project.project_name}: {str(e)}",
                exc_info=True
            )
            # Return project name with error message as narrative
            error_narrative = (
                f"ERROR: Failed to generate narrative for {project.project_name}. "
                f"Reason: {str(e)}"
            )
            return (project.project_name, error_narrative)
    
    async def _generate_narratives_batch(
        self,
        qualified_projects: List[QualifiedProject],
        template_url: Optional[str] = None,
        max_concurrent: int = 5
    ) -> Dict[str, str]:
        """
        Generate narratives for all qualified projects concurrently.
        
        This method processes multiple projects in parallel to improve performance
        while respecting rate limits. It uses asyncio to manage concurrent
        You.com API calls and provides real-time progress updates.
        
        Args:
            qualified_projects: List of QualifiedProject objects to process
            template_url: Optional URL to fetch narrative template from
            max_concurrent: Maximum number of concurrent narrative generations
                           (default: 5 to respect You.com rate limits)
        
        Returns:
            Dictionary mapping project names to generated narratives
        
        Example:
            >>> agent = AuditTrailAgent(youcom_client=..., glm_reasoner=...)
            >>> narratives = await agent._generate_narratives_batch(
            ...     qualified_projects=projects,
            ...     max_concurrent=5
            ... )
            >>> print(f"Generated {len(narratives)} narratives")
        
        Requirements: 4.1
        """
        logger.info(
            f"Starting batch narrative generation for {len(qualified_projects)} projects "
            f"(max_concurrent={max_concurrent})"
        )
        
        # Initialize narratives dictionary
        narratives = {}
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_with_semaphore(project: QualifiedProject):
            """Generate narrative with semaphore to limit concurrency."""
            async with semaphore:
                return await self._generate_narrative_async(project, template_url)
        
        # Create tasks for all projects
        tasks = [
            generate_with_semaphore(project)
            for project in qualified_projects
        ]
        
        # Execute all tasks concurrently and gather results
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task failed with exception: {result}")
                    continue
                
                project_name, narrative = result
                narratives[project_name] = narrative
                
                # Log You.com API call
                logger.info(
                    f"You.com Agent API call completed for project: {project_name} "
                    f"(narrative_length={len(narrative)} chars)"
                )
            
            logger.info(
                f"Batch narrative generation complete: "
                f"{len(narratives)}/{len(qualified_projects)} narratives generated"
            )
            
            return narratives
            
        except Exception as e:
            logger.error(
                f"Batch narrative generation failed: {str(e)}",
                exc_info=True
            )
            raise
    
    def run(
        self,
        qualified_projects: List[QualifiedProject],
        tax_year: int,
        company_name: Optional[str] = None
    ) -> AuditTrailResult:
        """
        Run the audit trail generation workflow.
        
        This method orchestrates the complete audit trail generation process:
        1. Generate technical narratives for each project using You.com Agent API
        2. Review narratives for compliance using You.com Express Agent
        3. Aggregate all data
        4. Generate PDF report (when PDFGenerator is implemented)
        
        Args:
            qualified_projects: List of QualifiedProject objects from Qualification Agent
            tax_year: Tax year for the report
            company_name: Optional company name for report header
        
        Returns:
            AuditTrailResult with generated report and metadata
        
        Raises:
            ValueError: If inputs are invalid
            APIConnectionError: If You.com or OpenRouter APIs fail
        
        Example:
            >>> agent = AuditTrailAgent(youcom_client=..., glm_reasoner=...)
            >>> result = agent.run(
            ...     qualified_projects=qualified_projects,
            ...     tax_year=2024,
            ...     company_name="Acme Corp"
            ... )
        
        Requirements: 4.1, 4.4, 4.5
        """
        # Validate inputs
        if not qualified_projects:
            raise ValueError("qualified_projects cannot be empty")
        
        if tax_year < 2000 or tax_year > 2100:
            raise ValueError(f"Invalid tax_year: {tax_year}")
        
        # Initialize result
        result = AuditTrailResult()
        
        # Record start time
        self.state.start_time = datetime.now()
        self.state.status = AgentStatus.IN_PROGRESS
        self.state.projects_to_process = len(qualified_projects)
        
        logger.info(
            f"Starting audit trail generation for {len(qualified_projects)} projects "
            f"(tax year: {tax_year})"
        )
        
        try:
            # Stage 1: Generate narratives using batch processing
            self._update_status(
                stage="generating_narratives",
                status=AgentStatus.IN_PROGRESS
            )
            
            logger.info(
                f"Starting batch narrative generation for {len(qualified_projects)} projects"
            )
            
            # Run async batch narrative generation
            # Use asyncio.run to execute the async method in sync context
            narratives = asyncio.run(
                self._generate_narratives_batch(
                    qualified_projects=qualified_projects,
                    template_url=None,  # Can be configured to fetch templates
                    max_concurrent=5  # Respect You.com rate limits
                )
            )
            
            # Store narratives in result
            result.narratives = narratives
            
            logger.info(
                f"Successfully generated {len(narratives)} narratives "
                f"(total API calls: {len(narratives)})"
            )
            
            # Stage 2: Review narratives for compliance
            self._update_status(
                stage="reviewing_narratives",
                status=AgentStatus.IN_PROGRESS
            )
            
            logger.info(
                f"Starting compliance review for {len(narratives)} narratives "
                "using You.com Express Agent API"
            )
            
            # Review each narrative for compliance
            compliance_reviews = {}
            for project_name, narrative in narratives.items():
                try:
                    # Find the corresponding project for context
                    project = next(
                        (p for p in qualified_projects if p.project_name == project_name),
                        None
                    )
                    
                    if project:
                        # Update status for this project
                        self._update_status(
                            stage="reviewing_narratives",
                            status=AgentStatus.IN_PROGRESS,
                            current_project=project_name
                        )
                        
                        # Review the narrative
                        review_result = self._review_narrative(
                            narrative=narrative,
                            project=project
                        )
                        
                        compliance_reviews[project_name] = review_result
                        
                        # Increment counter
                        self.state.narratives_reviewed += 1
                        
                        logger.info(
                            f"Reviewed narrative {self.state.narratives_reviewed}/"
                            f"{len(narratives)} for project: {project_name} "
                            f"(status: {review_result.get('compliance_status', 'unknown')})"
                        )
                    else:
                        logger.warning(
                            f"Could not find project object for {project_name}, "
                            "skipping compliance review"
                        )
                        
                except Exception as e:
                    logger.error(
                        f"Failed to review narrative for {project_name}: {str(e)}",
                        exc_info=True
                    )
                    # Store error in review results
                    compliance_reviews[project_name] = {
                        'compliance_status': 'Error',
                        'error': str(e)
                    }
            
            # Store compliance reviews in result
            result.compliance_reviews = compliance_reviews
            
            logger.info(
                f"Compliance review complete: {len(compliance_reviews)} narratives reviewed"
            )
            
            # Stage 3: Aggregate data
            self._update_status(
                stage="aggregating_data",
                status=AgentStatus.IN_PROGRESS
            )
            
            logger.info(
                "Starting final data aggregation for report generation"
            )
            
            # Aggregate all qualified data using Pandas
            aggregated_data = self._aggregate_report_data(
                qualified_projects=qualified_projects,
                tax_year=tax_year
            )
            
            logger.info(
                f"Data aggregation complete: "
                f"Total hours: {aggregated_data['total_qualified_hours']:.2f}, "
                f"Total cost: ${aggregated_data['total_qualified_cost']:,.2f}, "
                f"Estimated credit: ${aggregated_data['estimated_credit']:,.2f}"
            )
            
            # Stage 4: Generate PDF (placeholder - will be implemented in task 121)
            self._update_status(
                stage="generating_pdf",
                status=AgentStatus.IN_PROGRESS
            )
            
            if self.pdf_generator:
                logger.info("PDF generation will be implemented in task 121")
                # TODO: Implement PDF generation in task 121
            else:
                logger.warning(
                    "PDF generator not available - skipping PDF generation. "
                    "Will be implemented in task 118"
                )
            
            # Record end time and calculate execution time
            self.state.end_time = datetime.now()
            execution_time = (self.state.end_time - self.state.start_time).total_seconds()
            
            # Build result with aggregated data
            result.execution_time_seconds = execution_time
            result.aggregated_data = aggregated_data  # Store aggregated data for PDF generation
            result.summary = (
                f"Generated {len(result.narratives)} narratives for {len(qualified_projects)} projects "
                f"in {execution_time:.2f} seconds. "
                f"Total qualified cost: ${aggregated_data['total_qualified_cost']:,.2f}, "
                f"Estimated credit: ${aggregated_data['estimated_credit']:,.2f}, "
                f"Average confidence: {aggregated_data['average_confidence']:.2%}. "
                f"PDF generation pending (task 121)."
            )
            
            # Update final status
            self._update_status(
                stage="completed",
                status=AgentStatus.COMPLETED
            )
            
            logger.info(f"Audit trail generation workflow complete: {result.summary}")
            
            return result
        
        except APIConnectionError as e:
            # Handle API connection errors
            error_msg = f"API connection failed: {e.message}"
            logger.error(error_msg, exc_info=True)
            
            self._update_status(
                stage="error",
                status=AgentStatus.ERROR,
                error_message=error_msg
            )
            
            raise
        
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error during audit trail generation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            self._update_status(
                stage="error",
                status=AgentStatus.ERROR,
                error_message=error_msg
            )
            
            raise
    
    def _generate_narrative(
        self,
        project: QualifiedProject,
        template_url: Optional[str] = None
    ) -> str:
        """
        Generate a comprehensive technical narrative for a single qualified project.
        
        This method orchestrates the narrative generation process:
        1. Optionally fetch a narrative template using You.com Contents API
        2. Create a detailed prompt with project information and qualification reasoning
        3. Call You.com Agent API to generate the technical narrative
        4. Return the generated narrative text
        
        The narrative includes:
        - Project overview and timeline
        - Technical uncertainties that existed
        - Process of experimentation used
        - Technological nature of the work
        - Qualified purpose and business component
        - Outcomes and results achieved
        
        Args:
            project: QualifiedProject object with qualification results
            template_url: Optional URL to fetch narrative template from
                         If None, uses built-in template structure
        
        Returns:
            Generated narrative text as a string
        
        Raises:
            APIConnectionError: If You.com API calls fail
            ValueError: If project data is invalid
        
        Example:
            >>> agent = AuditTrailAgent(youcom_client=..., glm_reasoner=...)
            >>> project = QualifiedProject(
            ...     project_name="API Optimization",
            ...     qualified_hours=120.5,
            ...     qualified_cost=15000.00,
            ...     confidence_score=0.92,
            ...     qualification_percentage=85.0,
            ...     supporting_citation="...",
            ...     reasoning="...",
            ...     irs_source="CFR Title 26 § 1.41-4"
            ... )
            >>> narrative = agent._generate_narrative(project)
            >>> print(f"Generated {len(narrative)} characters")
        
        Requirements: 4.1, 4.2
        """
        logger.info(
            f"Generating narrative for project: {project.project_name} "
            f"(qualification={project.qualification_percentage}%, "
            f"confidence={project.confidence_score})"
        )
        
        # Step 1: Optionally fetch narrative template using You.com Contents API
        template_content = None
        if template_url:
            try:
                logger.info(f"Fetching narrative template from URL: {template_url}")
                template_response = self.youcom_client.fetch_content(
                    url=template_url,
                    format="markdown"
                )
                template_content = template_response.get('content', '')
                logger.info(
                    f"Successfully fetched template "
                    f"(word_count={template_response.get('word_count', 0)})"
                )
            except APIConnectionError as e:
                logger.warning(
                    f"Failed to fetch narrative template from {template_url}: {e.message}. "
                    f"Continuing with built-in template structure."
                )
                # Continue without external template - we have a built-in structure
            except Exception as e:
                logger.warning(
                    f"Unexpected error fetching template: {str(e)}. "
                    f"Continuing with built-in template structure."
                )
        
        # Step 2: Create prompt with project details and qualification reasoning
        # Import prompt template function
        from tools.prompt_templates import populate_narrative_generation_prompt
        
        # Build the narrative generation prompt with all project details
        narrative_prompt = populate_narrative_generation_prompt(
            project_name=project.project_name,
            qualification_percentage=project.qualification_percentage,
            qualified_hours=project.qualified_hours,
            qualified_cost=project.qualified_cost,
            confidence_score=project.confidence_score,
            qualification_reasoning=project.reasoning,
            irs_citations=f"{project.irs_source}\n\nSupporting Citation:\n{project.supporting_citation}"
        )
        
        # If we have a fetched template, add it to the prompt
        if template_content:
            narrative_prompt = (
                f"## Reference Template\n\n"
                f"Use the following template as a structural reference:\n\n"
                f"{template_content}\n\n"
                f"---\n\n"
                f"{narrative_prompt}"
            )
        
        # Add technical details if available
        if project.technical_details:
            technical_info = "\n\n## Additional Technical Information\n\n"
            for key, value in project.technical_details.items():
                technical_info += f"**{key.replace('_', ' ').title()}:** {value}\n\n"
            narrative_prompt += technical_info
        
        logger.debug(
            f"Created narrative generation prompt "
            f"(length={len(narrative_prompt)} chars)"
        )
        
        # Step 3: Call You.com Agent API to generate technical narrative
        try:
            logger.info(
                f"Calling You.com Agent API for narrative generation "
                f"(project: {project.project_name})"
            )
            
            # Use You.com Agent API in express mode for narrative generation
            # Express mode provides fast, high-quality responses with web search capability
            agent_response = self.youcom_client.agent_run(
                prompt=narrative_prompt,
                agent_mode="express",
                stream=False
            )
            
            # Extract the narrative text from the agent response
            # The response format is: {'output': [{'type': '...', 'text': '...', ...}]}
            narrative_text = ""
            
            if 'output' in agent_response and agent_response['output']:
                # Find the chat answer in the output
                for output_item in agent_response['output']:
                    if output_item.get('type') == 'chat_node.answer':
                        narrative_text = output_item.get('text', '')
                        break
                
                # If no chat answer found, use the first text output
                if not narrative_text and agent_response['output']:
                    narrative_text = agent_response['output'][0].get('text', '')
            
            if not narrative_text:
                raise ValueError(
                    "You.com Agent API returned empty narrative. "
                    "Response structure may have changed."
                )
            
            logger.info(
                f"Successfully generated narrative for {project.project_name} "
                f"(length={len(narrative_text)} chars)"
            )
            
            # Log a preview of the narrative
            preview = narrative_text[:200] + "..." if len(narrative_text) > 200 else narrative_text
            logger.debug(f"Narrative preview: {preview}")
            
            return narrative_text
            
        except APIConnectionError as e:
            logger.error(
                f"You.com Agent API failed during narrative generation "
                f"for project {project.project_name}: {e.message}"
            )
            raise
        
        except Exception as e:
            error_msg = (
                f"Unexpected error generating narrative for {project.project_name}: "
                f"{str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            raise APIConnectionError(
                message=error_msg,
                api_name="You.com Agent API",
                endpoint="/v1/agents/runs",
                details={"error": str(e), "project": project.project_name}
            )
    
    def _review_narrative(
        self,
        narrative: str,
        project: QualifiedProject
    ) -> Dict[str, Any]:
        """
        Review a generated narrative for compliance completeness using You.com Express Agent.
        
        This method performs a comprehensive compliance review of a generated R&D project
        narrative to ensure it meets IRS requirements for audit-ready documentation.
        It uses You.com Express Agent API for quick, expert-level compliance checks.
        
        The review verifies that the narrative includes:
        - Technical uncertainties clearly identified
        - Process of experimentation documented
        - Technological nature demonstrated
        - Qualified purpose explained
        - Sufficient detail and professional quality
        
        Args:
            narrative: The generated narrative text to review
            project: QualifiedProject object with qualification data for context
        
        Returns:
            Dictionary containing compliance review results:
                - compliance_status: Overall status (Compliant/Needs Revision/Non-Compliant)
                - completeness_score: Score from 0-100 indicating completeness
                - missing_elements: List of missing or weak elements
                - strengths: List of strong aspects of the narrative
                - recommendations: List of specific improvement suggestions
                - risk_assessment: Assessment of IRS challenge likelihood
                - required_revisions: List of must-fix issues
                - flagged_for_review: Boolean indicating if manual review needed
                - review_summary: Brief summary of the review
        
        Raises:
            APIConnectionError: If You.com Express Agent API call fails
            ValueError: If narrative or project data is invalid
        
        Example:
            >>> agent = AuditTrailAgent(youcom_client=..., glm_reasoner=...)
            >>> narrative = "Project Overview: This project aimed to..."
            >>> project = QualifiedProject(...)
            >>> review = agent._review_narrative(narrative, project)
            >>> 
            >>> if review['flagged_for_review']:
            ...     print(f"Manual review needed: {review['review_summary']}")
            >>> 
            >>> if review['compliance_status'] == 'Needs Revision':
            ...     print("Required revisions:")
            ...     for revision in review['required_revisions']:
            ...         print(f"  - {revision}")
        
        Requirements: 4.3, 6.3
        """
        logger.info(
            f"Reviewing narrative for compliance: {project.project_name} "
            f"(narrative_length={len(narrative)} chars)"
        )
        
        # Validate inputs
        if not narrative or not narrative.strip():
            raise ValueError("Narrative cannot be empty")
        
        if len(narrative) < 100:
            logger.warning(
                f"Narrative for {project.project_name} is very short ({len(narrative)} chars). "
                "This may indicate a generation issue."
            )
        
        # Import prompt template function
        from tools.prompt_templates import populate_youcom_compliance_review_prompt
        
        # Create compliance review prompt with the narrative
        review_prompt = populate_youcom_compliance_review_prompt(
            narrative_text=narrative
        )
        
        # Add project context to help with review
        project_context = (
            f"\n\n## Project Context\n\n"
            f"**Project Name:** {project.project_name}\n"
            f"**Qualification Percentage:** {project.qualification_percentage}%\n"
            f"**Confidence Score:** {project.confidence_score:.2f}\n"
            f"**Qualified Hours:** {project.qualified_hours}\n"
            f"**Qualified Cost:** ${project.qualified_cost:,.2f}\n"
            f"**IRS Source:** {project.irs_source}\n\n"
            f"**Original Qualification Reasoning:**\n{project.reasoning}\n"
        )
        
        review_prompt += project_context
        
        logger.debug(
            f"Created compliance review prompt "
            f"(length={len(review_prompt)} chars)"
        )
        
        # Call You.com Express Agent API for compliance review
        try:
            logger.info(
                f"Calling You.com Express Agent API for compliance review "
                f"(project: {project.project_name})"
            )
            
            # Use You.com Agent API in express mode for fast compliance review
            # Express mode is ideal for quick QA checks and compliance verification
            agent_response = self.youcom_client.agent_run(
                prompt=review_prompt,
                agent_mode="express",
                stream=False
            )
            
            # Extract the review text from the agent response
            review_text = ""
            
            if 'output' in agent_response and agent_response['output']:
                # Find the chat answer in the output
                for output_item in agent_response['output']:
                    if output_item.get('type') == 'chat_node.answer':
                        review_text = output_item.get('text', '')
                        break
                
                # If no chat answer found, use the first text output
                if not review_text and agent_response['output']:
                    review_text = agent_response['output'][0].get('text', '')
            
            if not review_text:
                raise ValueError(
                    "You.com Express Agent API returned empty review. "
                    "Response structure may have changed."
                )
            
            logger.info(
                f"Successfully received compliance review for {project.project_name} "
                f"(review_length={len(review_text)} chars)"
            )
            
            # Parse the review response to extract structured data
            review_result = self._parse_compliance_review(review_text, project)
            
            # Log review summary
            logger.info(
                f"Compliance review for {project.project_name}: "
                f"Status={review_result['compliance_status']}, "
                f"Completeness={review_result['completeness_score']}%, "
                f"Flagged={review_result['flagged_for_review']}"
            )
            
            # Log any required revisions
            if review_result['required_revisions']:
                logger.warning(
                    f"Required revisions for {project.project_name}: "
                    f"{len(review_result['required_revisions'])} issues identified"
                )
                for i, revision in enumerate(review_result['required_revisions'][:3], 1):
                    logger.warning(f"  {i}. {revision}")
            
            return review_result
            
        except APIConnectionError as e:
            logger.error(
                f"You.com Express Agent API failed during compliance review "
                f"for project {project.project_name}: {e.message}"
            )
            raise
        
        except Exception as e:
            error_msg = (
                f"Unexpected error reviewing narrative for {project.project_name}: "
                f"{str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            raise APIConnectionError(
                message=error_msg,
                api_name="You.com Express Agent API",
                endpoint="/v1/agents/runs",
                details={"error": str(e), "project": project.project_name}
            )
    
    def _parse_compliance_review(
        self,
        review_text: str,
        project: QualifiedProject
    ) -> Dict[str, Any]:
        """
        Parse compliance review response from You.com Express Agent.
        
        Extracts structured data from the review text including compliance status,
        completeness score, missing elements, recommendations, and risk assessment.
        
        Args:
            review_text: The review text from You.com Express Agent
            project: QualifiedProject object for context
        
        Returns:
            Dictionary with parsed review data
        """
        import re
        
        logger.debug(f"Parsing compliance review for {project.project_name}")
        
        # Initialize result with defaults
        result = {
            'compliance_status': 'Unknown',
            'completeness_score': 0,
            'missing_elements': [],
            'strengths': [],
            'recommendations': [],
            'risk_assessment': '',
            'required_revisions': [],
            'flagged_for_review': False,
            'review_summary': '',
            'raw_review': review_text
        }
        
        # Extract compliance status
        status_patterns = [
            r'Overall Compliance Status[:\s]+([^\n]+)',
            r'Compliance Status[:\s]+([^\n]+)',
            r'Status[:\s]+(Compliant|Needs Revision|Non-Compliant)',
        ]
        for pattern in status_patterns:
            match = re.search(pattern, review_text, re.IGNORECASE)
            if match:
                status = match.group(1).strip()
                # Normalize status
                if 'compliant' in status.lower() and 'non' not in status.lower():
                    result['compliance_status'] = 'Compliant'
                elif 'needs revision' in status.lower() or 'revision' in status.lower():
                    result['compliance_status'] = 'Needs Revision'
                elif 'non-compliant' in status.lower() or 'non compliant' in status.lower():
                    result['compliance_status'] = 'Non-Compliant'
                else:
                    result['compliance_status'] = status
                break
        
        # Extract completeness score
        score_patterns = [
            r'\*\*Completeness Score[:\s]*\*\*[:\s]*(\d+(?:\.\d+)?)\s*%',
            r'Completeness Score[:\s]+(\d+(?:\.\d+)?)\s*%?',
            r'Score[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s+complete',
        ]
        for pattern in score_patterns:
            match = re.search(pattern, review_text, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                # If score is > 100, it might be a different metric
                if score <= 100:
                    result['completeness_score'] = int(score)
                    break
        
        # Extract missing elements
        missing_section = re.search(
            r'\*\*Missing or Weak Elements[:\s]*\*\*[:\s]*\n(.*?)(?=\n\*\*|\n\n[A-Z]|\Z)',
            review_text,
            re.DOTALL | re.IGNORECASE
        )
        if missing_section:
            missing_text = missing_section.group(1)
            # Extract bullet points or numbered items
            missing_items = re.findall(r'^[-•*]\s*(.+?)$', missing_text, re.MULTILINE)
            if not missing_items:
                missing_items = re.findall(r'^\d+\.\s*(.+?)$', missing_text, re.MULTILINE)
            result['missing_elements'] = [item.strip() for item in missing_items if item.strip() and item.strip().lower() != 'none identified']
        
        # Extract strengths
        strengths_section = re.search(
            r'\*\*Strengths[:\s]*\*\*[:\s]*\n(.*?)(?=\n\*\*|\n\n[A-Z]|\Z)',
            review_text,
            re.DOTALL | re.IGNORECASE
        )
        if strengths_section:
            strengths_text = strengths_section.group(1)
            strength_items = re.findall(r'^[-•*]\s*(.+?)$', strengths_text, re.MULTILINE)
            if not strength_items:
                strength_items = re.findall(r'^\d+\.\s*(.+?)$', strengths_text, re.MULTILINE)
            result['strengths'] = [item.strip() for item in strength_items if item.strip() and item.strip().lower() != 'none identified']
        
        # Extract recommendations
        recommendations_section = re.search(
            r'\*\*(?:Specific )?Recommendations[:\s]*\*\*[:\s]*\n(.*?)(?=\n\*\*|\n\n[A-Z]|\Z)',
            review_text,
            re.DOTALL | re.IGNORECASE
        )
        if recommendations_section:
            rec_text = recommendations_section.group(1)
            rec_items = re.findall(r'^[-•*]\s*(.+?)$', rec_text, re.MULTILINE)
            if not rec_items:
                rec_items = re.findall(r'^\d+\.\s*(.+?)$', rec_text, re.MULTILINE)
            result['recommendations'] = [item.strip() for item in rec_items if item.strip() and item.strip().lower() != 'none']
        
        # Extract risk assessment
        risk_section = re.search(
            r'\*\*Risk Assessment[:\s]*\*\*[:\s]*\n(.*?)(?=\n\*\*|\n\n[A-Z]|\Z)',
            review_text,
            re.DOTALL | re.IGNORECASE
        )
        if risk_section:
            result['risk_assessment'] = risk_section.group(1).strip()
        
        # Extract required revisions
        revisions_section = re.search(
            r'\*\*Required Revisions[:\s]*\*\*[:\s]*\n(.*?)(?=\n\*\*|\Z)',
            review_text,
            re.DOTALL | re.IGNORECASE
        )
        if revisions_section:
            rev_text = revisions_section.group(1)
            rev_items = re.findall(r'^[-•*]\s*(.+?)$', rev_text, re.MULTILINE)
            if not rev_items:
                rev_items = re.findall(r'^\d+\.\s*(.+?)$', rev_text, re.MULTILINE)
            result['required_revisions'] = [item.strip() for item in rev_items if item.strip() and item.strip().lower() not in ['none required', 'none']]
        
        # Determine if narrative should be flagged for review
        # Flag if:
        # - Status is "Needs Revision" or "Non-Compliant"
        # - Completeness score is below 70%
        # - There are required revisions
        # - Project confidence score is already low (< 0.7)
        if (
            result['compliance_status'] in ['Needs Revision', 'Non-Compliant'] or
            result['completeness_score'] < 70 or
            len(result['required_revisions']) > 0 or
            project.confidence_score < 0.7
        ):
            result['flagged_for_review'] = True
        
        # Create review summary
        summary_parts = []
        summary_parts.append(f"Status: {result['compliance_status']}")
        summary_parts.append(f"Completeness: {result['completeness_score']}%")
        
        if result['missing_elements']:
            summary_parts.append(f"{len(result['missing_elements'])} missing elements")
        
        if result['required_revisions']:
            summary_parts.append(f"{len(result['required_revisions'])} required revisions")
        
        if result['flagged_for_review']:
            summary_parts.append("FLAGGED FOR MANUAL REVIEW")
        
        result['review_summary'] = " | ".join(summary_parts)
        
        logger.debug(
            f"Parsed compliance review: {result['review_summary']}"
        )
        
        return result
    
    def _aggregate_report_data(
        self,
        qualified_projects: List[QualifiedProject],
        tax_year: int
    ) -> Dict[str, Any]:
        """
        Aggregate all qualified project data for final report generation.
        
        This method uses Pandas to aggregate qualified hours, costs, and other metrics
        across all projects. It calculates summary statistics including total hours,
        total costs, estimated tax credit, average confidence score, and project count.
        The aggregated data is structured for use in PDF report generation.
        
        The method performs the following aggregations:
        1. Total qualified hours across all projects
        2. Total qualified costs across all projects
        3. Estimated R&D tax credit (20% of qualified costs)
        4. Average confidence score across all projects
        5. Project count and breakdown by confidence level
        6. Cost breakdown by project
        7. Summary statistics for audit reporting
        
        Args:
            qualified_projects: List of QualifiedProject objects from Qualification Agent
            tax_year: Tax year for the report
        
        Returns:
            Dictionary containing aggregated data with the following keys:
                - total_qualified_hours: Sum of all qualified hours
                - total_qualified_cost: Sum of all qualified costs
                - estimated_credit: Estimated R&D tax credit (20% of qualified costs)
                - average_confidence: Mean confidence score across all projects
                - project_count: Total number of qualified projects
                - high_confidence_count: Number of projects with confidence >= 0.8
                - medium_confidence_count: Number of projects with confidence 0.7-0.8
                - low_confidence_count: Number of projects with confidence < 0.7
                - flagged_count: Number of projects flagged for review
                - projects_df: Pandas DataFrame with per-project details
                - summary_stats: Dictionary with additional statistical measures
                - tax_year: Tax year for the report
        
        Raises:
            ValueError: If qualified_projects is empty or invalid
        
        Example:
            >>> agent = AuditTrailAgent(youcom_client=..., glm_reasoner=...)
            >>> aggregated = agent._aggregate_report_data(
            ...     qualified_projects=projects,
            ...     tax_year=2024
            ... )
            >>> print(f"Total credit: ${aggregated['estimated_credit']:,.2f}")
            >>> print(f"Average confidence: {aggregated['average_confidence']:.2%}")
            >>> print(f"Projects flagged: {aggregated['flagged_count']}")
        
        Requirements: 3.3, 4.4
        """
        import pandas as pd
        import numpy as np
        
        logger.info(
            f"Starting data aggregation for {len(qualified_projects)} qualified projects "
            f"(tax year: {tax_year})"
        )
        
        # Validate inputs
        if not qualified_projects:
            raise ValueError("qualified_projects cannot be empty")
        
        if tax_year < 2000 or tax_year > 2100:
            raise ValueError(f"Invalid tax_year: {tax_year}")
        
        # Convert qualified projects to DataFrame for efficient aggregation
        project_data = []
        for project in qualified_projects:
            project_data.append({
                'project_name': project.project_name,
                'qualified_hours': project.qualified_hours,
                'qualified_cost': project.qualified_cost,
                'confidence_score': project.confidence_score,
                'qualification_percentage': project.qualification_percentage,
                'flagged_for_review': project.flagged_for_review,
                'irs_source': project.irs_source,
                'reasoning_length': len(project.reasoning),
                'citation_length': len(project.supporting_citation)
            })
        
        projects_df = pd.DataFrame(project_data)
        
        logger.info(
            f"Created projects DataFrame with {len(projects_df)} records "
            f"and {len(projects_df.columns)} columns"
        )
        
        # Calculate total qualified hours
        total_qualified_hours = projects_df['qualified_hours'].sum()
        
        # Calculate total qualified cost
        total_qualified_cost = projects_df['qualified_cost'].sum()
        
        # Calculate estimated R&D tax credit (20% of qualified costs)
        # This is the standard federal R&D tax credit rate
        estimated_credit = total_qualified_cost * 0.20
        
        # Calculate average confidence score
        average_confidence = projects_df['confidence_score'].mean()
        
        # Count total projects
        project_count = len(projects_df)
        
        # Count projects by confidence level
        high_confidence_count = len(projects_df[projects_df['confidence_score'] >= 0.8])
        medium_confidence_count = len(
            projects_df[
                (projects_df['confidence_score'] >= 0.7) & 
                (projects_df['confidence_score'] < 0.8)
            ]
        )
        low_confidence_count = len(projects_df[projects_df['confidence_score'] < 0.7])
        
        # Count flagged projects
        flagged_count = projects_df['flagged_for_review'].sum()
        
        logger.info(
            f"Confidence distribution: "
            f"High (>=0.8): {high_confidence_count}, "
            f"Medium (0.7-0.8): {medium_confidence_count}, "
            f"Low (<0.7): {low_confidence_count}"
        )
        
        # Calculate additional summary statistics
        summary_stats = {
            'min_confidence': float(projects_df['confidence_score'].min()),
            'max_confidence': float(projects_df['confidence_score'].max()),
            'median_confidence': float(projects_df['confidence_score'].median()),
            'std_confidence': float(projects_df['confidence_score'].std()),
            'min_qualified_hours': float(projects_df['qualified_hours'].min()),
            'max_qualified_hours': float(projects_df['qualified_hours'].max()),
            'median_qualified_hours': float(projects_df['qualified_hours'].median()),
            'min_qualified_cost': float(projects_df['qualified_cost'].min()),
            'max_qualified_cost': float(projects_df['qualified_cost'].max()),
            'median_qualified_cost': float(projects_df['qualified_cost'].median()),
            'avg_qualification_percentage': float(projects_df['qualification_percentage'].mean()),
            'min_qualification_percentage': float(projects_df['qualification_percentage'].min()),
            'max_qualification_percentage': float(projects_df['qualification_percentage'].max())
        }
        
        # Sort projects by qualified cost (descending) for report presentation
        projects_df_sorted = projects_df.sort_values(
            'qualified_cost',
            ascending=False
        ).reset_index(drop=True)
        
        # Calculate cumulative percentages for top projects analysis
        projects_df_sorted['cumulative_cost'] = projects_df_sorted['qualified_cost'].cumsum()
        projects_df_sorted['cumulative_percentage'] = (
            projects_df_sorted['cumulative_cost'] / total_qualified_cost * 100
        )
        
        # Identify top projects (those contributing to 80% of total cost)
        top_projects_80_mask = projects_df_sorted['cumulative_percentage'] <= 80
        top_projects_80_count = top_projects_80_mask.sum()
        
        logger.info(
            f"Top {top_projects_80_count} projects account for 80% of total qualified costs"
        )
        
        # Build aggregated data dictionary
        aggregated_data = {
            # Core totals
            'total_qualified_hours': float(total_qualified_hours),
            'total_qualified_cost': float(total_qualified_cost),
            'estimated_credit': float(estimated_credit),
            
            # Confidence metrics
            'average_confidence': float(average_confidence),
            'high_confidence_count': int(high_confidence_count),
            'medium_confidence_count': int(medium_confidence_count),
            'low_confidence_count': int(low_confidence_count),
            
            # Project counts
            'project_count': int(project_count),
            'flagged_count': int(flagged_count),
            'top_projects_80_count': int(top_projects_80_count),
            
            # DataFrames for detailed reporting
            'projects_df': projects_df_sorted,
            
            # Summary statistics
            'summary_stats': summary_stats,
            
            # Metadata
            'tax_year': tax_year,
            'aggregation_timestamp': datetime.now().isoformat()
        }
        
        # Log summary of aggregation
        logger.info(
            f"Data aggregation complete:\n"
            f"  Total Projects: {project_count}\n"
            f"  Total Qualified Hours: {total_qualified_hours:,.2f}\n"
            f"  Total Qualified Cost: ${total_qualified_cost:,.2f}\n"
            f"  Estimated Credit (20%): ${estimated_credit:,.2f}\n"
            f"  Average Confidence: {average_confidence:.2%}\n"
            f"  Flagged for Review: {flagged_count}\n"
            f"  High Confidence (>=0.8): {high_confidence_count}\n"
            f"  Medium Confidence (0.7-0.8): {medium_confidence_count}\n"
            f"  Low Confidence (<0.7): {low_confidence_count}"
        )
        
        # Log warning if many projects are flagged
        if flagged_count > 0:
            flagged_percentage = (flagged_count / project_count) * 100
            if flagged_percentage > 30:
                logger.warning(
                    f"{flagged_count} projects ({flagged_percentage:.1f}%) are flagged for review. "
                    f"Consider manual review before finalizing the report."
                )
            else:
                logger.info(
                    f"{flagged_count} projects ({flagged_percentage:.1f}%) flagged for review "
                    f"(within acceptable range)"
                )
        
        # Log warning if average confidence is low
        if average_confidence < 0.75:
            logger.warning(
                f"Average confidence score is {average_confidence:.2%}, which is below 75%. "
                f"Consider additional documentation or expert review."
            )
        
        return aggregated_data
