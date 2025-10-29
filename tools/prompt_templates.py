"""
Prompt Templates for R&D Tax Credit Automation Agent

This module provides prompt templates for various LLM interactions in the system:
- RAG_INFERENCE_PROMPT: For RAG-augmented reasoning with IRS document context
- AGENT_DECISION_PROMPT: For PydanticAI agent decision-making logic
- THESYS_UI_GENERATION_PROMPT: For dynamic UI generation with Thesys C1

Each template includes placeholders that can be populated with actual data
using the provided helper functions.

Requirements: 2.3, 4.1, 4.3
"""

from typing import Dict, List, Any, Optional
import json


# ============================================================================
# RAG INFERENCE PROMPT
# ============================================================================

RAG_INFERENCE_PROMPT = """You are an expert tax consultant specializing in R&D tax credits under IRS Section 41.

Your task is to analyze a project and determine what percentage of its activities qualify for the R&D tax credit based on authoritative IRS guidance.

## IRS Document Context

The following excerpts from official IRS documents are relevant to this analysis:

{rag_context}

## Project Information

**Project Name:** {project_name}

**Project Description:** {project_description}

**Technical Activities:**
{technical_activities}

**Total Hours:** {total_hours}

**Total Cost:** ${total_cost:,.2f}

## Analysis Instructions

Based on the IRS guidance provided above, analyze this project against the four-part test for qualified research:

1. **Technological in Nature**: Does the process rely on principles of physical or biological sciences, engineering, or computer science?

2. **Elimination of Uncertainty**: Is the project intended to discover information that would eliminate uncertainty about the development or improvement of a business component?

3. **Process of Experimentation**: Does the project involve a systematic process of evaluating alternatives to achieve the desired result?

4. **Qualified Purpose**: Is the purpose to create a new or improved business component (product, process, software, technique, formula, or invention)?

## Required Output Format

Provide your analysis in the following JSON format:

```json
{{
  "qualification_percentage": <number between 0-100>,
  "confidence_score": <number between 0-1>,
  "reasoning": "<detailed explanation of your analysis>",
  "citations": ["<IRS document reference 1>", "<IRS document reference 2>"],
  "four_part_test_results": {{
    "technological_in_nature": <true/false>,
    "elimination_of_uncertainty": <true/false>,
    "process_of_experimentation": <true/false>,
    "qualified_purpose": <true/false>
  }},
  "technical_details": "<specific technical uncertainties and experimentation processes>"
}}
```

Be conservative in your qualification percentage. Only activities that clearly meet all four parts of the test should be included.
"""


# ============================================================================
# AGENT DECISION PROMPT
# ============================================================================

AGENT_DECISION_PROMPT = """You are an AI agent in the R&D Tax Credit Automation system, responsible for making decisions about the workflow.

## Current Stage: {stage_name}

## Agent State

{agent_state}

## Available Actions

{available_actions}

## Context

{context_information}

## Decision Required

{decision_question}

## Instructions

Based on the current state and context, decide on the next action to take. Consider:

1. **Data Quality**: Is the data sufficient and valid to proceed?
2. **Compliance**: Does the decision align with IRS regulations?
3. **Risk Assessment**: What are the potential risks of this decision?
4. **User Intent**: What does the user expect at this stage?

Provide your decision in the following format:

```json
{{
  "action": "<selected action from available actions>",
  "reasoning": "<explanation of why this action is appropriate>",
  "confidence": <number between 0-1>,
  "warnings": ["<any warnings or concerns>"],
  "next_steps": ["<recommended next steps after this action>"]
}}
```

Be transparent about your reasoning and flag any concerns that require user attention.
"""


# ============================================================================
# THESYS UI GENERATION PROMPTS
# ============================================================================

THESYS_DATA_INGESTION_PROMPT = """Generate an interactive data table interface with the following specifications:

## Data to Display

{data_json}

## Required Features

1. **Table Columns:**
   - Employee Name (sortable)
   - Project Name (sortable, filterable)
   - Task Description (truncated with expand option)
   - Hours Spent (sortable, numeric)
   - Date (sortable, date format)
   - R&D Classification (editable checkbox)

2. **Interactivity:**
   - Sort by any column (ascending/descending)
   - Filter by project name (dropdown or search)
   - Bulk select/deselect for R&D classification
   - Highlight rows where R&D Classification is checked

3. **Summary Section:**
   - Total Hours: {total_hours}
   - Classified R&D Hours: {classified_hours}
   - Classification Progress: {classification_percentage}%
   - Number of Projects: {project_count}

4. **Actions:**
   - "Proceed to Qualification" button (enabled only when at least one project is classified)
   - "Export Data" button (download as CSV)
   - "Reset Classifications" button

## Styling Requirements

- Professional, clean design
- Use color coding: green for classified R&D, gray for unclassified
- Responsive layout for desktop and tablet
- Loading states for data operations
- Clear visual feedback for user actions

Generate a modern, user-friendly interface that makes it easy to review and classify time entries.
"""


