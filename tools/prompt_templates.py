"""
Prompt Templates for R&D Tax Credit Automation Agent

This module provides prompt templates for various LLM interactions in the system:
- RAG_INFERENCE_PROMPT: For RAG-augmented reasoning with IRS document context
- AGENT_DECISION_PROMPT: For PydanticAI agent decision-making logic
- THESYS_UI_GENERATION_PROMPT: For dynamic UI generation with Thesys C1
- YOUCOM_QUALIFICATION_PROMPT: For You.com Agent API R&D qualification analysis
- YOUCOM_NARRATIVE_TEMPLATE_FETCH: For You.com Contents API template retrieval
- YOUCOM_COMPLIANCE_REVIEW_PROMPT: For You.com Express Agent compliance review
- YOUCOM_SEARCH_QUERY_TEMPLATE: For You.com Search API IRS guidance searches

Each template includes placeholders that can be populated with actual data
using the provided helper functions.

Requirements: 2.3, 4.1, 4.3, 6.1
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
# YOU.COM API PROMPTS
# ============================================================================

YOUCOM_QUALIFICATION_PROMPT = """You are an expert R&D tax credit consultant analyzing a project for IRS Section 41 qualification.

## IRS Guidance Context

{rag_context}

## Project Details

**Project Name:** {project_name}

**Project Description:** {project_description}

**Technical Activities:**
{technical_activities}

**Total Hours:** {total_hours}

**Total Cost:** ${total_cost:,.2f}

**Employee Roles Involved:** {employee_roles}

## Analysis Task

Using the IRS guidance provided above and your expertise, determine:

1. What percentage of this project's activities qualify for the R&D tax credit (0-100%)
2. Your confidence level in this assessment (0-1 scale)
3. Detailed reasoning supporting your determination
4. Specific IRS citations that support your conclusion

## Four-Part Test Evaluation

Evaluate the project against each criterion:

**1. Technological in Nature**
- Does the work fundamentally rely on principles of physical/biological sciences, engineering, or computer science?
- Are the methods used based on hard sciences rather than social sciences or arts?

**2. Elimination of Uncertainty**
- What specific technical uncertainties existed at the project's outset?
- Was the capability or method uncertain, or was the appropriate design uncertain?
- Could the desired result be achieved and was the method to achieve it uncertain?

**3. Process of Experimentation**
- Was there a systematic process to evaluate alternatives?
- Were different approaches tested and compared?
- Was there iteration and refinement based on results?

**4. Qualified Purpose**
- Is the purpose to create a new or improved business component?
- Does it result in new/improved functionality, performance, reliability, or quality?

## Output Requirements

