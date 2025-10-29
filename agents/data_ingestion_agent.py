"""
Data Ingestion Agent for R&D Tax Credit Automation.

This agent is responsible for collecting and standardizing data from external APIs
(Clockify for time tracking and Unified.to for HRIS/payroll data). It orchestrates
data fetching, validation, deduplication, and quality checks.

The agent uses PydanticAI for structured agent workflows and maintains state
throughout the ingestion process.

Requirements: 1.1, 1.2, 8.1
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from tools.api_connectors import ClockifyConnector, UnifiedToConnector
from models.financial_models import EmployeeTimeEntry, ProjectCost
from models.websocket_models import StatusUpdateMessage, AgentStage, AgentStatus
from utils.logger import get_data_ingestion_logger
from utils.exceptions import APIConnectionError, ValidationError as CustomValidationError
from pydantic import ValidationError as PydanticValidationError

# Get logger for data ingestion agent
logger = get_data_ingestion_logger()


class DataIngestionState(BaseModel):
    """
    State model for tracking Data Ingestion Agent progress.
    
    This model maintains the current state of the data ingestion workflow,
    including progress tracking, collected data, and error information.
    
    Attributes:
        stage: Current stage of ingestion (initializing, fetching_time_entries, etc.)
        status: Current execution status (pending, in_progress, completed, error)
        time_entries_fetched: Number of time entries successfully fetched
        costs_fetched: Number of cost entries successfully fetched
        validation_errors: Count of validation errors encountered
        deduplication_count: Number of duplicate entries removed
        start_time: Timestamp when ingestion started
        end_time: Timestamp when ingestion completed (None if in progress)
        error_message: Error message if ingestion failed
    """
    
    stage: str = Field(
        default="initializing",
        description="Current stage of ingestion workflow"
    )
    
    status: AgentStatus = Field(
        default=AgentStatus.PENDING,
        description="Current execution status"
    )
    
    time_entries_fetched: int = Field(
        default=0,
        description="Number of time entries successfully fetched"
    )
    
    costs_fetched: int = Field(
        default=0,
        description="Number of cost entries successfully fetched"
    )
    
    validation_errors: int = Field(
        default=0,
        description="Count of validation errors encountered"
    )
    
    deduplication_count: int = Field(
        default=0,
        description="Number of duplicate entries removed"
    )
    
    start_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when ingestion started"
    )
    
    end_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when ingestion completed"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if ingestion failed"
    )
    
    def to_status_message(self) -> StatusUpdateMessage:
        """
        Convert current state to a WebSocket status update message.
        
        Returns:
            StatusUpdateMessage for broadcasting to frontend
        """
        details = f"{self.stage}: "
        
        if self.status == AgentStatus.IN_PROGRESS:
            details += f"Fetched {self.time_entries_fetched} time entries, {self.costs_fetched} costs"
        elif self.status == AgentStatus.COMPLETED:
            details += f"Successfully ingested {self.time_entries_fetched} time entries and {self.costs_fetched} costs"
        elif self.status == AgentStatus.ERROR:
            details += f"Error: {self.error_message}"
        else:
            details += "Waiting to start"
        
        return StatusUpdateMessage(
            stage=AgentStage.DATA_INGESTION,
            status=self.status,
            details=details,
            timestamp=datetime.now()
        )


class DataIngestionResult(BaseModel):
    """
    Result model for Data Ingestion Agent execution.
    
    Contains all data collected during ingestion along with metadata
    about the ingestion process.
    
    Attributes:
        time_entries: List of validated EmployeeTimeEntry objects
        costs: List of validated ProjectCost objects
        validation_errors: List of validation error messages
        deduplication_count: Number of duplicates removed
        execution_time_seconds: Total execution time
        summary: Human-readable summary of ingestion results
    """
    
    time_entries: List[EmployeeTimeEntry] = Field(
        default_factory=list,
        description="List of validated time entries"
    )
    
    costs: List[ProjectCost] = Field(
        default_factory=list,
        description="List of validated cost entries"
    )
    
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation error messages"
    )
    
    deduplication_count: int = Field(
        default=0,
        description="Number of duplicate entries removed"
    )
    
    execution_time_seconds: float = Field(
        default=0.0,
        description="Total execution time in seconds"
    )
    
    summary: str = Field(
        default="",
        description="Human-readable summary of ingestion results"
    )


class DataIngestionAgent:
    """
    PydanticAI-based agent for data ingestion from external APIs.
    
    This agent orchestrates the collection of employee time tracking data from
    Clockify and payroll/HRIS data from Unified.to. It handles authentication,
    data fetching, validation, deduplication, and quality checks.
    
    The agent maintains state throughout execution and can send real-time
    status updates via WebSocket for frontend visualization.
    
    Example:
        >>> from datetime import datetime
        >>> 
        >>> # Initialize agent with API connectors
        >>> clockify = ClockifyConnector(api_key="...", workspace_id="...")
        >>> unified_to = UnifiedToConnector(api_key="...", workspace_id="...")
        >>> agent = DataIngestionAgent(
        ...     clockify_connector=clockify,
        ...     unified_to_connector=unified_to
        ... )
        >>> 
        >>> # Run ingestion for date range
        >>> result = agent.run(
        ...     start_date=datetime(2024, 1, 1),
        ...     end_date=datetime(2024, 1, 31)
        ... )
        >>> 
        >>> print(f"Fetched {len(result.time_entries)} time entries")
        >>> print(f"Fetched {len(result.costs)} costs")
    """
    
    def __init__(
        self,
        clockify_connector: ClockifyConnector,
        unified_to_connector: UnifiedToConnector,
        status_callback: Optional[callable] = None
    ):
        """
        Initialize Data Ingestion Agent.
        
        Args:
            clockify_connector: Initialized ClockifyConnector for time tracking data
            unified_to_connector: Initialized UnifiedToConnector for HRIS/payroll data
            status_callback: Optional callback function for status updates
                            (receives StatusUpdateMessage objects)
        
        Raises:
            ValueError: If connectors are None
        """
        if clockify_connector is None:
            raise ValueError("clockify_connector cannot be None")
        if unified_to_connector is None:
            raise ValueError("unified_to_connector cannot be None")
        
        self.clockify = clockify_connector
        self.unified_to = unified_to_connector
        self.status_callback = status_callback
        
        # Initialize agent state
        self.state = DataIngestionState()
        
        logger.info(
            "Initialized Data Ingestion Agent with Clockify and Unified.to connectors"
        )
    
    def _update_status(
        self,
        stage: str,
        status: AgentStatus,
        error_message: Optional[str] = None
    ):
        """
        Update agent state and send status update via callback.
        
        Args:
            stage: Current stage description
            status: Current execution status
            error_message: Optional error message if status is ERROR
        """
        self.state.stage = stage
        self.state.status = status
        
        if error_message:
            self.state.error_message = error_message
        
        # Log status update
        log_level = logging.ERROR if status == AgentStatus.ERROR else logging.INFO
        logger.log(
            log_level,
            f"Status update: {stage} - {status.value}"
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
        start_date: datetime,
        end_date: datetime,
        connection_id: Optional[str] = None
    ) -> DataIngestionResult:
        """
        Run the data ingestion workflow.
        
        This method orchestrates the complete data ingestion process:
        1. Fetch time entries from Clockify
        2. Fetch payroll/HRIS data from Unified.to
        3. Validate all data against Pydantic models
        4. Deduplicate entries
        5. Perform data quality checks
        
        Args:
            start_date: Start date for data collection (inclusive)
            end_date: End date for data collection (inclusive)
            connection_id: Optional Unified.to connection ID for HRIS system
        
        Returns:
            DataIngestionResult with collected data and metadata
        
        Raises:
            ValueError: If date range is invalid
            APIConnectionError: If API requests fail after retries
        
        Example:
            >>> agent = DataIngestionAgent(clockify=..., unified_to=...)
            >>> result = agent.run(
            ...     start_date=datetime(2024, 1, 1),
            ...     end_date=datetime(2024, 1, 31),
            ...     connection_id="conn_123"
            ... )
        """
        # Validate date range
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")
        
        # Initialize result
        result = DataIngestionResult()
        validation_errors = []
        
        # Record start time
        self.state.start_time = datetime.now()
        self.state.status = AgentStatus.IN_PROGRESS
        
        logger.info(
            f"Starting data ingestion for date range: "
            f"{start_date.date()} to {end_date.date()}"
        )
        
        try:
            # Stage 1: Fetch time entries from Clockify
            self._update_status(
                stage="fetching_time_entries",
                status=AgentStatus.IN_PROGRESS
            )
            
            time_entries, time_entry_errors = self._fetch_time_entries(
                start_date=start_date,
                end_date=end_date
            )
            
            self.state.time_entries_fetched = len(time_entries)
            validation_errors.extend(time_entry_errors)
            
            logger.info(
                f"Fetched {len(time_entries)} time entries "
                f"({len(time_entry_errors)} validation errors)"
            )
            
            # Stage 2: Fetch costs from Unified.to
            self._update_status(
                stage="fetching_costs",
                status=AgentStatus.IN_PROGRESS
            )
            
            costs, cost_errors = self._fetch_costs(
                start_date=start_date,
                end_date=end_date,
                connection_id=connection_id
            )
            
            self.state.costs_fetched = len(costs)
            validation_errors.extend(cost_errors)
            
            logger.info(
                f"Fetched {len(costs)} costs "
                f"({len(cost_errors)} validation errors)"
            )
            
            # Stage 3: Deduplicate entries
            self._update_status(
                stage="deduplicating",
                status=AgentStatus.IN_PROGRESS
            )
            
            time_entries, dedup_count = self._deduplicate_time_entries(time_entries)
            self.state.deduplication_count = dedup_count
            
            logger.info(f"Removed {dedup_count} duplicate time entries")
            
            # Stage 4: Data quality checks
            self._update_status(
                stage="quality_checks",
                status=AgentStatus.IN_PROGRESS
            )
            
            quality_warnings = self._check_data_quality(time_entries, costs)
            
            logger.info(f"Data quality check complete: {len(quality_warnings)} warnings")
            
            # Record end time and calculate execution time
            self.state.end_time = datetime.now()
            execution_time = (self.state.end_time - self.state.start_time).total_seconds()
            
            # Build result
            result.time_entries = time_entries
            result.costs = costs
            result.validation_errors = validation_errors
            result.deduplication_count = dedup_count
            result.execution_time_seconds = execution_time
            result.summary = (
                f"Successfully ingested {len(time_entries)} time entries and "
                f"{len(costs)} costs in {execution_time:.1f}s. "
                f"Removed {dedup_count} duplicates. "
                f"{len(validation_errors)} validation errors encountered."
            )
            
            # Update final status
            self._update_status(
                stage="completed",
                status=AgentStatus.COMPLETED
            )
            
            logger.info(f"Data ingestion completed: {result.summary}")
            
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
            error_msg = f"Unexpected error during data ingestion: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            self._update_status(
                stage="error",
                status=AgentStatus.ERROR,
                error_message=error_msg
            )
            
            raise
    
    def _fetch_time_entries(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> tuple[List[EmployeeTimeEntry], List[str]]:
        """
        Fetch and validate time entries from Clockify.
        
        This method fetches raw time entries from Clockify, transforms them to
        EmployeeTimeEntry objects, and validates them against the Pydantic model.
        Validation errors are collected without stopping execution, allowing the
        agent to process as much valid data as possible.
        
        Args:
            start_date: Start date for time entries
            end_date: End date for time entries
        
        Returns:
            Tuple of (validated_entries, error_messages)
            - validated_entries: List of successfully validated EmployeeTimeEntry objects
            - error_messages: List of detailed error messages for failed validations
        
        Raises:
            APIConnectionError: If Clockify API connection fails
        """
        logger.info("Fetching time entries from Clockify...")
        
        try:
            # Fetch raw time entries
            raw_entries = self.clockify.fetch_time_entries(
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(f"Received {len(raw_entries)} raw time entries from Clockify")
            
            # Transform and validate entries
            validated_entries = []
            errors = []
            
            for idx, raw_entry in enumerate(raw_entries):
                entry_id = raw_entry.get('id', f'entry_{idx}')
                
                try:
                    # Transform using connector's method
                    entry = self.clockify._transform_time_entry(raw_entry)
                    
                    if entry:
                        # Additional validation: ensure entry is EmployeeTimeEntry instance
                        if not isinstance(entry, EmployeeTimeEntry):
                            error_msg = (
                                f"Entry {entry_id}: Transformation returned invalid type "
                                f"{type(entry).__name__}, expected EmployeeTimeEntry"
                            )
                            errors.append(error_msg)
                            logger.warning(error_msg)
                            continue
                        
                        # Validate all required fields are present and non-empty
                        validation_issues = []
                        
                        if not entry.employee_id or not entry.employee_id.strip():
                            validation_issues.append("employee_id is empty")
                        
                        if not entry.employee_name or not entry.employee_name.strip():
                            validation_issues.append("employee_name is empty")
                        
                        if not entry.project_name or not entry.project_name.strip():
                            validation_issues.append("project_name is empty")
                        
                        if not entry.task_description or not entry.task_description.strip():
                            validation_issues.append("task_description is empty")
                        
                        if validation_issues:
                            error_msg = (
                                f"Entry {entry_id}: Validation failed - "
                                f"{', '.join(validation_issues)}"
                            )
                            errors.append(error_msg)
                            logger.warning(error_msg)
                            continue
                        
                        # Entry is valid, add to list
                        validated_entries.append(entry)
                        logger.debug(
                            f"Successfully validated entry {entry_id}: "
                            f"{entry.employee_name} - {entry.hours_spent}h on {entry.project_name}"
                        )
                    
                    else:
                        error_msg = (
                            f"Entry {entry_id}: Transformation returned None - "
                            f"likely missing required fields in raw data"
                        )
                        errors.append(error_msg)
                        logger.warning(error_msg)
                
                except ValueError as e:
                    # Pydantic validation error
                    error_msg = (
                        f"Entry {entry_id}: Pydantic validation failed - {str(e)}"
                    )
                    errors.append(error_msg)
                    logger.warning(error_msg)
                
                except Exception as e:
                    # Unexpected error during transformation
                    error_msg = (
                        f"Entry {entry_id}: Unexpected error during transformation - "
                        f"{type(e).__name__}: {str(e)}"
                    )
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)
            
            # Update state with validation error count
            self.state.validation_errors += len(errors)
            
            logger.info(
                f"Time entry validation complete: {len(validated_entries)} valid, "
                f"{len(errors)} errors"
            )
            
            return validated_entries, errors
        
        except APIConnectionError as e:
            logger.error(f"Failed to fetch time entries from Clockify: {e}")
            raise
    
    def _fetch_costs(
        self,
        start_date: datetime,
        end_date: datetime,
        connection_id: Optional[str] = None
    ) -> tuple[List[ProjectCost], List[str]]:
        """
        Fetch and validate cost data from Unified.to.
        
        This method fetches payroll and cost data from Unified.to, transforms them to
        ProjectCost objects, and validates them against the Pydantic model.
        Validation errors are collected without stopping execution, allowing the
        agent to process as much valid data as possible.
        
        Args:
            start_date: Start date for costs
            end_date: End date for costs
            connection_id: Optional Unified.to connection ID for HRIS system
        
        Returns:
            Tuple of (validated_costs, error_messages)
            - validated_costs: List of successfully validated ProjectCost objects
            - error_messages: List of detailed error messages for failed validations
        
        Raises:
            APIConnectionError: If Unified.to API connection fails
        """
        logger.info("Fetching costs from Unified.to...")
        
        # TODO: Implement Unified.to cost fetching
        # This will be implemented in subsequent tasks (98-101)
        # For now, return empty lists as placeholder with validation framework
        
        validated_costs = []
        errors = []
        
        try:
            # Placeholder for future implementation
            # When implemented, this will:
            # 1. Fetch raw payslip/cost data from Unified.to
            # 2. Transform each entry to ProjectCost
            # 3. Validate against Pydantic model
            # 4. Collect validation errors without stopping
            
            # Example validation logic (to be used when data is available):
            # raw_costs = self.unified_to.fetch_payslips(
            #     connection_id=connection_id,
            #     start_date=start_date,
            #     end_date=end_date
            # )
            #
            # for idx, raw_cost in enumerate(raw_costs):
            #     cost_id = raw_cost.get('id', f'cost_{idx}')
            #     
            #     try:
            #         cost = self.unified_to._transform_payslip_to_cost(raw_cost)
            #         
            #         if cost:
            #             # Validate instance type
            #             if not isinstance(cost, ProjectCost):
            #                 errors.append(f"Cost {cost_id}: Invalid type")
            #                 continue
            #             
            #             # Validate required fields
            #             validation_issues = []
            #             
            #             if not cost.cost_id or not cost.cost_id.strip():
            #                 validation_issues.append("cost_id is empty")
            #             
            #             if not cost.project_name or not cost.project_name.strip():
            #                 validation_issues.append("project_name is empty")
            #             
            #             if validation_issues:
            #                 error_msg = (
            #                     f"Cost {cost_id}: Validation failed - "
            #                     f"{', '.join(validation_issues)}"
            #                 )
            #                 errors.append(error_msg)
            #                 logger.warning(error_msg)
            #                 continue
            #             
            #             validated_costs.append(cost)
            #         else:
            #             errors.append(f"Cost {cost_id}: Transformation returned None")
            #     
            #     except ValueError as e:
            #         errors.append(f"Cost {cost_id}: Pydantic validation failed - {str(e)}")
            #     except Exception as e:
            #         errors.append(f"Cost {cost_id}: Unexpected error - {str(e)}")
            
            logger.warning(
                "Unified.to cost fetching not yet implemented - returning empty list"
            )
            
            # Update state with validation error count
            self.state.validation_errors += len(errors)
            
            return validated_costs, errors
        
        except APIConnectionError as e:
            logger.error(f"Failed to fetch costs from Unified.to: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching costs: {e}", exc_info=True)
            # Don't raise - return what we have so far
            return validated_costs, errors
    
    def _deduplicate_time_entries(
        self,
        entries: List[EmployeeTimeEntry]
    ) -> tuple[List[EmployeeTimeEntry], int]:
        """
        Remove duplicate time entries.
        
        Identifies duplicates by employee_id + date + project_name.
        When duplicates are found, hours are summed and the first entry is kept.
        
        Args:
            entries: List of time entries to deduplicate
        
        Returns:
            Tuple of (deduplicated_entries, duplicate_count)
        """
        logger.info(f"Deduplicating {len(entries)} time entries...")
        
        if not entries:
            logger.info("No entries to deduplicate")
            return entries, 0
        
        # Dictionary to track unique entries by composite key
        # Key: (employee_id, date_str, project_name)
        # Value: EmployeeTimeEntry with accumulated hours
        unique_entries = {}
        duplicate_count = 0
        
        for entry in entries:
            # Create composite key for deduplication
            # Use date string (YYYY-MM-DD) to ignore time component
            date_str = entry.date.strftime('%Y-%m-%d')
            key = (entry.employee_id, date_str, entry.project_name)
            
            if key in unique_entries:
                # Duplicate found - sum hours
                existing_entry = unique_entries[key]
                
                logger.debug(
                    f"Duplicate found: {entry.employee_name} - {entry.project_name} "
                    f"on {date_str}. Merging {entry.hours_spent}h with existing "
                    f"{existing_entry.hours_spent}h"
                )
                
                # Create new entry with summed hours
                # Keep all other fields from the first entry
                merged_entry = EmployeeTimeEntry(
                    employee_id=existing_entry.employee_id,
                    employee_name=existing_entry.employee_name,
                    project_name=existing_entry.project_name,
                    task_description=existing_entry.task_description,
                    hours_spent=existing_entry.hours_spent + entry.hours_spent,
                    date=existing_entry.date,
                    is_rd_classified=existing_entry.is_rd_classified
                )
                
                unique_entries[key] = merged_entry
                duplicate_count += 1
                
            else:
                # First occurrence of this key
                unique_entries[key] = entry
        
        # Convert dictionary back to list
        deduplicated_entries = list(unique_entries.values())
        
        # Log deduplication statistics
        logger.info(
            f"Deduplication complete: {len(entries)} entries -> "
            f"{len(deduplicated_entries)} unique entries. "
            f"Removed {duplicate_count} duplicates."
        )
        
        if duplicate_count > 0:
            logger.info(
                f"Deduplication statistics: "
                f"Original count: {len(entries)}, "
                f"Unique count: {len(deduplicated_entries)}, "
                f"Duplicates removed: {duplicate_count}, "
                f"Reduction: {(duplicate_count / len(entries) * 100):.1f}%"
            )
        
        return deduplicated_entries, duplicate_count
    
    def _validate_pydantic_model(
        self,
        model_class: type,
        data: dict,
        record_id: str
    ) -> tuple[Optional[BaseModel], Optional[str]]:
        """
        Validate data against a Pydantic model and return detailed error information.
        
        This helper method attempts to create a Pydantic model instance from raw data
        and captures detailed validation errors if the data is invalid.
        
        Args:
            model_class: The Pydantic model class to validate against
            data: Dictionary of data to validate
            record_id: Identifier for the record (for error messages)
        
        Returns:
            Tuple of (validated_model, error_message)
            - validated_model: Instance of model_class if validation succeeds, None otherwise
            - error_message: Detailed error message if validation fails, None otherwise
        
        Example:
            >>> model, error = self._validate_pydantic_model(
            ...     EmployeeTimeEntry,
            ...     {'employee_id': 'EMP001', 'hours_spent': 25},
            ...     'entry_123'
            ... )
            >>> if error:
            ...     print(error)  # "Entry entry_123: hours_spent cannot exceed 24 hours"
        """
        try:
            # Attempt to create model instance
            instance = model_class(**data)
            return instance, None
        
        except PydanticValidationError as e:
            # Extract detailed validation errors
            error_details = []
            
            for error in e.errors():
                field = '.'.join(str(loc) for loc in error['loc'])
                msg = error['msg']
                error_details.append(f"{field}: {msg}")
            
            error_message = (
                f"Record {record_id}: Pydantic validation failed - "
                f"{'; '.join(error_details)}"
            )
            
            return None, error_message
        
        except Exception as e:
            # Unexpected error
            error_message = (
                f"Record {record_id}: Unexpected validation error - "
                f"{type(e).__name__}: {str(e)}"
            )
            
            return None, error_message
    
    def _check_data_quality(
        self,
        time_entries: List[EmployeeTimeEntry],
        costs: List[ProjectCost]
    ) -> List[str]:
        """
        Perform data quality checks on ingested data.
        
        Checks for:
        - Suspicious time entries (> 16 hours/day)
        - Missing required fields
        - Invalid date ranges
        - Future dates
        - Zero or negative hours
        - Zero or negative costs
        
        Args:
            time_entries: List of time entries to check
            costs: List of costs to check
        
        Returns:
            List of warning messages
        
        Requirements: 1.3
        """
        logger.info("Performing data quality checks...")
        
        warnings = []
        current_date = datetime.now()
        
        # Check time entries
        for entry in time_entries:
            entry_id = f"{entry.employee_id}_{entry.project_name}_{entry.date.strftime('%Y-%m-%d')}"
            
            # Check for suspicious hours (> 16 hours/day)
            if entry.hours_spent > 16:
                warning = (
                    f"Suspicious time entry: {entry.employee_name} ({entry.employee_id}) "
                    f"logged {entry.hours_spent} hours on {entry.date.strftime('%Y-%m-%d')} "
                    f"for project '{entry.project_name}' - exceeds 16 hours/day threshold"
                )
                warnings.append(warning)
                logger.warning(warning)
            
            # Check for future dates
            if entry.date > current_date:
                warning = (
                    f"Invalid date: {entry.employee_name} ({entry.employee_id}) "
                    f"has time entry dated {entry.date.strftime('%Y-%m-%d')} "
                    f"which is in the future"
                )
                warnings.append(warning)
                logger.warning(warning)
            
            # Check for zero hours (should have been caught by Pydantic, but double-check)
            if entry.hours_spent <= 0:
                warning = (
                    f"Invalid hours: {entry.employee_name} ({entry.employee_id}) "
                    f"has {entry.hours_spent} hours on {entry.date.strftime('%Y-%m-%d')} "
                    f"for project '{entry.project_name}'"
                )
                warnings.append(warning)
                logger.warning(warning)
            
            # Check for missing required fields (whitespace-only strings)
            if not entry.employee_id.strip():
                warning = f"Missing employee_id in entry: {entry_id}"
                warnings.append(warning)
                logger.warning(warning)
            
            if not entry.employee_name.strip():
                warning = f"Missing employee_name in entry: {entry_id}"
                warnings.append(warning)
                logger.warning(warning)
            
            if not entry.project_name.strip():
                warning = f"Missing project_name in entry: {entry_id}"
                warnings.append(warning)
                logger.warning(warning)
            
            if not entry.task_description.strip():
                warning = f"Missing task_description in entry: {entry_id}"
                warnings.append(warning)
                logger.warning(warning)
        
        # Check costs
        for cost in costs:
            cost_id = f"{cost.cost_id}_{cost.project_name}"
            
            # Check for zero or negative amounts
            if cost.amount <= 0:
                warning = (
                    f"Invalid cost amount: Cost {cost.cost_id} "
                    f"for project '{cost.project_name}' has amount ${cost.amount:.2f}"
                )
                warnings.append(warning)
                logger.warning(warning)
            
            # Check for future dates
            if cost.date > current_date:
                warning = (
                    f"Invalid date: Cost {cost.cost_id} "
                    f"for project '{cost.project_name}' "
                    f"dated {cost.date.strftime('%Y-%m-%d')} is in the future"
                )
                warnings.append(warning)
                logger.warning(warning)
            
            # Check for missing required fields
            if not cost.cost_id.strip():
                warning = f"Missing cost_id in cost entry: {cost_id}"
                warnings.append(warning)
                logger.warning(warning)
            
            if not cost.project_name.strip():
                warning = f"Missing project_name in cost entry: {cost_id}"
                warnings.append(warning)
                logger.warning(warning)
            
            if not cost.cost_type.strip():
                warning = f"Missing cost_type in cost entry: {cost_id}"
                warnings.append(warning)
                logger.warning(warning)
        
        # Log summary
        if warnings:
            logger.warning(
                f"Data quality check complete: {len(warnings)} warnings found"
            )
        else:
            logger.info("Data quality check complete: No issues found")
        
        return warnings
    
    def get_state(self) -> DataIngestionState:
        """
        Get current agent state.
        
        Returns:
            Current DataIngestionState
        """
        return self.state
    
    def reset_state(self):
        """
        Reset agent state to initial values.
        
        Useful for running multiple ingestion operations with the same agent instance.
        """
        self.state = DataIngestionState()
        logger.info("Agent state reset to initial values")
