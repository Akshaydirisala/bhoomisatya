"""LangGraph state machine orchestrator for BhoomiSatya property verification."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Optional

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.agent.prompts import ANALYSIS_PROMPT, SYSTEM_PROMPT
from src.agent.tools import (
    check_court_cases,
    check_encumbrance,
    check_land_records,
    get_satellite_image,
    get_valuation_data,
    search_rera_project,
)

logger = structlog.get_logger(__name__)


class AgentState(TypedDict, total=False):
    """State for the BhoomiSatya verification pipeline."""

    messages: list[dict[str, Any]]
    property_input: dict[str, Any]
    land_records: Optional[dict[str, Any]]
    rera_data: Optional[dict[str, Any]]
    court_cases: Optional[dict[str, Any]]
    encumbrance_data: Optional[dict[str, Any]]
    valuation_data: Optional[dict[str, Any]]
    satellite_info: Optional[dict[str, Any]]
    trust_score: Optional[int]
    safety_verdict: Optional[str]
    valuation_verdict: Optional[str]
    report_id: Optional[str]
    report_type: Optional[str]
    error: Optional[str]


# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------

llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0, max_tokens=4096)

TOOLS = [
    check_land_records,
    check_encumbrance,
    check_court_cases,
    search_rera_project,
    get_valuation_data,
    get_satellite_image,
]

llm_with_tools = llm.bind_tools(TOOLS)


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


async def parse_input(state: AgentState) -> AgentState:
    """Extract structured property details from user message."""
    log = logger.bind(node="parse_input")

    prop = state.get("property_input", {})
    if not prop:
        log.error("no_property_input")
        return {**state, "error": "No property input provided."}

    report_id = str(uuid.uuid4())
    report_type = state.get("report_type", "full")
    log.info("input_parsed", report_id=report_id, report_type=report_type)

    return {**state, "report_id": report_id, "report_type": report_type}


async def run_safety_checks(state: AgentState) -> AgentState:
    """Run land records, RERA, court cases, and encumbrance checks in parallel."""
    log = logger.bind(node="run_safety_checks", report_id=state.get("report_id"))
    prop = state["property_input"]

    survey_number = prop.get("survey_number", "")
    district = prop.get("district", "")
    mandal = prop.get("mandal", "")
    village = prop.get("village", "")
    state_name = prop.get("state", "telangana")
    owner_name = prop.get("owner_name", "")
    project_name = prop.get("project_name", "")
    from_year = prop.get("from_year", 2000)
    to_year = prop.get("to_year", 2025)

    log.info("running_safety_checks")

    tasks = [
        check_land_records.ainvoke(
            {
                "survey_number": survey_number,
                "district": district,
                "mandal": mandal,
                "village": village,
                "state": state_name,
            }
        ),
        check_court_cases.ainvoke(
            {
                "party_name": owner_name,
                "state": state_name,
                "district": district,
            }
        ),
        check_encumbrance.ainvoke(
            {
                "survey_number": survey_number,
                "district": district,
                "village": village,
                "state": state_name,
                "from_year": from_year,
                "to_year": to_year,
            }
        ),
    ]

    if project_name:
        tasks.append(
            search_rera_project.ainvoke(
                {
                    "project_name_or_rera_number": project_name,
                    "state": state_name,
                }
            )
        )

    tasks.append(
        get_satellite_image.ainvoke(
            {
                "village": village,
                "mandal": mandal,
                "district": district,
                "state": state_name,
            }
        )
    )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    def _safe_parse(val: Any) -> Any:
        if isinstance(val, Exception):
            return {"error": str(val)}
        if isinstance(val, str):
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return {"raw": val}
        return val

    land_records = _safe_parse(results[0])
    court_cases = _safe_parse(results[1])
    encumbrance_data = _safe_parse(results[2])

    idx = 3
    rera_data: Any = None
    if project_name:
        rera_data = _safe_parse(results[idx])
        idx += 1

    satellite_info = _safe_parse(results[idx]) if idx < len(results) else None

    log.info("safety_checks_complete")
    return {
        **state,
        "land_records": land_records,
        "court_cases": court_cases,
        "encumbrance_data": encumbrance_data,
        "rera_data": rera_data,
        "satellite_info": satellite_info,
    }


async def run_valuation_checks(state: AgentState) -> AgentState:
    """Fetch guideline values and comparable sales data."""
    log = logger.bind(node="run_valuation_checks", report_id=state.get("report_id"))
    prop = state["property_input"]

    log.info("running_valuation_checks")
    result = await get_valuation_data.ainvoke(
        {
            "district": prop.get("district", ""),
            "mandal": prop.get("mandal", ""),
            "village": prop.get("village", ""),
            "state": prop.get("state", "telangana"),
        }
    )

    valuation_data: Any
    if isinstance(result, str):
        try:
            valuation_data = json.loads(result)
        except json.JSONDecodeError:
            valuation_data = {"raw": result}
    else:
        valuation_data = result

    log.info("valuation_checks_complete")
    return {**state, "valuation_data": valuation_data}


async def analyze(state: AgentState) -> AgentState:
    """Call the LLM with all collected data to produce trust score and verdicts."""
    log = logger.bind(node="analyze", report_id=state.get("report_id"))
    prop = state["property_input"]

    analysis_input = ANALYSIS_PROMPT.format(
        land_records=json.dumps(state.get("land_records"), ensure_ascii=False, default=str),
        rera_data=json.dumps(state.get("rera_data"), ensure_ascii=False, default=str),
        court_cases=json.dumps(state.get("court_cases"), ensure_ascii=False, default=str),
        encumbrance_data=json.dumps(state.get("encumbrance_data"), ensure_ascii=False, default=str),
        valuation_data=json.dumps(state.get("valuation_data"), ensure_ascii=False, default=str),
        satellite_info=json.dumps(state.get("satellite_info"), ensure_ascii=False, default=str),
        asking_price=prop.get("asking_price", "Not provided"),
    )

    log.info("calling_llm_for_analysis")
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=analysis_input),
    ]

    response = await llm_with_tools.ainvoke(messages)
    content = response.content if isinstance(response, AIMessage) else str(response)

    # Parse LLM JSON output
    analysis: dict[str, Any] = {}
    try:
        # Try to extract JSON from the response
        if isinstance(content, str):
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                analysis = json.loads(content[start:end])
    except json.JSONDecodeError:
        log.warning("llm_json_parse_failed", content_preview=str(content)[:200])

    trust_score = analysis.get("trust_score", 50)
    safety_verdict = analysis.get("safety_verdict", "CAUTION")
    valuation_verdict = analysis.get("valuation_verdict", "INSUFFICIENT_DATA")

    log.info(
        "analysis_complete",
        trust_score=trust_score,
        safety_verdict=safety_verdict,
        valuation_verdict=valuation_verdict,
    )

    return {
        **state,
        "trust_score": trust_score,
        "safety_verdict": safety_verdict,
        "valuation_verdict": valuation_verdict,
        "messages": state.get("messages", []) + [{"role": "assistant", "analysis": analysis}],
    }


async def generate_report_node(state: AgentState) -> AgentState:
    """Generate a PDF report from the analysis results."""
    log = logger.bind(node="generate_report", report_id=state.get("report_id"))
    try:
        from src.agent.report_generator import generate_pdf, save_report

        report_data = {
            "report_id": state.get("report_id"),
            "property_input": state.get("property_input"),
            "land_records": state.get("land_records"),
            "rera_data": state.get("rera_data"),
            "court_cases": state.get("court_cases"),
            "encumbrance_data": state.get("encumbrance_data"),
            "valuation_data": state.get("valuation_data"),
            "satellite_info": state.get("satellite_info"),
            "trust_score": state.get("trust_score"),
            "safety_verdict": state.get("safety_verdict"),
            "valuation_verdict": state.get("valuation_verdict"),
        }

        log.info("generating_pdf")
        pdf_bytes = await generate_pdf(report_data)
        file_path = await save_report(state["report_id"], pdf_bytes)  # type: ignore[arg-type]
        log.info("pdf_generated", path=file_path)

    except Exception as exc:
        log.error("report_generation_failed", error=str(exc))

    return state


async def respond(state: AgentState) -> AgentState:
    """Format a final WhatsApp-friendly response message."""
    log = logger.bind(node="respond", report_id=state.get("report_id"))

    verdict_emoji = {
        "SAFE": "✅",
        "CAUTION": "⚠️",
        "UNSAFE": "🚫",
    }
    price_label = {
        "FAIR_PRICE": "Fair Price",
        "OVERPRICED": "Overpriced",
        "UNDERPRICED": "Underpriced",
        "INSUFFICIENT_DATA": "Insufficient Data",
    }

    safety = state.get("safety_verdict", "CAUTION")
    score = state.get("trust_score", 0)
    valuation = state.get("valuation_verdict", "INSUFFICIENT_DATA")

    reply = (
        f"{verdict_emoji.get(safety, '')} *BhoomiSatya Verification Result*\n\n"
        f"*Trust Score:* {score}/100\n"
        f"*Safety Verdict:* {safety}\n"
        f"*Price Verdict:* {price_label.get(valuation, valuation)}\n\n"
        f"Your detailed PDF report is being prepared. "
        f"Report ID: `{state.get('report_id')}`"
    )

    log.info("response_formatted")
    messages = state.get("messages", [])
    messages.append({"role": "assistant", "content": reply})
    return {**state, "messages": messages}


# ---------------------------------------------------------------------------
# Conditional edge
# ---------------------------------------------------------------------------


def should_skip_valuation(state: AgentState) -> str:
    """Route: skip valuation for quick_check reports."""
    if state.get("report_type") == "quick_check":
        return "analyze"
    return "run_valuation_checks"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    """Construct and return the compiled BhoomiSatya verification graph."""
    graph = StateGraph(AgentState)

    graph.add_node("parse_input", parse_input)
    graph.add_node("run_safety_checks", run_safety_checks)
    graph.add_node("run_valuation_checks", run_valuation_checks)
    graph.add_node("analyze", analyze)
    graph.add_node("generate_report", generate_report_node)
    graph.add_node("respond", respond)

    graph.set_entry_point("parse_input")

    graph.add_edge("parse_input", "run_safety_checks")
    graph.add_conditional_edges(
        "run_safety_checks",
        should_skip_valuation,
        {
            "run_valuation_checks": "run_valuation_checks",
            "analyze": "analyze",
        },
    )
    graph.add_edge("run_valuation_checks", "analyze")
    graph.add_edge("analyze", "generate_report")
    graph.add_edge("generate_report", "respond")
    graph.add_edge("respond", END)

    return graph


checkpointer = MemorySaver()
compiled_graph = build_graph().compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_verification(
    property_input: dict[str, Any], report_type: str = "full"
) -> dict[str, Any]:
    """Run the full property verification pipeline.

    Args:
        property_input: Dict with survey_number, district, mandal, village,
            state, owner_name, project_name (optional), asking_price, etc.
        report_type: 'full' or 'quick_check'. Quick check skips valuation.

    Returns:
        Final agent state dict with verdicts, trust score, and report_id.
    """
    log = logger.bind(report_type=report_type)
    log.info("verification_started", property=property_input)

    initial_state: AgentState = {
        "messages": [],
        "property_input": property_input,
        "report_type": report_type,
    }

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    final_state = await compiled_graph.ainvoke(initial_state, config=config)

    log.info(
        "verification_complete",
        trust_score=final_state.get("trust_score"),
        safety_verdict=final_state.get("safety_verdict"),
    )
    return dict(final_state)