THESYS_QUALIFICATION_DASHBOARD_PROMPT = """Generate a comprehensive qualification dashboard with the following specifications:

## Qualified Projects Data

{qualified_projects_json}

## Required Components

### 1. Executive Summary Card
Display prominently at the top:
- **Total Qualified Hours:** {total_qualified_hours}
- **Total Qualified Cost:** ${total_qualified_cost:,.2f}
- **Estimated Tax Credit:** ${estimated_credit:,.2f} (20% of qualified costs)
- **Average Confidence Score:** {average_confidence:.1%}
- **Number of Qualified Projects:** {project_count}

### 2. Project Cards Grid
For each qualified project, create a card showing:
- Project name (bold, large text)
- Qualified hours and cost
- Confidence score with color coding:
  * Green (≥ 0.8): High confidence
  * Yellow (0.7-0.79): Medium confidence
  * Red (< 0.7): Low confidence - FLAGGED FOR REVIEW
- IRS citation reference
- Expandable "View Reasoning" section with detailed explanation
- Expandable "Technical Details" section

### 3. Risk Assessment Panel
- Count of low-confidence projects (< 0.7)
- List of flagged projects requiring review
- Recommendations for additional documentation
- Overall risk level indicator (Low/Medium/High)

### 4. Confidence Distribution Chart
- Visual representation of confidence scores across all projects
- Histogram or bar chart showing distribution

### 5. Action Buttons
- "Generate Audit Report" button (primary, large)
- "Back to Edit Classifications" button (secondary)
- "Export Qualification Summary" button (download JSON/CSV)

## Styling Requirements

- Use card-based layout for projects
- Color-coded confidence indicators
- Professional, audit-ready appearance
- Clear visual hierarchy
- Responsive design
- Smooth animations for expandable sections

Generate an informative dashboard that provides clear visibility into qualification results and risk assessment.
"""


THESYS_REPORT_CONFIRMATION_PROMPT = """Generate a final confirmation screen for report download with the following specifications:

## Report Metadata

{report_metadata_json}

## Required Components

### 1. Executive Summary Display
Large, prominent card showing:
- **Tax Year:** {tax_year}
- **Report Generated:** {generation_date}
- **Total Qualified Expenditure:** ${total_qualified_cost:,.2f}
- **Estimated Credit Amount:** ${estimated_credit:,.2f}
- **Number of Qualified Projects:** {project_count}
- **Report ID:** {report_id}

### 2. Final Checklist
Interactive checklist showing completion status:
- ✓ All projects reviewed and classified
- ✓ Qualification analysis completed
- ✓ Confidence scores acceptable (or warnings if low-confidence projects exist)
- ✓ IRS citations included for all projects
- ✓ Technical narratives generated
- ✓ Compliance review completed
- ✓ PDF report generated successfully

### 3. Risk Summary
If any low-confidence projects exist:
- Warning message about flagged projects
- List of projects requiring additional documentation
- Recommendation to review before submission

### 4. Action Buttons
- **"Download Audit Report (PDF)"** - Large, primary button
- **"Back to Edit"** - Secondary button to return to qualification stage
- **"Generate New Report"** - Start over with new data

### 5. Additional Information
- File size and page count
- Download instructions
- Next steps for IRS submission
- Support contact information

## Styling Requirements

- Celebratory, confident tone (if no warnings)
- Clear warning indicators (if low-confidence projects exist)
- Large, obvious download button
- Professional, polished appearance
- Responsive design
- Success animations

Generate a clear, confident confirmation screen that gives users assurance about their report quality.
"""


# ============================================================================
# NARRATIVE GENERATION PROMPT
# ============================================================================

