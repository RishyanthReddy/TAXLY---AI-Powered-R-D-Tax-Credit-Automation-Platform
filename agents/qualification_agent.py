"""
Qualification Agent for R&D Tax Credit Automation.

This agent is responsible for determining which activities and costs qualify for
R&D tax credits using IRS guidance from the RAG system, You.com APIs for recent
guidance and expert reasoning, and GLM 4.5 Air for decision-making.

The agent uses PydanticAI for structured agent workflows and maintains state
throughout the qualification process.

Requirements: 2.1, 2.2, 2.3, 8.1
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from tools.rd_knowledge_tool import RD_Knowledge_Tool
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from models.financial_models import EmployeeTimeEntry, ProjectCost
from models.tax_models import QualifiedProject, RAGContext
from models.websocket_models import StatusUpdateMessage, AgentStage, AgentStatus
from utils.logger import get_qualification_logger
from utils.exceptions import RAGRetrievalError, APIConnectionError

# Get logger for qualification agent
logger = get_qualification_logger()


class QualificationState(BaseModel):
    """
    State model for tracking Qualification Agent progress.
    
    This model maintains the current state of the qualification workflow,
    including progress tracking, qualified projects, and error information.
    
    Attributes:
        stage: Current stage of qualification (initializing, filtering_projects, etc.)
        status: Current execution status (pending, in_progress, completed, error)
        projects_to_qualify: Total number of projects to qualify
        projects_qualified: Number of projects successfully qualified
        projects_flagged: Number of projects flagged for review (low confidence)
        current_project: Name of project currently being qualified
        start_time: Timestamp when qualification started
        end_time: Timestamp when qualification completed (None if in progress)
        error_message: Error message if qualification failed
    """
    
    stage: str = Field(
        default="initializing",
        description="Current stage of qualification workflow"
    )
    
    status: AgentStatus = Field(
        default=AgentStatus.PENDING,
        description="Current execution status"
    )
    
    projects_to_qualify: int = Field(
        default=0,
        description="Total number of projects to qualify"
    )
    
    projects_qualified: int = Field(
        default=0,
        description="Number of projects successfully qualified"
    )
    
    projects_flagged: int = Field(
        default=0,
        description="Number of projects flagged for review (low confidence)"
    )
    
    current_project: Optional[str] = Field(
        default=None,
        description="Name of project currently being qualified"
    )
    
    start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when qualification started"
    )
    
    end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when qualification completed"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if qualification failed"
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
                details += f"Qualifying project '{self.current_project}' ({self.projects_qualified}/{self.projects_to_qualify})"
            else:
                details += f"Qualified {self.projects_qualified}/{self.projects_to_qualify} projects"
        elif self.status == AgentStatus.COMPLETED:
            details += (
                f"Successfully qualified {self.projects_qualified} projects "
                f"({self.projects_flagged} flagged for review)"
            )
        elif self.status == AgentStatus.ERROR:
            details += f"Error: {self.error_message}"
        else:
            details += "Waiting to start"
        
        return StatusUpdateMessage(
            stage=AgentStage.QUALIFICATION,
            status=self.status,
            details=details,
            timestamp=datetime.now()
        )


class QualificationResult(BaseModel):
    """
    Result model for Qualification Agent execution.
    
    Contains all qualified projects along with metadata about the
    qualification process.
    
    Attributes:
        qualified_projects: List of QualifiedProject objects
        total_qualified_hours: Sum of all qualified hours
        total_qualified_cost: Sum of all qualified costs
        estimated_credit: Estimated tax credit (20% of qualified costs)
        average_confidence: Average confidence score across all projects
        flagged_projects: List of project names flagged for review
        execution_time_seconds: Total execution time
        summary: Human-readable summary of qualification results
    """
    
    qualified_projects: List[QualifiedProject] = Field(
        default_factory=list,
        description="List of qualified projects"
    )
    
    total_qualified_hours: float = Field(
        default=0.0,
        description="Sum of all qualified hours"
    )
    
    total_qualified_cost: float = Field(
        default=0.0,
        description="Sum of all qualified costs"
    )
    
    estimated_credit: float = Field(
        default=0.0,
        description="Estimated tax credit (20% of qualified costs)"
    )
    
    average_confidence: float = Field(
        default=0.0,
        description="Average confidence score across all projects"
    )
    
    flagged_projects: List[str] = Field(
        default_factory=list,
        description="List of project names flagged for review"
    )
    
    execution_time_seconds: float = Field(
        default=0.0,
        description="Total execution time in seconds"
    )
    
    summary: str = Field(
        default="",
        description="Human-readable summary of qualification results"
    )


class QualificationAgent:
    """
    PydanticAI-based agent for R&D qualification using RAG and You.com APIs.
    
    This agent determines which projects and costs qualify for R&D tax credits by:
    1. Filtering projects marked as R&D by the user
    2. Querying the RAG system (local IRS documents) for relevant guidance
    3. Using You.com Search/News APIs for recent IRS rulings
    4. Using GLM 4.5 Air via OpenRouter for qualification reasoning
    5. Generating confidence scores and IRS citations
    
    The agent maintains state throughout execution and can send real-time
    status updates via WebSocket for frontend visualization.
    
    Example:
        >>> from tools.rd_knowledge_tool import RD_Knowledge_Tool
        >>> from tools.you_com_client import YouComClient
        >>> from tools.glm_reasoner import GLMReasoner
        >>> 
        >>> # Initialize agent with tools
        >>> rag_tool = RD_Knowledge_Tool()
        >>> youcom_client = YouComClient(api_key="...")
        >>> glm_reasoner = GLMReasoner(api_key="...")
        >>> 
        >>> agent = QualificationAgent(
        ...     rag_tool=rag_tool,
        ...     youcom_client=youcom_client,
        ...     glm_reasoner=glm_reasoner
        ... )
        >>> 
        >>> # Run qualification
        >>> result = agent.run(
        ...     time_entries=time_entries,
        ...     costs=costs
        ... )
        >>> 
        >>> print(f"Qualified {len(result.qualified_projects)} projects")
        >>> print(f"Estimated credit: ${result.estimated_credit:,.2f}")
    """
    
    def __init__(
        self,
        rag_tool: RD_Knowledge_Tool,
        youcom_client: YouComClient,
        glm_reasoner: GLMReasoner,
        status_callback: Optional[callable] = None
    ):
        """
        Initialize Qualification Agent.
        
        Args:
            rag_tool: Initialized RD_Knowledge_Tool for querying local IRS documents
            youcom_client: Initialized YouComClient for Search/News APIs
            glm_reasoner: Initialized GLMReasoner for GLM 4.5 Air reasoning via OpenRouter
            status_callback: Optional callback function for status updates
                            (receives StatusUpdateMessage objects)
        
        Raises:
            ValueError: If any required tool is None
        """
        if rag_tool is None:
            raise ValueError("rag_tool cannot be None")
        if youcom_client is None:
            raise ValueError("youcom_client cannot be None")
        if glm_reasoner is None:
            raise ValueError("glm_reasoner cannot be None")
        
        self.rag_tool = rag_tool
        self.youcom_client = youcom_client
        self.glm_reasoner = glm_reasoner
        self.status_callback = status_callback
        
        # Initialize agent state
        self.state = QualificationState()
        
        logger.info(
            "Initialized Qualification Agent with RD_Knowledge_Tool, "
            "YouComClient, and GLMReasoner (GLM 4.5 Air via OpenRouter)"
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
    
    def run(
        self,
        time_entries: List[EmployeeTimeEntry],
        costs: List[ProjectCost],
        tax_year: Optional[int] = None
    ) -> QualificationResult:
        """
        Run the qualification workflow.
        
        This method orchestrates the complete qualification process:
        1. Filter projects marked as R&D (is_rd_classified=True)
        2. Group entries by project
        3. For each project:
           a. Query RAG system for relevant IRS guidance
           b. Search You.com for recent IRS rulings (if tax_year provided)
           c. Use GLM 4.5 Air to determine qualification
           d. Generate confidence scores and citations
        4. Flag low-confidence projects for review
        
        Args:
            time_entries: List of EmployeeTimeEntry objects
            costs: List of ProjectCost objects
            tax_year: Optional tax year for checking recent IRS guidance
        
        Returns:
            QualificationResult with qualified projects and metadata
        
        Raises:
            ValueError: If inputs are invalid
            RAGRetrievalError: If RAG system fails
            APIConnectionError: If You.com or OpenRouter APIs fail
        
        Example:
            >>> agent = QualificationAgent(rag_tool=..., youcom_client=..., glm_reasoner=...)
            >>> result = agent.run(
            ...     time_entries=time_entries,
            ...     costs=costs,
            ...     tax_year=2024
            ... )
        """
        # Validate inputs
        if not time_entries:
            raise ValueError("time_entries cannot be empty")
        
        # Initialize result
        result = QualificationResult()
        
        # Record start time
        self.state.start_time = datetime.now()
        self.state.status = AgentStatus.IN_PROGRESS
        
        logger.info(
            f"Starting qualification for {len(time_entries)} time entries "
            f"and {len(costs)} costs"
        )
        
        try:
            # Stage 1: Filter R&D projects
            self._update_status(
                stage="filtering_projects",
                status=AgentStatus.IN_PROGRESS
            )
            
            rd_projects = self._filter_rd_projects(time_entries, costs)
            self.state.projects_to_qualify = len(rd_projects)
            
            logger.info(
                f"Filtered {len(rd_projects)} R&D projects from "
                f"{len(set(e.project_name for e in time_entries))} total projects"
            )
            
            if not rd_projects:
                logger.warning("No projects marked as R&D - returning empty result")
                
                self.state.end_time = datetime.now()
                execution_time = (self.state.end_time - self.state.start_time).total_seconds()
                
                result.execution_time_seconds = execution_time
                result.summary = "No projects marked as R&D for qualification"
                
                self._update_status(
                    stage="completed",
                    status=AgentStatus.COMPLETED
                )
                
                return result
            
            # Stage 2: Qualify each project with concurrent processing
            self._update_status(
                stage="qualifying_projects",
                status=AgentStatus.IN_PROGRESS
            )
            
            logger.info(f"Starting batch qualification for {len(rd_projects)} projects")
            
            # Process projects concurrently with rate limiting
            qualified_projects = self._process_projects_batch(
                rd_projects=rd_projects,
                tax_year=tax_year
            )
            
            # Stage 3: Flag low-confidence projects
            if qualified_projects:
                self._update_status(
                    stage="flagging_low_confidence",
                    status=AgentStatus.IN_PROGRESS
                )
                
                logger.info("Flagging low-confidence projects for review")
                
                flagging_result = self._flag_low_confidence(
                    qualified_projects=qualified_projects
                )
                
                # Log flagging results
                logger.info(f"Flagging complete: {flagging_result['summary']}")
                
                if flagging_result['flagged_count'] > 0:
                    logger.warning(
                        f"{flagging_result['flagged_count']} projects flagged for review"
                    )
                    
                    for recommendation in flagging_result['recommendations']:
                        logger.warning(f"Recommendation: {recommendation}")
            
            # Stage 4: Check for recent IRS guidance (if tax_year provided)
            if tax_year and qualified_projects:
                self._update_status(
                    stage="checking_recent_guidance",
                    status=AgentStatus.IN_PROGRESS
                )
                
                logger.info(f"Checking for recent IRS guidance for tax year {tax_year}")
                
                guidance_check = self._check_recent_guidance(
                    tax_year=tax_year,
                    qualified_projects=qualified_projects
                )
                
                # Log guidance check results
                if guidance_check['has_new_guidance']:
                    logger.warning(
                        f"New IRS guidance found: {guidance_check['guidance_summary']}"
                    )
                    
                    if guidance_check['affected_projects']:
                        logger.warning(
                            f"{len(guidance_check['affected_projects'])} projects may be "
                            f"affected by new guidance: {', '.join(guidance_check['affected_projects'][:5])}"
                        )
                else:
                    logger.info("No recent IRS guidance found")
            
            # Record end time and calculate execution time
            self.state.end_time = datetime.now()
            execution_time = (self.state.end_time - self.state.start_time).total_seconds()
            
            # Build result
            result.qualified_projects = qualified_projects
            result.total_qualified_hours = sum(p.qualified_hours for p in qualified_projects)
            result.total_qualified_cost = sum(p.qualified_cost for p in qualified_projects)
            result.estimated_credit = result.total_qualified_cost * 0.20  # 20% credit rate
            
            if qualified_projects:
                result.average_confidence = sum(
                    p.confidence_score for p in qualified_projects
                ) / len(qualified_projects)
                result.flagged_projects = [
                    p.project_name for p in qualified_projects if p.flagged_for_review
                ]
            
            result.execution_time_seconds = execution_time
            
            # Build summary including guidance check results
            summary_parts = [
                f"Successfully qualified {len(qualified_projects)} projects"
            ]
            
            if tax_year and qualified_projects:
                if guidance_check['has_new_guidance']:
                    summary_parts.append(
                        f"Found recent IRS guidance for {tax_year}"
                    )
                    if guidance_check['affected_projects']:
                        summary_parts.append(
                            f"{len(guidance_check['affected_projects'])} projects may require review"
                        )
                else:
                    summary_parts.append(
                        f"No recent IRS guidance found for {tax_year}"
                    )
            
            result.summary = ". ".join(summary_parts) + "."
            
            # Update final status
            self._update_status(
                stage="completed",
                status=AgentStatus.COMPLETED
            )
            
            logger.info(f"Qualification complete: {result.summary}")
            
            return result
        
        except RAGRetrievalError as e:
            # Handle RAG retrieval errors
            error_msg = f"RAG retrieval failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            self._update_status(
                stage="error",
                status=AgentStatus.ERROR,
                error_message=error_msg
            )
            
            raise
        
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
            error_msg = f"Unexpected error during qualification: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            self._update_status(
                stage="error",
                status=AgentStatus.ERROR,
                error_message=error_msg
            )
            
            raise
    
    def _filter_rd_projects(
        self,
        time_entries: List[EmployeeTimeEntry],
        costs: List[ProjectCost]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Filter and group projects marked as R&D.
        
        This method:
        1. Filters time entries where is_rd_classified=True
        2. Filters costs where is_rd_classified=True
        3. Groups entries by project_name
        4. Aggregates hours and costs per project
        
        Args:
            time_entries: List of all time entries
            costs: List of all costs
        
        Returns:
            Dictionary mapping project_name to project data:
            {
                'project_name': {
                    'time_entries': List[EmployeeTimeEntry],
                    'costs': List[ProjectCost],
                    'total_hours': float,
                    'total_cost': float
                }
            }
        
        Requirements: 2.1
        """
        logger.info("Filtering R&D projects...")
        
        # Filter R&D entries
        rd_time_entries = [e for e in time_entries if e.is_rd_classified]
        rd_costs = [c for c in costs if c.is_rd_classified]
        
        logger.info(
            f"Filtered {len(rd_time_entries)} R&D time entries and "
            f"{len(rd_costs)} R&D costs"
        )
        
        # Group by project
        projects: Dict[str, Dict[str, Any]] = {}
        
        # Add time entries to projects
        for entry in rd_time_entries:
            project_name = entry.project_name
            
            if project_name not in projects:
                projects[project_name] = {
                    'time_entries': [],
                    'costs': [],
                    'total_hours': 0.0,
                    'total_cost': 0.0
                }
            
            projects[project_name]['time_entries'].append(entry)
            projects[project_name]['total_hours'] += entry.hours_spent
        
        # Add costs to projects
        for cost in rd_costs:
            project_name = cost.project_name
            
            if project_name not in projects:
                projects[project_name] = {
                    'time_entries': [],
                    'costs': [],
                    'total_hours': 0.0,
                    'total_cost': 0.0
                }
            
            projects[project_name]['costs'].append(cost)
            projects[project_name]['total_cost'] += cost.amount
        
        # Log project summary
        for project_name, data in projects.items():
            logger.info(
                f"Project '{project_name}': "
                f"{len(data['time_entries'])} time entries ({data['total_hours']:.1f} hours), "
                f"{len(data['costs'])} costs (${data['total_cost']:,.2f})"
            )
        
        logger.info(f"Grouped {len(projects)} R&D projects")
        
        return projects
    
    def _qualify_project(
        self,
        project_name: str,
        project_data: Dict[str, Any],
        tax_year: Optional[int] = None
    ) -> QualifiedProject:
        """
        Qualify a single project using RAG and You.com Agent API.
        
        This method implements the core qualification workflow:
        1. Query RAG system with project description for IRS guidance
        2. Format RAG context for LLM prompt
        3. Call You.com Agent API with context and project data
        4. Parse qualification response (percentage, confidence, reasoning, citations)
        5. Create and return QualifiedProject object
        
        Args:
            project_name: Name of the project to qualify
            project_data: Dictionary containing:
                - time_entries: List[EmployeeTimeEntry]
                - costs: List[ProjectCost]
                - total_hours: float
                - total_cost: float
            tax_year: Optional tax year for checking recent IRS guidance
        
        Returns:
            QualifiedProject object with qualification results
        
        Raises:
            RAGRetrievalError: If RAG system fails to retrieve context
            APIConnectionError: If You.com Agent API fails
            ValueError: If project data is invalid or response cannot be parsed
        
        Requirements: 2.2, 2.3, 2.4
        
        Example:
            >>> project_data = {
            ...     'time_entries': [entry1, entry2],
            ...     'costs': [cost1, cost2],
            ...     'total_hours': 120.5,
            ...     'total_cost': 15000.00
            ... }
            >>> qualified = agent._qualify_project(
            ...     project_name="API Optimization",
            ...     project_data=project_data,
            ...     tax_year=2024
            ... )
        """
        from tools.prompt_templates import populate_rag_inference_prompt
        
        logger.info(f"Qualifying project: {project_name}")
        
        # Validate project data
        if not project_data:
            raise ValueError(f"Project data cannot be empty for project '{project_name}'")
        
        if 'total_hours' not in project_data or 'total_cost' not in project_data:
            raise ValueError(
                f"Project data must contain 'total_hours' and 'total_cost' for project '{project_name}'"
            )
        
        # Extract project information
        total_hours = project_data['total_hours']
        total_cost = project_data['total_cost']
        time_entries = project_data.get('time_entries', [])
        
        # Build project description from time entries
        # Collect unique task descriptions
        task_descriptions = set()
        for entry in time_entries:
            if entry.task_description:
                task_descriptions.add(entry.task_description)
        
        # Create project description
        if task_descriptions:
            project_description = f"Project involving: {', '.join(list(task_descriptions)[:5])}"
        else:
            project_description = f"R&D project: {project_name}"
        
        # Create technical activities summary
        technical_activities = "\n".join([
            f"- {desc}" for desc in list(task_descriptions)[:10]
        ]) if task_descriptions else "- Software development and technical research"
        
        logger.info(
            f"Project '{project_name}': {total_hours:.1f} hours, ${total_cost:,.2f}, "
            f"{len(task_descriptions)} unique activities"
        )
        
        # Step 1: Query RAG system for relevant IRS guidance
        logger.info(f"Querying RAG system for project '{project_name}'")
        
        try:
            # Create query for RAG system
            rag_query = (
                f"R&D tax credit qualification for {project_name}. "
                f"Project involves: {project_description}. "
                f"What IRS guidance applies to determine if this qualifies as qualified research?"
            )
            
            # Query RAG system (uses GLM 4.5 Air for RAG inference)
            rag_context = self.rag_tool.query(
                question=rag_query,
                top_k=3,  # Get top 3 most relevant chunks
                enable_query_expansion=True,
                enable_query_rewriting=True,
                enable_reranking=True
            )
            
            logger.info(
                f"RAG retrieval successful: {rag_context.chunk_count} chunks retrieved "
                f"(avg relevance: {rag_context.average_relevance:.3f})"
            )
            
        except RAGRetrievalError as e:
            logger.error(f"RAG retrieval failed for project '{project_name}': {e}")
            raise
        
        # Step 2: Format RAG context for LLM prompt
        logger.info("Formatting RAG context for LLM prompt")
        
        formatted_rag_context = rag_context.format_for_llm_prompt()
        
        # Step 3: Create prompt with RAG context and project data
        prompt = populate_rag_inference_prompt(
            rag_context=formatted_rag_context,
            project_name=project_name,
            project_description=project_description,
            technical_activities=technical_activities,
            total_hours=total_hours,
            total_cost=total_cost
        )
        
        logger.info(
            f"Created qualification prompt for project '{project_name}' "
            f"(length: {len(prompt)} chars)"
        )
        
        # Step 4: Call You.com Agent API for expert qualification
        logger.info(f"Calling You.com Agent API for project '{project_name}'")
        
        try:
            # Call You.com Agent API with express mode for fast qualification
            agent_response = self.youcom_client.agent_run(
                prompt=prompt,
                agent_mode="express",
                stream=False
            )
            
            # Extract answer text from response
            # Response format: {'output': [{'text': '...', 'type': '...', ...}]}
            if not agent_response or 'output' not in agent_response:
                raise ValueError(
                    f"Invalid agent response format for project '{project_name}': "
                    f"missing 'output' field"
                )
            
            if not agent_response['output'] or len(agent_response['output']) == 0:
                raise ValueError(
                    f"Invalid agent response format for project '{project_name}': "
                    f"empty 'output' list"
                )
            
            # Get the answer text from the first output item
            answer_text = agent_response['output'][0].get('text', '')
            
            if not answer_text:
                raise ValueError(
                    f"Invalid agent response format for project '{project_name}': "
                    f"empty 'text' field"
                )
            
            logger.info(
                f"You.com Agent API call successful for project '{project_name}' "
                f"(response length: {len(answer_text)} chars)"
            )
            
        except APIConnectionError as e:
            logger.error(
                f"You.com Agent API failed for project '{project_name}': {e.message}"
            )
            raise
        
        # Step 5: Parse qualification response
        logger.info(f"Parsing qualification response for project '{project_name}'")
        
        try:
            parsed_response = self.youcom_client._parse_agent_response(answer_text)
            
            logger.info(
                f"Parsed qualification for project '{project_name}': "
                f"{parsed_response['qualification_percentage']}% "
                f"(confidence: {parsed_response['confidence_score']:.2f})"
            )
            
        except ValueError as e:
            logger.error(
                f"Failed to parse agent response for project '{project_name}': {e}"
            )
            raise
        
        # Step 6: Extract IRS citations from RAG context
        # Use the first chunk's source as the primary citation
        irs_source = "IRS Guidance"
        supporting_citation = "Based on IRS guidance from knowledge base"
        
        if rag_context.chunks:
            first_chunk = rag_context.chunks[0]
            irs_source = f"{first_chunk['source']} (Page {first_chunk['page']})"
            supporting_citation = first_chunk['text'][:500]  # First 500 chars
        
        # Add citations from agent response if available
        if parsed_response.get('citations'):
            irs_source += f" | {', '.join(parsed_response['citations'][:2])}"
        
        # Step 7: Calculate qualified hours and costs
        qualification_pct = parsed_response['qualification_percentage'] / 100.0
        qualified_hours = total_hours * qualification_pct
        qualified_cost = total_cost * qualification_pct
        
        logger.info(
            f"Calculated qualified amounts for project '{project_name}': "
            f"{qualified_hours:.1f} hours, ${qualified_cost:,.2f}"
        )
        
        # Step 8: Create QualifiedProject object
        # Handle technical_details - convert string to dict if needed
        technical_details = parsed_response.get('technical_details')
        if technical_details and isinstance(technical_details, str):
            # Convert string to dict format
            technical_details = {'description': technical_details}
        
        qualified_project = QualifiedProject(
            project_name=project_name,
            qualified_hours=qualified_hours,
            qualified_cost=qualified_cost,
            confidence_score=parsed_response['confidence_score'],
            qualification_percentage=parsed_response['qualification_percentage'],
            supporting_citation=supporting_citation,
            reasoning=parsed_response['reasoning'],
            irs_source=irs_source,
            technical_details=technical_details
        )
        
        # Log flagging status
        if qualified_project.flagged_for_review:
            logger.warning(
                f"Project '{project_name}' flagged for review "
                f"(confidence: {qualified_project.confidence_score:.2f} < 0.7)"
            )
        
        logger.info(
            f"Successfully qualified project '{project_name}': "
            f"{qualified_project.qualification_percentage}% qualified, "
            f"confidence: {qualified_project.confidence_score:.2f}, "
            f"flagged: {qualified_project.flagged_for_review}"
        )
        
        return qualified_project
    
    def _process_projects_batch(
        self,
        rd_projects: Dict[str, Dict[str, Any]],
        tax_year: Optional[int] = None
    ) -> List[QualifiedProject]:
        """
        Process all projects with concurrent qualification and rate limiting.
        
        This method implements batch processing with:
        - Concurrent processing using asyncio
        - Rate limiting (max 5 concurrent for You.com API)
        - Progress tracking and status updates
        - Comprehensive error handling and logging
        
        Args:
            rd_projects: Dictionary mapping project_name to project data
            tax_year: Optional tax year for checking recent IRS guidance
        
        Returns:
            List of QualifiedProject objects
        
        Requirements: 2.3
        
        Example:
            >>> rd_projects = {
            ...     'Project A': {'time_entries': [...], 'costs': [...], ...},
            ...     'Project B': {'time_entries': [...], 'costs': [...], ...}
            ... }
            >>> qualified = agent._process_projects_batch(rd_projects, tax_year=2024)
        """
        logger.info(
            f"Starting batch qualification for {len(rd_projects)} projects "
            f"with max 5 concurrent operations"
        )
        
        # Run async batch processing
        qualified_projects = asyncio.run(
            self._qualify_projects_async(rd_projects, tax_year)
        )
        
        logger.info(
            f"Batch qualification complete: {len(qualified_projects)} projects qualified"
        )
        
        return qualified_projects
    
    async def _qualify_projects_async(
        self,
        rd_projects: Dict[str, Dict[str, Any]],
        tax_year: Optional[int] = None
    ) -> List[QualifiedProject]:
        """
        Asynchronously qualify all projects with concurrency control.
        
        This method:
        1. Creates a semaphore to limit concurrent operations (max 5)
        2. Creates async tasks for each project
        3. Processes tasks concurrently with rate limiting
        4. Tracks progress and sends status updates
        5. Handles errors gracefully (continues on individual failures)
        
        Args:
            rd_projects: Dictionary mapping project_name to project data
            tax_year: Optional tax year for checking recent IRS guidance
        
        Returns:
            List of successfully qualified QualifiedProject objects
        """
        # Create semaphore to limit concurrent operations (max 5 for You.com API)
        semaphore = asyncio.Semaphore(5)
        
        # Create tasks for all projects
        tasks = []
        project_names = list(rd_projects.keys())
        
        for project_name in project_names:
            project_data = rd_projects[project_name]
            task = self._qualify_project_with_semaphore(
                semaphore=semaphore,
                project_name=project_name,
                project_data=project_data,
                tax_year=tax_year
            )
            tasks.append(task)
        
        logger.info(f"Created {len(tasks)} async tasks for project qualification")
        
        # Process all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results and log errors
        qualified_projects = []
        
        for i, result in enumerate(results):
            project_name = project_names[i]
            
            if isinstance(result, Exception):
                # Log error but continue processing other projects
                logger.error(
                    f"Failed to qualify project '{project_name}': {result}",
                    exc_info=result
                )
                
                # Update state to track failed project
                # (don't increment projects_qualified)
                
            elif isinstance(result, QualifiedProject):
                # Success - add to results
                qualified_projects.append(result)
                
                # Update state
                self.state.projects_qualified += 1
                
                if result.flagged_for_review:
                    self.state.projects_flagged += 1
                
                # Send progress update
                self._update_status(
                    stage="qualifying_projects",
                    status=AgentStatus.IN_PROGRESS,
                    current_project=project_name
                )
                
                logger.info(
                    f"Progress: {self.state.projects_qualified}/{self.state.projects_to_qualify} "
                    f"projects qualified"
                )
            else:
                # Unexpected result type
                logger.warning(
                    f"Unexpected result type for project '{project_name}': {type(result)}"
                )
        
        logger.info(
            f"Batch processing complete: {len(qualified_projects)} successful, "
            f"{len(results) - len(qualified_projects)} failed"
        )
        
        return qualified_projects
    
    async def _qualify_project_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        project_name: str,
        project_data: Dict[str, Any],
        tax_year: Optional[int] = None
    ) -> QualifiedProject:
        """
        Qualify a single project with semaphore-based rate limiting.
        
        This method wraps the synchronous _qualify_project method with:
        - Semaphore acquisition for rate limiting
        - Async execution in thread pool
        - Proper error propagation
        
        Args:
            semaphore: Asyncio semaphore for concurrency control
            project_name: Name of the project to qualify
            project_data: Dictionary containing project data
            tax_year: Optional tax year for checking recent IRS guidance
        
        Returns:
            QualifiedProject object
        
        Raises:
            Exception: Any exception from _qualify_project is propagated
        """
        async with semaphore:
            logger.info(f"Acquiring semaphore for project '{project_name}'")
            
            # Run synchronous qualification in thread pool
            loop = asyncio.get_event_loop()
            
            try:
                qualified_project = await loop.run_in_executor(
                    None,  # Use default executor
                    self._qualify_project,
                    project_name,
                    project_data,
                    tax_year
                )
                
                logger.info(
                    f"Successfully qualified project '{project_name}' "
                    f"({qualified_project.qualification_percentage}% qualified)"
                )
                
                return qualified_project
                
            except Exception as e:
                logger.error(
                    f"Error qualifying project '{project_name}': {e}",
                    exc_info=True
                )
                raise
    
    def _flag_low_confidence(
        self,
        qualified_projects: List[QualifiedProject]
    ) -> Dict[str, Any]:
        """
        Flag projects with low confidence scores for user review.
        
        This method identifies projects with confidence scores below 0.7 and:
        1. Adds warning messages to flagged projects
        2. Creates a summary of flagged projects
        3. Provides recommendations for additional documentation
        
        Args:
            qualified_projects: List of QualifiedProject objects to check
        
        Returns:
            Dictionary containing:
                - flagged_count: int number of projects flagged
                - flagged_projects: List[Dict] with project details and warnings
                - summary: str human-readable summary
                - recommendations: List[str] of recommended actions
                - average_confidence: float average confidence of flagged projects
        
        Requirements: 6.4
        
        Example:
            >>> flagging_result = agent._flag_low_confidence(qualified_projects)
            >>> if flagging_result['flagged_count'] > 0:
            ...     print(f"Warning: {flagging_result['flagged_count']} projects flagged")
            ...     print(f"Summary: {flagging_result['summary']}")
        """
        logger.info(f"Checking {len(qualified_projects)} projects for low confidence scores")
        
        # Initialize result
        result = {
            'flagged_count': 0,
            'flagged_projects': [],
            'summary': '',
            'recommendations': [],
            'average_confidence': 0.0
        }
        
        # Identify low-confidence projects (confidence < 0.7)
        LOW_CONFIDENCE_THRESHOLD = 0.7
        flagged_projects = []
        
        for project in qualified_projects:
            if project.confidence_score < LOW_CONFIDENCE_THRESHOLD:
                # Determine warning level based on confidence score
                if project.confidence_score < 0.5:
                    warning_level = "CRITICAL"
                    warning_message = (
                        f"Very low confidence ({project.confidence_score:.2f}). "
                        f"This project requires significant additional documentation "
                        f"and may not withstand IRS audit scrutiny."
                    )
                elif project.confidence_score < 0.6:
                    warning_level = "HIGH"
                    warning_message = (
                        f"Low confidence ({project.confidence_score:.2f}). "
                        f"This project needs additional technical documentation "
                        f"to support R&D qualification."
                    )
                else:  # 0.6 <= confidence < 0.7
                    warning_level = "MODERATE"
                    warning_message = (
                        f"Below-threshold confidence ({project.confidence_score:.2f}). "
                        f"Consider gathering additional evidence to strengthen "
                        f"the qualification case."
                    )
                
                # Create flagged project entry
                flagged_entry = {
                    'project_name': project.project_name,
                    'confidence_score': project.confidence_score,
                    'qualification_percentage': project.qualification_percentage,
                    'qualified_cost': project.qualified_cost,
                    'warning_level': warning_level,
                    'warning_message': warning_message,
                    'reasoning': project.reasoning,
                    'irs_source': project.irs_source
                }
                
                flagged_projects.append(flagged_entry)
                
                logger.warning(
                    f"Project '{project.project_name}' flagged for review: "
                    f"{warning_level} - confidence {project.confidence_score:.2f}"
                )
        
        # Update result
        result['flagged_count'] = len(flagged_projects)
        result['flagged_projects'] = flagged_projects
        
        # Calculate average confidence of flagged projects
        if flagged_projects:
            result['average_confidence'] = sum(
                p['confidence_score'] for p in flagged_projects
            ) / len(flagged_projects)
        
        # Build summary
        if result['flagged_count'] == 0:
            result['summary'] = (
                f"All {len(qualified_projects)} qualified projects have confidence "
                f"scores above the 0.7 threshold. No projects flagged for review."
            )
            result['recommendations'].append(
                "All projects meet confidence threshold - proceed with report generation"
            )
            
            logger.info("No projects flagged for review - all above confidence threshold")
        
        else:
            # Count by warning level
            critical_count = sum(1 for p in flagged_projects if p['warning_level'] == 'CRITICAL')
            high_count = sum(1 for p in flagged_projects if p['warning_level'] == 'HIGH')
            moderate_count = sum(1 for p in flagged_projects if p['warning_level'] == 'MODERATE')
            
            # Calculate total qualified cost at risk
            total_flagged_cost = sum(p['qualified_cost'] for p in flagged_projects)
            total_cost = sum(p.qualified_cost for p in qualified_projects)
            cost_percentage = (total_flagged_cost / total_cost * 100) if total_cost > 0 else 0
            
            # Build detailed summary
            summary_parts = [
                f"{result['flagged_count']} of {len(qualified_projects)} projects "
                f"flagged for review (confidence < 0.7)"
            ]
            
            if critical_count > 0:
                summary_parts.append(f"{critical_count} CRITICAL (confidence < 0.5)")
            if high_count > 0:
                summary_parts.append(f"{high_count} HIGH (confidence < 0.6)")
            if moderate_count > 0:
                summary_parts.append(f"{moderate_count} MODERATE (confidence < 0.7)")
            
            summary_parts.append(
                f"Flagged projects represent ${total_flagged_cost:,.2f} "
                f"({cost_percentage:.1f}%) of total qualified costs"
            )
            
            summary_parts.append(
                f"Average confidence of flagged projects: {result['average_confidence']:.2f}"
            )
            
            result['summary'] = ". ".join(summary_parts) + "."
            
            # Generate recommendations based on warning levels
            if critical_count > 0:
                result['recommendations'].append(
                    f"URGENT: {critical_count} project(s) with critical confidence issues - "
                    f"strongly recommend excluding from claim or obtaining expert review"
                )
            
            if high_count > 0:
                result['recommendations'].append(
                    f"{high_count} project(s) need substantial additional documentation - "
                    f"gather detailed technical records, meeting notes, and design documents"
                )
            
            if moderate_count > 0:
                result['recommendations'].append(
                    f"{moderate_count} project(s) need supporting evidence - "
                    f"document technical uncertainties and experimentation processes"
                )
            
            # General recommendations
            result['recommendations'].append(
                "Review IRS four-part test criteria for each flagged project"
            )
            
            result['recommendations'].append(
                "Consider consulting with R&D tax credit specialist for flagged projects"
            )
            
            if cost_percentage > 25:
                result['recommendations'].append(
                    f"WARNING: Flagged projects represent {cost_percentage:.1f}% of total claim - "
                    f"high audit risk if included without additional documentation"
                )
            
            # Log detailed summary
            logger.warning(f"Low-confidence flagging summary: {result['summary']}")
            
            for recommendation in result['recommendations']:
                logger.warning(f"Recommendation: {recommendation}")
        
        return result
    
    def _check_recent_guidance(
        self,
        tax_year: int,
        qualified_projects: List[QualifiedProject]
    ) -> Dict[str, Any]:
        """
        Check for recent IRS guidance using You.com Search API.
        
        This method searches for recent IRS rulings, precedents, and guidance from
        the specified tax year that may affect R&D qualification decisions. It:
        1. Uses You.com Search API to find IRS rulings from current tax year
        2. Parses and summarizes new guidance
        3. Flags projects potentially affected by new rules
        
        Args:
            tax_year: Tax year to search for guidance (e.g., 2024)
            qualified_projects: List of QualifiedProject objects to check against new guidance
        
        Returns:
            Dictionary containing:
                - has_new_guidance: bool indicating if new guidance was found
                - guidance_summary: str summarizing new guidance
                - search_results: List[Dict] of relevant search results
                - affected_projects: List[str] of project names potentially affected
                - recommendations: List[str] of recommended actions
        
        Requirements: 6.1, 6.2
        
        Example:
            >>> guidance_check = agent._check_recent_guidance(
            ...     tax_year=2024,
            ...     qualified_projects=qualified_projects
            ... )
            >>> if guidance_check['has_new_guidance']:
            ...     print(f"New guidance found: {guidance_check['guidance_summary']}")
            ...     print(f"Affected projects: {guidance_check['affected_projects']}")
        """
        logger.info(f"Checking for recent IRS guidance for tax year {tax_year}")
        
        # Initialize result
        result = {
            'has_new_guidance': False,
            'guidance_summary': '',
            'search_results': [],
            'affected_projects': [],
            'recommendations': []
        }
        
        try:
            # Build search query for recent IRS guidance
            search_query = (
                f"IRS R&D tax credit qualified research expenditure "
                f"software development guidance rulings {tax_year}"
            )
            
            logger.info(f"Searching You.com for: '{search_query}'")
            
            # Call You.com Search API with freshness filter for recent results
            search_results = self.youcom_client.search(
                query=search_query,
                count=10,  # Get top 10 results
                freshness="year",  # Only results from past year
                country="US"
            )
            
            logger.info(f"You.com Search returned {len(search_results)} results")
            
            # Also call You.com News API for recent IRS news articles
            news_query = f"IRS R&D tax credit {tax_year} guidance ruling"
            logger.info(f"Searching You.com News for: '{news_query}'")
            
            news_results = self.youcom_client.news(
                query=news_query,
                count=10,  # Get top 10 news results
                freshness="year",  # Only news from past year
                country="US"
            )
            
            logger.info(f"You.com News returned {len(news_results)} results")
            
            # Combine search and news results
            all_results = search_results + news_results
            logger.info(f"Total results from Search + News: {len(all_results)}")
            
            # Filter for IRS-related results from combined search and news
            irs_results = []
            for result_item in all_results:
                url = result_item.get('url', '').lower()
                title = result_item.get('title', '').lower()
                
                # Check if result is from IRS or authoritative tax source
                if any(domain in url for domain in ['irs.gov', 'govinfo.gov', 'federalregister.gov']):
                    irs_results.append(result_item)
                    logger.info(f"Found IRS result: {result_item.get('title', 'Untitled')}")
                elif any(keyword in title for keyword in ['irs', 'internal revenue', 'tax credit', 'qualified research']):
                    irs_results.append(result_item)
                    logger.info(f"Found relevant result: {result_item.get('title', 'Untitled')}")
            
            result['search_results'] = irs_results
            
            # If we found IRS-related results, analyze them
            if irs_results:
                result['has_new_guidance'] = True
                
                # Build summary of new guidance
                guidance_titles = [r.get('title', 'Untitled') for r in irs_results[:5]]
                result['guidance_summary'] = (
                    f"Found {len(irs_results)} recent IRS guidance documents for {tax_year}: "
                    f"{', '.join(guidance_titles[:3])}"
                    + (f" and {len(guidance_titles) - 3} more" if len(guidance_titles) > 3 else "")
                )
                
                logger.info(f"New guidance summary: {result['guidance_summary']}")
                
                # Analyze if any projects might be affected
                # Look for keywords in guidance that relate to project types
                software_keywords = ['software', 'development', 'code', 'programming', 'application']
                research_keywords = ['research', 'experimentation', 'uncertainty', 'qualified']
                
                for result_item in irs_results:
                    description = result_item.get('description', '').lower()
                    snippets = ' '.join(result_item.get('snippets', [])).lower()
                    combined_text = f"{description} {snippets}"
                    
                    # Check if guidance mentions software/development
                    has_software_mention = any(kw in combined_text for kw in software_keywords)
                    has_research_mention = any(kw in combined_text for kw in research_keywords)
                    
                    if has_software_mention and has_research_mention:
                        # This guidance may affect software R&D projects
                        # Flag all projects for review
                        for project in qualified_projects:
                            if project.project_name not in result['affected_projects']:
                                result['affected_projects'].append(project.project_name)
                                logger.warning(
                                    f"Project '{project.project_name}' may be affected by "
                                    f"new guidance: {result_item.get('title', 'Untitled')}"
                                )
                
                # Generate recommendations
                if result['affected_projects']:
                    result['recommendations'].append(
                        f"Review {len(result['affected_projects'])} projects against new IRS guidance"
                    )
                    result['recommendations'].append(
                        "Consider consulting with tax professional for recent guidance interpretation"
                    )
                    result['recommendations'].append(
                        "Document how new guidance was considered in qualification decisions"
                    )
                else:
                    result['recommendations'].append(
                        "New guidance found but does not appear to affect current projects"
                    )
                    result['recommendations'].append(
                        "Monitor IRS website for additional updates"
                    )
                
                logger.info(
                    f"Compliance check complete: {len(result['affected_projects'])} projects "
                    f"potentially affected by new guidance"
                )
            else:
                # No new guidance found
                result['guidance_summary'] = (
                    f"No recent IRS guidance found for {tax_year}. "
                    f"Proceeding with existing knowledge base."
                )
                result['recommendations'].append(
                    "Continue monitoring IRS website for updates"
                )
                
                logger.info("No recent IRS guidance found")
        
        except APIConnectionError as e:
            # Log error but don't fail the entire qualification process
            logger.error(
                f"Failed to check recent guidance via You.com Search API: {e.message}",
                exc_info=True
            )
            
            result['guidance_summary'] = (
                f"Unable to check for recent guidance due to API error. "
                f"Proceeding with existing knowledge base."
            )
            result['recommendations'].append(
                "Manually check IRS website for recent guidance"
            )
        
        except Exception as e:
            # Log unexpected errors
            logger.error(
                f"Unexpected error checking recent guidance: {str(e)}",
                exc_info=True
            )
            
            result['guidance_summary'] = (
                f"Unable to check for recent guidance due to error. "
                f"Proceeding with existing knowledge base."
            )
            result['recommendations'].append(
                "Manually check IRS website for recent guidance"
            )
        
        return result
    
    def get_state(self) -> QualificationState:
        """
        Get current agent state.
        
        Returns:
            Current QualificationState
        """
        return self.state
    
    def reset_state(self):
        """
        Reset agent state to initial values.
        
        Useful for running multiple qualification operations with the same agent instance.
        """
        self.state = QualificationState()
        logger.info("Agent state reset to initial values")
