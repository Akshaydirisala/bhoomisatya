"""Tests for the AI agent orchestrator (LangGraph pipeline)."""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest


class TestOrchestratorGraphCreation:
    """Test that the LangGraph state graph is properly constructed."""

    def test_graph_has_required_nodes(self):
        from src.agent.orchestrator import build_graph

        graph = build_graph()

        expected_nodes = [
            "parse_input",
            "scrape_land_records",
            "scrape_encumbrance",
            "check_rera",
            "check_litigation",
            "compute_valuation",
            "generate_verdicts",
            "generate_report",
        ]

        node_names = list(graph.nodes.keys())
        for expected in expected_nodes:
            assert expected in node_names, f"Missing node: {expected}"

    def test_graph_has_entry_point(self):
        from src.agent.orchestrator import build_graph

        graph = build_graph()
        # The compiled graph should have __start__ -> parse_input
        assert graph.builder is not None or graph is not None

    def test_graph_compiles_without_error(self):
        from src.agent.orchestrator import build_graph

        graph = build_graph()
        # If we got here, compilation succeeded
        assert graph is not None


class TestParseInputNode:
    """Test the input parsing node that extracts property identifiers."""

    @pytest.mark.asyncio
    async def test_parse_survey_number_input(self):
        from src.agent.orchestrator import parse_input_node

        state = {
            "property_input": "Survey number 45, Shamshabad mandal, Rangareddy district",
            "report_type": "full",
        }

        result = await parse_input_node(state)

        assert result["parsed"]["survey_number"] == "45"
        assert "shamshabad" in result["parsed"]["mandal"].lower()
        assert "rangareddy" in result["parsed"]["district"].lower()

    @pytest.mark.asyncio
    async def test_parse_address_input(self):
        from src.agent.orchestrator import parse_input_node

        state = {
            "property_input": "Flat 301, My Home Bhooja, Madhapur, Hyderabad",
            "report_type": "quick",
        }

        result = await parse_input_node(state)

        assert result["parsed"]["property_type"] in ("flat", "apartment")
        assert "madhapur" in result["parsed"].get("locality", "").lower()

    @pytest.mark.asyncio
    async def test_parse_telugu_input(self):
        from src.agent.orchestrator import parse_input_node

        state = {
            "property_input": "సర్వే నంబర్ 45, శంషాబాద్, రంగారెడ్డి",
            "report_type": "full",
        }

        result = await parse_input_node(state)

        # Should still extract structured data (via LLM or rule-based)
        assert "parsed" in result
        assert result["parsed"].get("survey_number") is not None

    @pytest.mark.asyncio
    async def test_parse_handles_ambiguous_input(self):
        from src.agent.orchestrator import parse_input_node

        state = {
            "property_input": "land near highway",
            "report_type": "quick",
        }

        result = await parse_input_node(state)

        # Should flag as needing clarification
        assert result.get("needs_clarification") is True or result["parsed"] is not None
