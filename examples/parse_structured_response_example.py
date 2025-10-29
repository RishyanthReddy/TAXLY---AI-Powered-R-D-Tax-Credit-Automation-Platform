"""
Example usage of GLMReasoner.parse_structured_response() method

This example demonstrates the enhanced response parsing capabilities
that handle various formats including JSON, markdown code blocks,
and natural language key-value pairs.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.glm_reasoner import GLMReasoner


def example_parse_json():
    """Example: Parse direct JSON response"""
    print("=" * 60)
    print("Example 1: Parse Direct JSON Response")
    print("=" * 60)
    
    reasoner = GLMReasoner()
    
    json_response = """{
        "project_name": "ML Model Development",
        "qualification_percentage": 85.5,
        "confidence_score": 0.92,
        "qualified": true
    }"""
    
    result = reasoner.parse_structured_response(json_response)
    
    print(f"Input: {json_response[:50]}...")
    print(f"\nParsed Result:")
    for key, value in result.items():
        print(f"  {key}: {value} ({type(value).__name__})")
    print()


def example_parse_markdown_json():
    """Example: Parse JSON from markdown code block"""
    print("=" * 60)
    print("Example 2: Parse JSON from Markdown Code Block")
    print("=" * 60)
    
    reasoner = GLMReasoner()
    
    markdown_response = """Based on my analysis, here are the results:

```json
{
    "status": "qualified",
    "percentage": 75.0,
    "confidence": 0.88
}
```

This project meets the R&D criteria."""
    
    result = reasoner.parse_structured_response(markdown_response)
    
    print(f"Input: {markdown_response[:80]}...")
    print(f"\nParsed Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    print()


def example_parse_key_value_pairs():
    """Example: Parse key-value pairs from natural language"""
    print("=" * 60)
    print("Example 3: Parse Key-Value Pairs from Natural Language")
    print("=" * 60)
    
    reasoner = GLMReasoner()
    
    nl_response = """
    Project Analysis Results:
    
    project_name: Advanced AI Research
    qualification_percentage: 90
    confidence_score: 0.95
    is_qualified: yes
    risk_level: low
    
    The project demonstrates significant R&D activities.
    """
    
    result = reasoner.parse_structured_response(nl_response)
    
    print(f"Input: {nl_response[:80]}...")
    print(f"\nParsed Result:")
    for key, value in result.items():
        if key != 'content':
            print(f"  {key}: {value} ({type(value).__name__})")
    print()


def example_parse_mixed_format():
    """Example: Parse mixed format with both structured and natural language"""
    print("=" * 60)
    print("Example 4: Parse Mixed Format Response")
    print("=" * 60)
    
    reasoner = GLMReasoner()
    
    mixed_response = """
    Analysis Summary:
    
    status: complete
    confidence: 0.87
    
    The project qualifies for R&D tax credit based on the four-part test.
    Technical uncertainty was demonstrated through novel algorithm development.
    """
    
    result = reasoner.parse_structured_response(mixed_response)
    
    print(f"Input: {mixed_response[:80]}...")
    print(f"\nParsed Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    print()


def example_parse_array():
    """Example: Parse JSON array"""
    print("=" * 60)
    print("Example 5: Parse JSON Array")
    print("=" * 60)
    
    reasoner = GLMReasoner()
    
    array_response = '[{"project": "A", "score": 85}, {"project": "B", "score": 92}]'
    
    result = reasoner.parse_structured_response(array_response)
    
    print(f"Input: {array_response}")
    print(f"\nParsed Result:")
    print(f"  Type: {type(result).__name__}")
    print(f"  Length: {len(result)}")
    for i, item in enumerate(result):
        print(f"  Item {i}: {item}")
    print()


def example_error_handling():
    """Example: Error handling for malformed responses"""
    print("=" * 60)
    print("Example 6: Error Handling for Malformed Responses")
    print("=" * 60)
    
    reasoner = GLMReasoner()
    
    # Test with invalid JSON
    invalid_json = "{invalid: json, missing: quotes}"
    result = reasoner.parse_structured_response(invalid_json)
    
    print(f"Input (invalid JSON): {invalid_json}")
    print(f"Parsed Result (fallback to content): {result}")
    print()
    
    # Test with empty response
    try:
        reasoner.parse_structured_response("")
    except ValueError as e:
        print(f"Empty response error: {e}")
    print()


async def example_real_llm_parsing():
    """Example: Parse real LLM response"""
    print("=" * 60)
    print("Example 7: Parse Real LLM Response")
    print("=" * 60)
    
    reasoner = GLMReasoner()
    
    # Get a real response from GLM 4.5 Air
    prompt = """Analyze this R&D project and respond in JSON format:

Project: Machine Learning Model for Fraud Detection
Description: Developed novel neural network architecture

Provide: qualification_percentage, confidence_score, reasoning"""
    
    try:
        response = await reasoner.reason(prompt, temperature=0.2)
        print(f"Raw LLM Response:\n{response[:200]}...\n")
        
        # Parse the response
        parsed = reasoner.parse_structured_response(response)
        
        print("Parsed Result:")
        for key, value in parsed.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error: {e}")
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("GLMReasoner parse_structured_response() Examples")
    print("=" * 60 + "\n")
    
    # Run synchronous examples
    example_parse_json()
    example_parse_markdown_json()
    example_parse_key_value_pairs()
    example_parse_mixed_format()
    example_parse_array()
    example_error_handling()
    
    # Run async example
    print("\nRunning async example with real LLM...")
    asyncio.run(example_real_llm_parsing())
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
