# Prompt Templates Module

## Overview

The `prompt_templates.py` module provides standardized prompt templates for all LLM interactions in the R&D Tax Credit Automation system. These templates ensure consistent, high-quality prompts across different agents and use cases.

## Template Categories

### 1. RAG Inference Prompt
**Purpose**: Analyze projects using IRS document context to determine R&D qualification

**Use Case**: Qualification Agent uses this to determine what percentage of a project qualifies for R&D tax credit

**Key Features**:
- Includes RAG context from IRS documents
- Structured project information
- Four-part test analysis framework
- JSON output format for structured parsing

**Example Usage**:
```python
from tools.prompt_templates import populate_rag_inference_prompt
from tools.rd_knowledge_tool import RD_Knowledge_Tool

# Get RAG context
rag_tool = RD_Knowledge_Tool()
context = rag_tool.query("What is the four-part test?")

# Populate prompt
prompt = populate_rag_inference_prompt(
    rag_context=context.format_for_llm_prompt(),
    project_name="API Optimization Project",
    project_description="Improve API response times through algorithm optimization",
    technical_activities="Algorithm analysis, caching strategies, performance testing",
    total_hours=120.5,
    total_cost=15000.00
)

# Use with GLM Reasoner
from tools.glm_reasoner import GLMReasoner
reasoner = GLMReasoner()
response = await reasoner.reason(prompt)
result = reasoner.parse_qualification_response(response)
```

### 2. Agent Decision Prompt
**Purpose**: Guide PydanticAI agents in making workflow decisions

**Use Case**: Agents use this to decide on next actions based on current state

**Key Features**:
- Current stage context
- Agent state information
- Available actions
- Decision framework

**Example Usage**:
```python
from tools.prompt_templates import populate_agent_decision_prompt

prompt = populate_agent_decision_prompt(
    stage_name="Qualification",
    agent_state={
        "projects_analyzed": 10,
        "low_confidence_count": 2,
        "total_qualified_cost": 45000.00
    },
    available_actions=["proceed_to_report", "flag_for_review", "request_more_data"],
    context_information="2 projects have confidence scores below 0.7",
    decision_question="Should we proceed to report generation or flag projects for review?"
)

# Use with agent reasoning
reasoner = GLMReasoner()
decision = await reasoner.reason(prompt)
parsed_decision = reasoner.parse_structured_response(decision)
```

### 3. Thesys UI Generation Prompts
**Purpose**: Generate dynamic UI components with Thesys C1

**Templates**:
- `THESYS_DATA_INGESTION_PROMPT`: Interactive data table for time entries
- `THESYS_QUALIFICATION_DASHBOARD_PROMPT`: Qualification results dashboard
- `THESYS_REPORT_CONFIRMATION_PROMPT`: Final report confirmation screen

**Example Usage**:
```python
from tools.prompt_templates import populate_thesys_data_ingestion_prompt

# Prepare data
time_entries = [
    {
        "employee_name": "John Doe",
        "project_name": "API Optimization",
        "hours_spent": 8.5,
        "date": "2024-01-15",
        "is_rd_classified": True
    },
    # ... more entries
]

prompt = populate_thesys_data_ingestion_prompt(
    data=time_entries,
    total_hours=500.0,
    classified_hours=350.0,
    project_count=10
)

# Send to Thesys C1 for UI generation
# (Thesys C1 integration code here)
```

### 4. Narrative Generation Prompt
**Purpose**: Generate technical narratives for qualified R&D projects

**Use Case**: Audit Trail Agent uses this to create detailed project narratives for the PDF report

**Key Features**:
- Structured narrative sections
- IRS compliance focus
- Technical writing guidelines
- Audit-ready output

**Example Usage**:
```python
from tools.prompt_templates import populate_narrative_generation_prompt

prompt = populate_narrative_generation_prompt(
    project_name="Machine Learning Model Optimization",
    qualification_percentage=85.0,
    qualified_hours=102.0,
    qualified_cost=12750.00,
    confidence_score=0.88,
    qualification_reasoning="Project meets all four-part test criteria with clear technical uncertainties...",
    irs_citations=["CFR Title 26 § 1.41-4(a)(1)", "Form 6765 Instructions"]
)

# Generate narrative
reasoner = GLMReasoner()
narrative = await reasoner.reason(prompt)
```

### 5. Compliance Review Prompt
**Purpose**: Review generated narratives for IRS compliance

**Use Case**: Audit Trail Agent uses this to QA check narratives before including in report

**Key Features**:
- Comprehensive checklist
- Compliance verification
- Improvement suggestions
- Quality scoring

**Example Usage**:
```python
from tools.prompt_templates import populate_compliance_review_prompt

# Review a generated narrative
prompt = populate_compliance_review_prompt(
    narrative_text=generated_narrative
)

reasoner = GLMReasoner()
review = await reasoner.reason(prompt)
review_result = reasoner.parse_structured_response(review)

if review_result["compliance_status"] != "compliant":
    print(f"Missing elements: {review_result['missing_elements']}")
    print(f"Suggestions: {review_result['suggestions']}")
```