NARRATIVE_GENERATION_PROMPT = """You are a technical writer specializing in R&D tax credit documentation.

Generate a comprehensive technical narrative for the following qualified R&D project that will be included in an IRS audit report.

## Project Information

**Project Name:** {project_name}

**Qualification Percentage:** {qualification_percentage}%

**Qualified Hours:** {qualified_hours}

**Qualified Cost:** ${qualified_cost:,.2f}

**Confidence Score:** {confidence_score}

**Qualification Reasoning:** {qualification_reasoning}

**IRS Citations:** {irs_citations}

## Narrative Template Structure

Your narrative should include the following sections:

### 1. Project Overview
- Brief description of the project and its business purpose
- Timeline and key milestones

### 2. Technical Uncertainties
- Specific technical challenges that were uncertain at the project's outset
- Why existing solutions were inadequate
- What information needed to be discovered

### 3. Process of Experimentation
- Systematic approach used to evaluate alternatives
- Specific experiments, tests, or trials conducted
- How results were analyzed and used to refine the approach
- Iterations and refinements made

### 4. Technological Nature
- Scientific or engineering principles applied
- Technical methodologies employed
- How the work relied on hard sciences (computer science, engineering, etc.)

### 5. Qualified Purpose
- New or improved business component being developed
- How the component differs from existing solutions
- Performance improvements or new capabilities achieved

### 6. Outcomes and Results
- Technical achievements
- Knowledge gained
- How uncertainties were resolved

## Writing Guidelines

- Use specific, technical language (avoid vague terms)
- Include concrete examples and details
- Reference IRS guidance where applicable
- Maintain professional, objective tone
- Be thorough but concise
- Focus on the technical aspects, not business benefits

## Output Format

Provide the narrative as a well-structured document with clear section headings. The narrative should be audit-ready and demonstrate clear compliance with IRS Section 41 requirements.
"""


# ============================================================================
# COMPLIANCE REVIEW PROMPT
# ============================================================================

