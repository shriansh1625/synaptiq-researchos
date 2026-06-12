"""Conditional routing for the research graph."""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END

from app.graphs.state import ResearchState
from app.models.enums import Sufficiency


def route_after_discovery(
    state: ResearchState,
) -> Literal["discovery", "verification", "__end__"]:
    """Route after discovery based on sufficiency and iteration budget."""
    control = state.get("control") or {}
    sufficiency = control.get("sufficiency")
    iteration = int(control.get("iteration", 0))
    max_iterations = int(control.get("max_iterations", 2))
    papers = state.get("papers") or []

    if not papers:
        return END

    if sufficiency == Sufficiency.INSUFFICIENT.value and iteration < max_iterations:
        return "discovery"
    return "verification"


def route_after_verification(
    state: ResearchState,
) -> Literal["discovery", "comparative"]:
    """Route after verification; loop to discovery if claims are too thin."""
    verified_claims = state.get("verified_claims") or []
    control = state.get("control") or {}
    iteration = int(control.get("iteration", 0))
    max_iterations = int(control.get("max_iterations", 2))
    unsupported_ratio = float(control.get("unsupported_ratio", 0.0) or 0.0)
    errors = state.get("errors") or []
    verification_failed = any(error.get("agent") == "verification" for error in errors)

    if verification_failed and not verified_claims:
        return "comparative"
    if len(verified_claims) >= 2:
        return "comparative"
    if iteration >= max_iterations:
        return "comparative"
    if unsupported_ratio > 0.8:
        return "discovery"
    if len(verified_claims) < 2:
        return "discovery"
    return "comparative"
