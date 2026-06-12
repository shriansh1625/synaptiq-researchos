"""Unit tests for research graph routing."""

from __future__ import annotations

from langgraph.graph import END

from app.graphs.routing import route_after_discovery, route_after_verification
from app.models.enums import Sufficiency


def test_route_after_discovery_loops_when_insufficient() -> None:
    """Discovery should loop when sufficiency is insufficient and budget remains."""
    state = {
        "papers": [{"paper_id": "ss:1"}],
        "control": {"sufficiency": Sufficiency.INSUFFICIENT.value, "iteration": 0, "max_iterations": 2},
    }
    assert route_after_discovery(state) == "discovery"


def test_route_after_discovery_advances_when_sufficient() -> None:
    """Discovery should advance to verification when sufficiency is met."""
    state = {
        "papers": [{"paper_id": "ss:1"}],
        "control": {"sufficiency": Sufficiency.SUFFICIENT.value, "iteration": 0, "max_iterations": 2},
    }
    assert route_after_discovery(state) == "verification"


def test_route_after_discovery_ends_without_papers() -> None:
    """Discovery should end when no papers were found."""
    state = {"papers": [], "control": {}}
    assert route_after_discovery(state) == END


def test_route_after_verification_loops_on_thin_claims() -> None:
    """Verification should loop to discovery when claims are too thin."""
    state = {
        "verified_claims": [{"claim_id": "clm_1"}],
        "control": {"iteration": 0, "max_iterations": 2, "unsupported_ratio": 0.1},
    }
    assert route_after_verification(state) == "discovery"


def test_route_after_verification_advances_with_enough_claims() -> None:
    """Verification should advance to comparative with enough claims."""
    state = {
        "verified_claims": [{"claim_id": "clm_1"}, {"claim_id": "clm_2"}],
        "control": {"iteration": 0, "max_iterations": 2, "unsupported_ratio": 0.2},
    }
    assert route_after_verification(state) == "comparative"


def test_route_after_verification_advances_on_failure() -> None:
    """Verification failures should not loop discovery indefinitely."""
    state = {
        "verified_claims": [],
        "errors": [{"agent": "verification", "message": "failed"}],
        "control": {"iteration": 0, "max_iterations": 2},
    }
    assert route_after_verification(state) == "comparative"
