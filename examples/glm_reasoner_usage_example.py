"""
GLM Reasoner Usage Examples

This script demonstrates various use cases for the GLMReasoner class.
"""

import asyncio
import logging
from rd_tax_agent.tools.glm_reasoner import GLMReasoner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_basic_reasoning():
    """Example 1: Basic reasoning with GLM 4.5 Air"""
    print("\n" + "="*60)
    print("Example 1: Basic Reasoning")
    print("="*60)
    
    reasoner = GLMReasoner()
    
    prompt = """
    Explain the four-part test for R&D tax credit qualification
    in simple terms.
    """
    
    system_prompt = "You are an expert in IRS R&D tax credit regulations."
    
    response = await reasoner.reason(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2
    )
    
    print(f"\nResponse:\n{response}")


async def example_rag_augmented_reasoning():
    """Example 2: RAG-augmented reasoning"""
    print("\n" + "="*60)
    print("Example 2: RAG-Augmented Reasoning")
    print("="*60)
    
    reasoner = GLMReasoner()
    
    # Simulated RAG context
    rag_context = """
    Source: CFR Title 26 § 1.41-4, Page 3
    The research must be undertaken for the purpose of discovering information
    that is technological in nature, and the application of which is intended
    to be useful in the development of a new or improved business component.
    
    Source: Form 6765 Instructions, Page 5
    Qualified research expenses include wages paid to employees who perform
    qualified services, supplies used in the conduct of qualified research,
    and contract research expenses.
    """
    
    prompt = f"""Based on the following IRS guidance:

{rag_context}

Question: What types of expenses qualify for the R&D tax credit?

Provide a detailed answer with specific citations."""
    
    response = await reasoner.reason(prompt=prompt, temperature=0.2)
    
    print(f"\nResponse:\n{response}")


async def example_qualification_analysis():
    """Example 3: Project qualification analysis"""
    print("\n" + "="*60)
    print("Example 3: Project Qualification Analysis")
    print("="*60)
    
    reasoner = GLMReasoner()
    
    prompt = """Analyze this project for R&D tax credit qualification:

Project Name: AI-Powered Fraud Detection System
Description: Developed a novel machine learning model using deep learning 
techniques to detect fraudulent transactions in real-time. The project involved:
- Research into new neural network architectures
- Experimentation with various feature engineering approaches
- Development of custom algorithms for anomaly detection
- Testing and validation with large datasets

Technical Challenges:
- Achieving high accuracy while minimizing false positives
- Processing transactions in real-time (< 100ms latency)
- Handling imbalanced datasets
- Ensuring model interpretability for compliance

Hours Spent: 2,400 hours
Team Size: 5 engineers

Please provide:
1. Qualification percentage (0-100%)
2. Confidence score (0-1)
3. Detailed reasoning
4. Relevant IRS citations

Format your response as JSON with keys: qualification_percentage, confidence_score, reasoning, citations"""
    
    response = await reasoner.reason(
        prompt=prompt,
        system_prompt="You are an expert in IRS R&D tax credit regulations.",
        temperature=0.2
    )
    
    print(f"\nRaw Response:\n{response}")
    
    # Parse the response
    try:
        qualification_data = reasoner.parse_qualification_response(response)
        print(f"\n--- Parsed Data ---")
        print(f"Qualification: {qualification_data['qualification_percentage']}%")
        print(f"Confidence: {qualification_data['confidence_score']}")
        print(f"Reasoning: {qualification_data['reasoning'][:200]}...")
        print(f"Citations: {qualification_data['citations']}")
    except ValueError as e:
        print(f"\nFailed to parse: {e}")


async def example_natural_language_parsing():
    """Example 4: Natural language response parsing"""
    print("\n" + "="*60)
    print("Example 4: Natural Language Response Parsing")
    print("="*60)
    
    reasoner = GLMReasoner()
    
    # Simulate a natural language response
    natural_response = """
    Based on my analysis, this project qualifies at approximately 75% for the R&D tax credit.
    
    My confidence in this assessment is 0.85 (high confidence).
    
    Reasoning: The project demonstrates clear technological uncertainty in developing
    novel fraud detection algorithms. The experimentation with neural network architectures
    and feature engineering approaches aligns with the four-part test outlined in
    CFR Title 26 § 1.41-4. The technical challenges around real-time processing and
    model interpretability further support R&D qualification.
    
    However, some routine engineering work (data preprocessing, standard model training)
    would not qualify, hence the 75% qualification rate.
    
    Relevant citations: CFR Title 26 § 1.41-4, Form 6765, Publication 542
    """
    
    try:
        qualification_data = reasoner.parse_qualification_response(natural_response)
        print(f"\n--- Parsed from Natural Language ---")
        print(f"Qualification: {qualification_data['qualification_percentage']}%")
        print(f"Confidence: {qualification_data['confidence_score']}")
        print(f"Citations Found: {qualification_data['citations']}")
    except ValueError as e:
        print(f"\nFailed to parse: {e}")


async def example_structured_response_parsing():
    """Example 5: Structured response parsing"""
    print("\n" + "="*60)
    print("Example 5: Structured Response Parsing")
    print("="*60)
    
    reasoner = GLMReasoner()
    
    # Simulate a JSON response
    json_response = """{
        "qualification_percentage": 80,
        "confidence_score": 0.9,
        "reasoning": "This project demonstrates significant R&D activities...",
        "citations": ["CFR Title 26 § 1.41-4", "Form 6765"]
    }"""
    
    try:
        data = reasoner.parse_structured_response(json_response)
        print(f"\n--- Parsed JSON ---")
        print(f"Data: {data}")
    except Exception as e:
        print(f"\nFailed to parse: {e}")


async def example_error_handling():
    """Example 6: Error handling"""
    print("\n" + "="*60)
    print("Example 6: Error Handling")
    print("="*60)
    
    # Test with invalid API key
    try:
        reasoner = GLMReasoner(api_key="invalid_key")
        response = await reasoner.reason("Test prompt")
    except Exception as e:
        print(f"\nExpected error caught: {type(e).__name__}: {e}")
    
    # Test with empty prompt
    try:
        reasoner = GLMReasoner()
        response = await reasoner.reason("")
        print(f"\nEmpty prompt response: {response}")
    except Exception as e:
        print(f"\nError with empty prompt: {e}")


async def example_temperature_comparison():
    """Example 7: Temperature comparison"""
    print("\n" + "="*60)
    print("Example 7: Temperature Comparison")
    print("="*60)
    
    reasoner = GLMReasoner()
    
    prompt = "List three key factors for R&D tax credit qualification."
    
    print("\n--- Low Temperature (0.1) - Deterministic ---")
    response_low = await reasoner.reason(prompt, temperature=0.1)
    print(response_low[:200] + "...")
    
    print("\n--- Medium Temperature (0.5) - Balanced ---")
    response_med = await reasoner.reason(prompt, temperature=0.5)
    print(response_med[:200] + "...")
    
    print("\n--- High Temperature (0.9) - Creative ---")
    response_high = await reasoner.reason(prompt, temperature=0.9)
    print(response_high[:200] + "...")


async def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("GLM Reasoner Usage Examples")
    print("="*60)
    
    try:
        await example_basic_reasoning()
        await example_rag_augmented_reasoning()
        await example_qualification_analysis()
        await example_natural_language_parsing()
        await example_structured_response_parsing()
        await example_temperature_comparison()
        
        # Skip error handling example in normal runs
        # await example_error_handling()
        
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