COMPLIANCE_REVIEW_PROMPT = """You are a compliance reviewer for R&D tax credit documentation.

Review the following technical narrative for completeness and compliance with IRS requirements.

## Narrative to Review

{narrative_text}

## Review Checklist

Verify that the narrative includes:

1. **Technical Uncertainties**
   - [ ] Specific uncertainties are clearly identified
   - [ ] Uncertainties are technological in nature
   - [ ] Explanation of why existing knowledge was inadequate

2. **Process of Experimentation**
   - [ ] Systematic approach is described
   - [ ] Specific experiments or tests are mentioned
   - [ ] Evaluation of alternatives is documented
   - [ ] Iterative refinement process is explained

3. **Technological Nature**
   - [ ] Reliance on hard sciences is demonstrated
   - [ ] Technical principles are referenced
   - [ ] Scientific or engineering methodologies are described

4. **Qualified Purpose**
   - [ ] Business component is clearly identified
   - [ ] New or improved functionality is described
   - [ ] Purpose aligns with IRS requirements

5. **Documentation Quality**
   - [ ] Language is specific and technical
   - [ ] Concrete examples are provided
   - [ ] Professional tone is maintained
   - [ ] Narrative is well-organized and clear

## Output Format

Provide your review in the following JSON format:

```json
{{
  "compliance_status": "<compliant/needs_revision/non_compliant>",
  "completeness_score": <number between 0-1>,
  "missing_elements": ["<list of missing required elements>"],
  "suggestions": ["<specific suggestions for improvement>"],
  "strengths": ["<strong points in the narrative>"],
  "overall_assessment": "<summary of the review>"
}}
```

Be thorough and specific in your feedback. Flag any areas that could be challenged in an IRS audit.
"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def populate_rag_inference_prompt(
    rag_context: str,
    project_name: str,
    project_description: str,
    technical_activities: str,
    total_hours: float,
    total_cost: float
) -> str:
    """
    Populate the RAG inference prompt with actual data.
    
    Args:
        rag_context: Formatted RAG context from RD_Knowledge_Tool
        project_name: Name of the project being analyzed
        project_description: Description of the project
        technical_activities: List or description of technical activities
        total_hours: Total hours spent on the project
        total_cost: Total cost of the project
    
    Returns:
        Populated prompt string ready for LLM
    
    Example:
        >>> prompt = populate_rag_inference_prompt(
        ...     rag_context=context.format_for_llm_prompt(),
        ...     project_name="API Optimization",
        ...     project_description="Improve API response times",
        ...     technical_activities="Algorithm optimization, caching strategies",
        ...     total_hours=120.5,
        ...     total_cost=15000.00
        ... )
    """
    return RAG_INFERENCE_PROMPT.format(
        rag_context=rag_context,
        project_name=project_name,
        project_description=project_description,
        technical_activities=technical_activities,
        total_hours=total_hours,
        total_cost=total_cost
    )


def populate_agent_decision_prompt(
    stage_name: str,
    agent_state: Dict[str, Any],
    available_actions: List[str],
    context_information: str,
    decision_question: str
) -> str:
    """
    Populate the agent decision prompt with current state.
    
    Args:
        stage_name: Current stage of the workflow (e.g., "Data Ingestion")
        agent_state: Dictionary containing current agent state
        available_actions: List of actions the agent can take
        context_information: Additional context for the decision
        decision_question: Specific question the agent needs to answer
    
    Returns:
        Populated prompt string ready for LLM
    
    Example:
        >>> prompt = populate_agent_decision_prompt(
        ...     stage_name="Qualification",
        ...     agent_state={"projects_analyzed": 5, "low_confidence_count": 2},
        ...     available_actions=["proceed", "flag_for_review", "request_more_data"],
        ...     context_information="2 projects have confidence < 0.7",
        ...     decision_question="Should we proceed to report generation?"
        ... )
    """
    return AGENT_DECISION_PROMPT.format(
        stage_name=stage_name,
        agent_state=json.dumps(agent_state, indent=2),
        available_actions=json.dumps(available_actions, indent=2),
        context_information=context_information,
        decision_question=decision_question
    )


def populate_thesys_data_ingestion_prompt(
    data: List[Dict[str, Any]],
    total_hours: float,
    classified_hours: float,
    project_count: int
) -> str:
    """
    Populate the Thesys C1 data ingestion UI prompt.
    
    Args:
        data: List of time entry dictionaries
        total_hours: Total hours across all entries
        classified_hours: Hours classified as R&D
        project_count: Number of unique projects
    
    Returns:
        Populated prompt string for Thesys C1
    
    Example:
        >>> prompt = populate_thesys_data_ingestion_prompt(
        ...     data=time_entries,
        ...     total_hours=500.0,
        ...     classified_hours=350.0,
        ...     project_count=10
        ... )
    """
    classification_percentage = (classified_hours / total_hours * 100) if total_hours > 0 else 0
    
    return THESYS_DATA_INGESTION_PROMPT.format(
        data_json=json.dumps(data, indent=2, default=str),
        total_hours=total_hours,
        classified_hours=classified_hours,
        classification_percentage=classification_percentage,
        project_count=project_count
    )


def populate_thesys_qualification_dashboard_prompt(
    qualified_projects: List[Dict[str, Any]],
    total_qualified_hours: float,
    total_qualified_cost: float,
    estimated_credit: float,
    average_confidence: float
) -> str:
    """
    Populate the Thesys C1 qualification dashboard prompt.
    
    Args:
        qualified_projects: List of qualified project dictionaries
        total_qualified_hours: Sum of all qualified hours
        total_qualified_cost: Sum of all qualified costs
        estimated_credit: Estimated tax credit (typically 20% of costs)
        average_confidence: Average confidence score across projects
    
    Returns:
        Populated prompt string for Thesys C1
    
    Example:
        >>> prompt = populate_thesys_qualification_dashboard_prompt(
        ...     qualified_projects=projects,
        ...     total_qualified_hours=350.0,
        ...     total_qualified_cost=45000.00,
        ...     estimated_credit=9000.00,
        ...     average_confidence=0.85
        ... )
    """
    return THESYS_QUALIFICATION_DASHBOARD_PROMPT.format(
        qualified_projects_json=json.dumps(qualified_projects, indent=2, default=str),
        total_qualified_hours=total_qualified_hours,
        total_qualified_cost=total_qualified_cost,
        estimated_credit=estimated_credit,
        average_confidence=average_confidence,
        project_count=len(qualified_projects)
    )


def populate_thesys_report_confirmation_prompt(
    report_metadata: Dict[str, Any],
    tax_year: int,
    generation_date: str,
    total_qualified_cost: float,
    estimated_credit: float,
    project_count: int,
    report_id: str
) -> str:
    """
    Populate the Thesys C1 report confirmation prompt.
    
    Args:
        report_metadata: Dictionary containing report metadata
        tax_year: Tax year for the report
        generation_date: Date the report was generated
        total_qualified_cost: Total qualified costs
        estimated_credit: Estimated tax credit amount
        project_count: Number of qualified projects
        report_id: Unique report identifier
    
    Returns:
        Populated prompt string for Thesys C1
    
    Example:
        >>> prompt = populate_thesys_report_confirmation_prompt(
        ...     report_metadata=metadata,
        ...     tax_year=2024,
        ...     generation_date="2024-12-15",
        ...     total_qualified_cost=45000.00,
        ...     estimated_credit=9000.00,
        ...     project_count=10,
        ...     report_id="RPT-2024-001"
        ... )
    """
    return THESYS_REPORT_CONFIRMATION_PROMPT.format(
        report_metadata_json=json.dumps(report_metadata, indent=2, default=str),
        tax_year=tax_year,
        generation_date=generation_date,
        total_qualified_cost=total_qualified_cost,
        estimated_credit=estimated_credit,
        project_count=project_count,
        report_id=report_id
    )


def populate_narrative_generation_prompt(
    project_name: str,
    qualification_percentage: float,
    qualified_hours: float,
    qualified_cost: float,
    confidence_score: float,
    qualification_reasoning: str,
    irs_citations: List[str]
) -> str:
    """
    Populate the narrative generation prompt.
    
    Args:
        project_name: Name of the project
        qualification_percentage: Percentage of project qualifying for credit
        qualified_hours: Hours that qualify
        qualified_cost: Cost that qualifies
        confidence_score: Confidence in the qualification
        qualification_reasoning: Reasoning from qualification analysis
        irs_citations: List of IRS document citations
    
    Returns:
        Populated prompt string for narrative generation
    
    Example:
        >>> prompt = populate_narrative_generation_prompt(
        ...     project_name="API Optimization",
        ...     qualification_percentage=85.0,
        ...     qualified_hours=102.0,
        ...     qualified_cost=12750.00,
        ...     confidence_score=0.88,
        ...     qualification_reasoning="Project meets all four-part test criteria...",
        ...     irs_citations=["CFR Title 26 § 1.41-4", "Form 6765"]
        ... )
    """
    return NARRATIVE_GENERATION_PROMPT.format(
        project_name=project_name,
        qualification_percentage=qualification_percentage,
        qualified_hours=qualified_hours,
        qualified_cost=qualified_cost,
        confidence_score=confidence_score,
        qualification_reasoning=qualification_reasoning,
        irs_citations=", ".join(irs_citations) if irs_citations else "None"
    )


def populate_compliance_review_prompt(narrative_text: str) -> str:
    """
    Populate the compliance review prompt.
    
    Args:
        narrative_text: The technical narrative to review
    
    Returns:
        Populated prompt string for compliance review
    
    Example:
        >>> prompt = populate_compliance_review_prompt(
        ...     narrative_text="Project Overview: This project aimed to..."
        ... )
    """
    return COMPLIANCE_REVIEW_PROMPT.format(
        narrative_text=narrative_text
    )


# ============================================================================
# BATCH PROCESSING HELPERS
# ============================================================================

def create_batch_rag_prompts(
    projects: List[Dict[str, Any]],
    rag_contexts: List[str]
) -> List[str]:
    """
    Create multiple RAG inference prompts for batch processing.
    
    Args:
        projects: List of project dictionaries with required fields
        rag_contexts: List of RAG context strings (one per project)
    
    Returns:
        List of populated prompt strings
    
    Example:
        >>> prompts = create_batch_rag_prompts(
        ...     projects=[
        ...         {"name": "Project A", "description": "...", ...},
        ...         {"name": "Project B", "description": "...", ...}
        ...     ],
        ...     rag_contexts=[context_a, context_b]
        ... )
    """
    if len(projects) != len(rag_contexts):
        raise ValueError("Number of projects must match number of RAG contexts")
    
    prompts = []
    for project, rag_context in zip(projects, rag_contexts):
        prompt = populate_rag_inference_prompt(
            rag_context=rag_context,
            project_name=project.get("name", "Unknown Project"),
            project_description=project.get("description", ""),
            technical_activities=project.get("technical_activities", ""),
            total_hours=project.get("total_hours", 0.0),
            total_cost=project.get("total_cost", 0.0)
        )
        prompts.append(prompt)
    
    return prompts


def create_batch_narrative_prompts(
    qualified_projects: List[Dict[str, Any]]
) -> List[str]:
    """
    Create multiple narrative generation prompts for batch processing.
    
    Args:
        qualified_projects: List of qualified project dictionaries
    
    Returns:
        List of populated prompt strings
    
    Example:
        >>> prompts = create_batch_narrative_prompts(qualified_projects)
    """
    prompts = []
    for project in qualified_projects:
        prompt = populate_narrative_generation_prompt(
            project_name=project.get("project_name", "Unknown Project"),
            qualification_percentage=project.get("qualification_percentage", 0.0),
            qualified_hours=project.get("qualified_hours", 0.0),
            qualified_cost=project.get("qualified_cost", 0.0),
            confidence_score=project.get("confidence_score", 0.0),
            qualification_reasoning=project.get("reasoning", ""),
            irs_citations=project.get("citations", [])
        )
        prompts.append(prompt)
    
    return prompts
