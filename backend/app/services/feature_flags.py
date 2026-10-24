"""Feature flags for phased rollout (env overrides)."""

from __future__ import annotations

import os


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, str(default)).strip().lower()
    return raw in ("1", "true", "yes", "on")


def research_llm_enabled() -> bool:
    """Optional LLM rewrite of cite-only Research chat answers."""
    return _flag("RESEARCH_LLM", False)


def llm_extract_enabled() -> bool:
    """Prefer LLM extract when API key present (default on if keyed)."""
    from app.services.llm_client import llm_configured

    if "INTELLENS_LLM_EXTRACT" in os.environ:
        return _flag("INTELLENS_LLM_EXTRACT", False)
    # Also honor legacy RESEARCH_LLM for extract path
    if research_llm_enabled():
        return True
    return llm_configured()


def embeddings_enabled() -> bool:
    """Prefer API embeddings when keyed (default on if keyed)."""
    from app.services.llm_client import llm_configured

    if "INTELLENS_EMBEDDINGS" in os.environ:
        return _flag("INTELLENS_EMBEDDINGS", False)
    return llm_configured()


def consensus_import_enabled() -> bool:
    return _flag("CONSENSUS_IMPORT", True)


def sso_enabled() -> bool:
    return _flag("SSO", False)


def freeze_demo_pad() -> bool:
    """When True, do not pad hand_labeled companies with demo filler."""
    return _flag("FREEZE_DEMO_PAD", True)


def analytics_granger_v1_enabled() -> bool:
    """Tier 3 Granger/LASSO panel — on when PIT warehouse supplies ≥12 points."""
    return _flag("ANALYTICS_GRANGER_V1", True)


def analytics_experimental_ui() -> bool:
    """Proxy corr/impact panel — off by default for external demos."""
    return _flag("ANALYTICS_EXPERIMENTAL_UI", False)


def allow_demo_street() -> bool:
    """When False, Research estimates omit fabricated street consensus."""
    return _flag("ALLOW_DEMO_STREET", False)


def ir_mirror_enabled() -> bool:
    """Corporate IR Mirror ledger mode."""
    return _flag("IR_MIRROR", False)


def portfolio_stretch_enabled() -> bool:
    """P5 stretch endpoints (NCI, workbench) — on in dev, flaggable in prod."""
    return _flag("PORTFOLIO_STRETCH", True)


def sights_enabled() -> bool:
    """CiteAlpha Sights shell SKU — on by default."""
    return _flag("SIGHTS", True)


def sights_deep_dive_enabled() -> bool:
    return _flag("SIGHTS_DEEP_DIVE", True)


def sights_grid_enabled() -> bool:
    return _flag("SIGHTS_GRID", True)


def sights_advanced_enabled() -> bool:
    """Boards/Themes/Street/Field/Deep Dive/Agents/Export — off in production."""
    return _flag("SIGHTS_ADVANCED", False)


def sights_web_assist_enabled() -> bool:
    """Open-web assist beside IR corpus — off until quality gates."""
    return _flag("SIGHTS_WEB_ASSIST", False)


def analyst_llm_enabled() -> bool:
    """CiteAlpha Analyst: optional model-written summary (still verified) — off by default."""
    return _flag("ANALYST_LLM", False)


def analyst_monitors_enabled() -> bool:
    """CiteAlpha Analyst: process new filings for Monitors after each refresh — on by default."""
    return _flag("ANALYST_MONITORS", True)


def gci_version() -> str:
    """Active GCI scorer: ``v3`` (default, exp δ / recency) or legacy ``v2``."""
    from app.services.gci_scoring import scorer_version

    return scorer_version()


def operator_flags() -> list:
    """Jobs a platform operator can see. Labels only — no environment variable names."""
    return [
        {"id": "india_coverage", "label": "India coverage roll", "on": _flag("INTELLENS_INDIA_COVERAGE")},
        {"id": "filing_fetch", "label": "Live filing fetch", "on": _flag("INTELLENS_FILING_LIVE")},
        {"id": "us_coverage", "label": "US coverage roll", "on": _flag("INTELLENS_US_COVERAGE")},
        {"id": "guidance_review", "label": "Guidance review", "on": _flag("INTELLENS_GUIDANCE_REVIEW")},
        {"id": "source_verification", "label": "Source verification", "on": _flag("INTELLENS_VERIFY_SOURCES")},
        {"id": "analyst_monitors", "label": "Analyst monitors", "on": analyst_monitors_enabled()},
        {"id": "event_filings", "label": "Event filings", "on": _flag("ANALYST_EVENT_FILINGS")},
        {"id": "sights_grid", "label": "Compare grid", "on": sights_grid_enabled()},
        {"id": "sights_deep_dive", "label": "Deep dive", "on": sights_deep_dive_enabled()},
    ]


def flags_dict() -> dict:
    from app.services.llm_client import llm_configured

    return {
        "RESEARCH_LLM": research_llm_enabled(),
        "INTELLENS_LLM_EXTRACT": llm_extract_enabled(),
        "INTELLENS_EMBEDDINGS": embeddings_enabled(),
        "LLM_CONFIGURED": llm_configured(),
        "CONSENSUS_IMPORT": consensus_import_enabled(),
        "SSO": sso_enabled(),
        "FREEZE_DEMO_PAD": freeze_demo_pad(),
        "ANALYTICS_GRANGER_V1": analytics_granger_v1_enabled(),
        "ANALYTICS_EXPERIMENTAL_UI": analytics_experimental_ui(),
        "ALLOW_DEMO_STREET": allow_demo_street(),
        "IR_MIRROR": ir_mirror_enabled(),
        "PORTFOLIO_STRETCH": portfolio_stretch_enabled(),
        "SIGHTS": sights_enabled(),
        "SIGHTS_DEEP_DIVE": sights_deep_dive_enabled(),
        "SIGHTS_GRID": sights_grid_enabled(),
        "SIGHTS_ADVANCED": sights_advanced_enabled(),
        "SIGHTS_WEB_ASSIST": sights_web_assist_enabled(),
        "ANALYST_LLM": analyst_llm_enabled(),
        "ANALYST_MONITORS": analyst_monitors_enabled(),
        "INTELLENS_GCI_VERSION": gci_version(),
    }