## Batch Processing Helpers

### create_batch_rag_prompts()
Process multiple projects simultaneously:

```python
from tools.prompt_templates import create_batch_rag_prompts

projects = [
    {
        "name": "Project A",
        "description": "...",
        "technical_activities": "...",
        "total_hours": 100,
        "total_cost": 12000
    },
    # ... more projects
]

rag_contexts = [context_a, context_b, context_c]

prompts = create_batch_rag_prompts(projects, rag_contexts)

# Process all prompts concurrently
import asyncio
reasoner = GLMReasoner()
responses = await asyncio.gather(*[
    reasoner.reason(prompt) for prompt in prompts
])
```

### create_batch_narrative_prompts()
Generate narratives for multiple projects:

```python
from tools.prompt_templates import create_batch_narrative_prompts

qualified_projects = [
    {
        "project_name": "Project A",
        "qualification_percentage": 85.0,
        "qualified_hours": 100,
        "qualified_cost": 12000,
        "confidence_score": 0.88,
        "reasoning": "...",
        "citations": ["..."]
    },
    # ... more projects
]

prompts = create_batch_narrative_prompts(qualified_projects)

# Generate all narratives
narratives = await asyncio.gather(*[
    reasoner.reason(prompt) for prompt in prompts
])
```

## Best Practices

### 1. Always Use Helper Functions
Don't manually format prompts - use the provided helper functions to ensure consistency:

```python
# ✅ Good
prompt = populate_rag_inference_prompt(
    rag_context=context,
    project_name=name,
    # ... other params
)

# ❌ Bad
prompt = RAG_INFERENCE_PROMPT.format(
    rag_context=context,
    project_name=name,
    # ... might miss required params
)
```

### 2. Validate Input Data
Ensure all required fields are present before populating prompts:

```python
required_fields = ["name", "description", "total_hours", "total_cost"]
for field in required_fields:
    if field not in project:
        raise ValueError(f"Missing required field: {field}")

prompt = populate_rag_inference_prompt(...)
```

### 3. Handle JSON Serialization
Use the `default=str` parameter for datetime objects:

```python
import json
from datetime import datetime

data = [
    {
        "date": datetime.now(),
        "hours": 8.5
    }
]

# This will work
json.dumps(data, default=str)
```

### 4. Parse Responses Appropriately
Use the correct parsing method based on expected output:

```python
# For qualification responses
result = reasoner.parse_qualification_response(response)

# For general structured responses
result = reasoner.parse_structured_response(response)

# For narrative text (no parsing needed)
narrative = response  # Already a string
```

## Integration with Other Components

### With RD_Knowledge_Tool
```python
from tools.rd_knowledge_tool import RD_Knowledge_Tool
from tools.prompt_templates import populate_rag_inference_prompt

rag_tool = RD_Knowledge_Tool()
context = rag_tool.query("What is qualified research?")

prompt = populate_rag_inference_prompt(
    rag_context=context.format_for_llm_prompt(),
    # ... other params
)
```

### With GLMReasoner
```python
from tools.glm_reasoner import GLMReasoner
from tools.prompt_templates import populate_narrative_generation_prompt

reasoner = GLMReasoner()
prompt = populate_narrative_generation_prompt(...)
narrative = await reasoner.reason(prompt, temperature=0.3)
```

### With PydanticAI Agents
```python
from pydantic_ai import Agent
from tools.prompt_templates import populate_agent_decision_prompt

# In agent implementation
async def make_decision(self, state):
    prompt = populate_agent_decision_prompt(
        stage_name=self.current_stage,
        agent_state=state.dict(),
        available_actions=self.get_available_actions(),
        context_information=self.get_context(),
        decision_question="What should we do next?"
    )
    
    decision = await self.reasoner.reason(prompt)
    return self.reasoner.parse_structured_response(decision)
```

## Testing

Example test for prompt population:

```python
import pytest
from tools.prompt_templates import populate_rag_inference_prompt

def test_rag_inference_prompt_population():
    prompt = populate_rag_inference_prompt(
        rag_context="Test context",
        project_name="Test Project",
        project_description="Test description",
        technical_activities="Test activities",
        total_hours=100.0,
        total_cost=10000.0
    )
    
    assert "Test Project" in prompt
    assert "Test context" in prompt
    assert "100.0" in prompt
    assert "$10,000.00" in prompt
    assert "four-part test" in prompt
```

## Requirements Mapping

- **Requirement 2.3**: RAG inference prompt for qualification analysis
- **Requirement 4.1**: Narrative generation prompt for technical documentation
- **Requirement 4.3**: Compliance review prompt for quality assurance

## Related Modules

- `tools/glm_reasoner.py`: LLM interface for using these prompts
- `tools/rd_knowledge_tool.py`: RAG context generation
- `agents/qualification_agent.py`: Uses RAG inference prompts
- `agents/audit_trail_agent.py`: Uses narrative and compliance prompts

## Future Enhancements

- Add prompt versioning for A/B testing
- Implement prompt performance metrics
- Add support for custom prompt templates
- Create prompt optimization utilities