Provide a comprehensive analysis that includes:
- Qualification percentage with clear justification
- Confidence score reflecting certainty of your assessment
- Detailed reasoning explaining how the project meets (or doesn't meet) each part of the four-part test
- Specific citations from the IRS guidance provided
- Technical details about uncertainties and experimentation
- Any red flags or concerns that could be challenged in an audit

Be conservative and thorough. Only activities that clearly meet ALL four criteria should be fully qualified.
"""


YOUCOM_NARRATIVE_TEMPLATE_FETCH = """Retrieve a comprehensive R&D tax credit project narrative template that can be used to document qualified research activities for IRS audit purposes.

## Template Requirements

The template should include sections for:

1. **Executive Summary**
   - Project overview and business context
   - Key technical objectives
   - Timeline and milestones

2. **Technical Uncertainties**
   - Specific uncertainties that existed at project start
   - Why existing knowledge or methods were inadequate
   - What needed to be discovered or developed

3. **Process of Experimentation**
   - Systematic approach used to resolve uncertainties
   - Alternative solutions evaluated
   - Tests, trials, or experiments conducted
   - How results informed subsequent iterations
   - Refinements made based on findings

4. **Technological Nature**
   - Scientific or engineering principles applied
   - Technical methodologies employed
   - Reliance on hard sciences (computer science, engineering, physics, etc.)
   - Technical expertise required

5. **Qualified Purpose**
   - Business component being developed or improved
   - New or improved functionality achieved
   - Performance enhancements or new capabilities
   - How the result differs from prior art

6. **Project Team and Resources**
   - Key personnel and their technical qualifications
   - Time allocation and effort distribution
   - Tools, technologies, and methodologies used

7. **Outcomes and Results**
   - Technical achievements
   - Knowledge gained
   - How uncertainties were resolved
   - Deliverables produced

## Format Preferences

- Professional, audit-ready language
- Clear section headings and structure
- Placeholders for project-specific details
- Guidance notes for completing each section
- Examples of strong technical descriptions
- Compliance with IRS documentation standards

Please provide a detailed template in Markdown format that can be populated with project-specific information.
"""


YOUCOM_COMPLIANCE_REVIEW_PROMPT = """You are a compliance expert reviewing R&D tax credit documentation for IRS audit readiness.

## Narrative to Review

{narrative_text}

## Compliance Review Criteria

Perform a thorough review to ensure the narrative meets IRS requirements for R&D tax credit documentation under Section 41.

### 1. Technical Uncertainties (Required)
- [ ] Specific technical uncertainties are clearly identified
- [ ] Uncertainties are technological in nature (not business/market uncertainties)
- [ ] Explanation of why existing knowledge was inadequate
- [ ] Description of what information needed to be discovered
- [ ] Uncertainties existed at the project's commencement

### 2. Process of Experimentation (Required)
- [ ] Systematic process for evaluating alternatives is described
- [ ] Specific experiments, tests, or trials are documented
- [ ] Multiple approaches or designs were considered
- [ ] Evaluation methodology is explained
- [ ] Iterative refinement process is demonstrated
- [ ] Results were analyzed and used to inform next steps

### 3. Technological Nature (Required)
- [ ] Reliance on hard sciences is clearly demonstrated
- [ ] Specific scientific or engineering principles are referenced
- [ ] Technical methodologies are described in detail
- [ ] Work required specialized technical knowledge
- [ ] Not primarily based on social sciences, arts, or humanities

### 4. Qualified Purpose (Required)
- [ ] Business component is clearly identified
- [ ] New or improved functionality is described
- [ ] Purpose aligns with IRS definition of qualified research
- [ ] Improvements are technical, not cosmetic or stylistic
- [ ] Result provides new capabilities or enhanced performance

### 5. Documentation Quality
- [ ] Language is specific and technical (not vague or generic)
- [ ] Concrete examples and details are provided
- [ ] Professional, objective tone is maintained
- [ ] Narrative is well-organized with clear structure
- [ ] Sufficient detail for IRS examiner to understand the work
- [ ] No exaggerated or unsupported claims

### 6. Audit Defense Readiness
- [ ] Documentation would withstand IRS scrutiny
- [ ] Technical claims are credible and verifiable
- [ ] No obvious red flags or weaknesses
- [ ] Appropriate level of technical detail
- [ ] Clear connection between activities and qualified research

## Review Output

Provide a detailed compliance assessment including:

1. **Overall Compliance Status**: Compliant / Needs Revision / Non-Compliant

2. **Completeness Score**: 0-100% based on how well all requirements are met

3. **Missing or Weak Elements**: Specific items that need to be added or strengthened

4. **Strengths**: Aspects of the narrative that are particularly strong

5. **Specific Recommendations**: Actionable suggestions for improvement

6. **Risk Assessment**: Likelihood of IRS challenge and areas of concern

7. **Required Revisions**: Must-fix issues before the narrative is audit-ready

Be thorough and critical. The goal is to ensure this documentation will withstand IRS examination.
"""


YOUCOM_SEARCH_QUERY_TEMPLATE = """Search for recent IRS guidance, rulings, and precedents related to R&D tax credits.

## Search Context

**Tax Year:** {tax_year}

**Industry/Sector:** {industry}

**Specific Topic:** {topic}

## Search Objectives

Find authoritative IRS information about:

1. **Recent Guidance and Rulings**
   - Revenue rulings issued in {tax_year} or later
   - IRS notices and announcements
   - Chief Counsel Advice memoranda
   - Technical Advice Memoranda (TAMs)

2. **Industry-Specific Guidance**
   - Guidance specific to {industry} sector
   - Software development qualification criteria (if applicable)
   - Manufacturing and engineering standards (if applicable)

3. **Compliance Updates**
   - Changes to Form 6765 or instructions
   - Updates to Section 41 regulations
   - New documentation requirements
   - Audit technique guides

4. **Case Law and Precedents**
   - Recent Tax Court decisions on R&D credits
   - Circuit court rulings affecting qualification
   - Settled cases with published guidance

## Search Query

{search_query}

## Expected Results

Return relevant IRS documents, rulings, and guidance that could impact the qualification analysis for projects in {industry} for tax year {tax_year}.

Focus on:
- Official IRS publications and rulings
- Recent updates or changes to existing guidance
- Industry-specific clarifications
- Precedents that could affect qualification decisions

Prioritize authoritative sources and recent publications.
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


# ============================================================================
# YOU.COM PROMPT HELPER FUNCTIONS
# ============================================================================

def populate_youcom_qualification_prompt(
    rag_context: str,
    project_name: str,
    project_description: str,
    technical_activities: str,
    total_hours: float,
    total_cost: float,
    employee_roles: Optional[str] = None
) -> str:
    """
    Populate the You.com qualification prompt with project data and RAG context.
    
    Args:
        rag_context: Formatted RAG context from RD_Knowledge_Tool
        project_name: Name of the project being analyzed
        project_description: Description of the project
        technical_activities: List or description of technical activities
        total_hours: Total hours spent on the project
        total_cost: Total cost of the project
        employee_roles: Optional description of employee roles involved
    
    Returns:
        Populated prompt string ready for You.com Agent API
    
    Example:
        >>> prompt = populate_youcom_qualification_prompt(
        ...     rag_context=context.format_for_llm_prompt(),
        ...     project_name="API Optimization",
        ...     project_description="Improve API response times",
        ...     technical_activities="Algorithm optimization, caching strategies",
        ...     total_hours=120.5,
        ...     total_cost=15000.00,
        ...     employee_roles="Senior Software Engineers, DevOps Engineers"
        ... )
    """
    if employee_roles is None:
        employee_roles = "Not specified"
    
    return YOUCOM_QUALIFICATION_PROMPT.format(
        rag_context=rag_context,
        project_name=project_name,
        project_description=project_description,
        technical_activities=technical_activities,
        total_hours=total_hours,
        total_cost=total_cost,
        employee_roles=employee_roles
    )


def populate_youcom_narrative_template_fetch() -> str:
    """
    Get the You.com narrative template fetch prompt.
    
    This prompt is used with You.com Contents API to retrieve
    R&D tax credit narrative templates from known sources.
    
    Returns:
        Prompt string for You.com Contents API
    
    Example:
        >>> prompt = populate_youcom_narrative_template_fetch()
        >>> # Use with You.com Contents API to fetch template
    """
    return YOUCOM_NARRATIVE_TEMPLATE_FETCH


def populate_youcom_compliance_review_prompt(narrative_text: str) -> str:
    """
    Populate the You.com compliance review prompt with a narrative to review.
    
    Args:
        narrative_text: The technical narrative to review for compliance
    
    Returns:
        Populated prompt string for You.com Express Agent API
    
    Example:
        >>> prompt = populate_youcom_compliance_review_prompt(
        ...     narrative_text="Project Overview: This project aimed to..."
        ... )
        >>> # Use with You.com Express Agent for quick compliance check
    """
    return YOUCOM_COMPLIANCE_REVIEW_PROMPT.format(
        narrative_text=narrative_text
    )


def populate_youcom_search_query_template(
    tax_year: int,
    industry: str,
    topic: str,
    search_query: str
) -> str:
    """
    Populate the You.com search query template for IRS guidance searches.
    
    Args:
        tax_year: Tax year for the search (e.g., 2024)
        industry: Industry or sector (e.g., "Software Development")
        topic: Specific topic to search (e.g., "Four-Part Test")
        search_query: The actual search query string
    
    Returns:
        Populated prompt string for You.com Search API
    
    Example:
        >>> prompt = populate_youcom_search_query_template(
        ...     tax_year=2024,
        ...     industry="Software Development",
        ...     topic="Process of Experimentation",
        ...     search_query="IRS Section 41 software development experimentation 2024"
        ... )
    """
    return YOUCOM_SEARCH_QUERY_TEMPLATE.format(
        tax_year=tax_year,
        industry=industry,
        topic=topic,
        search_query=search_query
    )


def create_youcom_search_query(
    tax_year: int,
    industry: str,
    keywords: List[str]
) -> str:
    """
    Create a focused search query for You.com Search API.
    
    Args:
        tax_year: Tax year for the search
        industry: Industry or sector
        keywords: List of keywords to include in search
    
    Returns:
        Formatted search query string
    
    Example:
        >>> query = create_youcom_search_query(
        ...     tax_year=2024,
        ...     industry="Software Development",
        ...     keywords=["Section 41", "qualified research", "four-part test"]
        ... )
        >>> # Returns: "IRS Section 41 qualified research four-part test software development 2024"
    """
    # Combine keywords with industry and tax year
    query_parts = ["IRS"] + keywords + [industry, str(tax_year)]
    return " ".join(query_parts)


def create_batch_youcom_qualification_prompts(
    projects: List[Dict[str, Any]],
    rag_contexts: List[str]
) -> List[str]:
    """
    Create multiple You.com qualification prompts for batch processing.
    
    Args:
        projects: List of project dictionaries with required fields
        rag_contexts: List of RAG context strings (one per project)
    
    Returns:
        List of populated prompt strings for You.com Agent API
    
    Example:
        >>> prompts = create_batch_youcom_qualification_prompts(
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
        prompt = populate_youcom_qualification_prompt(
            rag_context=rag_context,
            project_name=project.get("name", "Unknown Project"),
            project_description=project.get("description", ""),
            technical_activities=project.get("technical_activities", ""),
            total_hours=project.get("total_hours", 0.0),
            total_cost=project.get("total_cost", 0.0),
            employee_roles=project.get("employee_roles")
        )
        prompts.append(prompt)
    
    return prompts
