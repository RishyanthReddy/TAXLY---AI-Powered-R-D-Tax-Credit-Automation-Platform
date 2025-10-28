"""
Test file to verify pytest configuration is working correctly.
This file demonstrates the use of custom markers and can be removed after verification.
"""

import pytest
import asyncio


@pytest.mark.unit
def test_unit_marker_example():
    """Example unit test with unit marker."""
    assert 1 + 1 == 2


@pytest.mark.integration
def test_integration_marker_example():
    """Example integration test with integration marker."""
    assert "hello" + " " + "world" == "hello world"


@pytest.mark.e2e
def test_e2e_marker_example():
    """Example end-to-end test with e2e marker."""
    result = sum([1, 2, 3, 4, 5])
    assert result == 15


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_unit_example():
    """Example async unit test."""
    await asyncio.sleep(0.01)
    assert True


@pytest.mark.slow
def test_slow_marker_example():
    """Example test marked as slow."""
    # Simulate a slow operation
    import time
    time.sleep(0.1)
    assert True


@pytest.mark.api
def test_api_marker_example():
    """Example test marked as API test."""
    # This would normally test API interactions
    assert True


@pytest.mark.rag
def test_rag_marker_example():
    """Example test marked as RAG test."""
    # This would normally test RAG functionality
    assert True


@pytest.mark.pdf
def test_pdf_marker_example():
    """Example test marked as PDF test."""
    # This would normally test PDF generation
    assert True


@pytest.mark.requires_env
def test_requires_env_marker_example():
    """Example test that requires environment variables."""
    # This would normally check for required env vars
    assert True


class TestMarkerCombinations:
    """Test class demonstrating marker combinations."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_combined_markers(self):
        """Test with multiple markers."""
        await asyncio.sleep(0.01)
        assert 2 * 2 == 4

    @pytest.mark.integration
    @pytest.mark.slow
    def test_integration_slow(self):
        """Integration test that is also slow."""
        import time
        time.sleep(0.1)
        assert len([1, 2, 3]) == 3
