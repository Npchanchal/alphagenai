from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CompanySummary(BaseModel):
    id: str
    name: str
    ticker: str
    sector: str
    gci_score: Optional[float]
    data_quality: str = "demo_structured"
    peer_rank_in_sector: Optional[int] = None
    sector_avg_gci: Optional[float] = None
    gci_change_pct: Optional[float] = None
    gci_change_horizon: Optional[str] = None
    wow_pct: Optional[float] = None
    mom_pct: Optional[float] = None
    qoq_pct: Optional[float] = None
    yoy_pct: Optional[float] = None
    market_id: Optional[str] = None
    index_ids: Optional[List[str]] = None
    # Index integrity (W1.3): every published number carries its confidence + provenance.
    confidence_tier: Optional[str] = Field(
        default=None, description="provisional | established | deep; null when not scored"
    )
    closed_periods: int = 0
    metrics_scored: int = 0
    as_of: Optional[str] = Field(default=None, description="Latest reviewed outcome date")
    algorithm_id: Optional[str] = None
    coverage_status: Optional[str] = Field(
        default=None,
        description="scored | open_period | filing_in_review | no_quantified_guidance | listed_only",
    )
    coverage_reason: Optional[str] = Field(
        default=None,
        description="Plain sentence shown instead of a number, e.g. 'First guided year (FY27) closes Mar 2027'",
    )


class AuthRegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""
    preferences: Optional[Dict[str, Any]] = None
    guest_token: Optional[str] = None
    accept_terms: bool = False
    account_type: str = "b2b"  # b2b desk; retail only after sebi_retail attest
    org_name: Optional[str] = None
    org_id: Optional[str] = None
    challenge_id: Optional[str] = None
    challenge_answer: Optional[str] = None


class AuthLoginRequest(BaseModel):
    email: str
    password: str
    totp_code: Optional[str] = None


class AuthMfaConfirmRequest(BaseModel):
    code: str


class AuthGuestRequest(BaseModel):
    accept_terms: bool = False
    challenge_id: Optional[str] = None
    challenge_answer: Optional[str] = None


class LegalAttestRequest(BaseModel):
    kind: str  # terms_privacy | sebi_retail
    attested_by: str
    note: str = ""


class PlatformAdminRoleRequest(BaseModel):
    platform_admin_role: Optional[str] = None  # super | ops | compliance | billing | support | null


class MsaInvoiceRequest(BaseModel):
    plan: str = "desk"
    seats: int = 5
    amount_inr: Optional[float] = None
    po_number: Optional[str] = None
    conversion_path: Optional[str] = None  # "pilot_to_desk" → create_msa_from_pilot
    from_pilot: bool = False


class MsaSignRequest(BaseModel):
    signer_email: str


class RetailCheckoutRequest(BaseModel):
    pass


class RetailPayConfirm(BaseModel):
    order_id: str
    payment_ref: str = "upi-demo"


class AuthEmailRequest(BaseModel):
    email: str


class AuthVerifyConfirm(BaseModel):
    token: str


class AuthPasswordResetConfirm(BaseModel):
    token: str
    password: str


class OrgInviteRequest(BaseModel):
    email: str
    role: str = "member"


class OrgRevokeRequest(BaseModel):
    user_id: str


class OrgOidcRequest(BaseModel):
    oidc_issuer: Optional[str] = None
    oidc_client_id: Optional[str] = None
    email_domain: Optional[str] = None


class AcceptInviteRequest(BaseModel):
    token: str
    password: str
    name: str = ""
    accept_terms: bool = False


class PreferencesUpdate(BaseModel):
    language: Optional[str] = None
    default_market: Optional[str] = None
    default_index: Optional[str] = None
    watchlist: Optional[List[str]] = None
    show_demo_tape: Optional[bool] = None
    density: Optional[str] = None
    saved_queries: Optional[List[str]] = None
    analytics_consent: Optional[bool] = None


class MemberRoleRequest(BaseModel):
    role: str
    company_scope: Optional[List[str]] = None


class FeedbackCreate(BaseModel):
    company_id: Optional[str] = None
    period: Optional[str] = None
    metric: Optional[str] = None
    kind: str
    comment: str = ""
    nps: Optional[int] = None


class PilotRequestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    firm: str = Field(min_length=1, max_length=200)
    role: str = Field(default="", max_length=120)
    team_size: str = Field(default="", max_length=40)
    message: str = Field(default="", max_length=4000)
    challenge_id: Optional[str] = None
    challenge_answer: Optional[str] = None


class PilotRequestReview(BaseModel):
    action: str = Field(description="approve or reject")
    note: str = Field(default="", max_length=1000)
    term_days: Optional[int] = Field(
        default=None,
        description="Required on approve: 30, 45, or 60",
    )


class SetAuditFlagRequest(BaseModel):
    flag: str
    source_url: str = ""
    note: str = ""


class LabelDraftRequest(BaseModel):
    company_id: str
    ticker: Optional[str] = None
    period: str = "FY"
    metric: str = "revenue_growth_pct"
    guided_low: Optional[float] = None
    guided_high: Optional[float] = None
    guided_value: Optional[float] = None
    actual_value: Optional[float] = None
    dropped: bool = False
    guided_text: str = ""
    quote_span: Optional[str] = None
    source_url: Optional[str] = None
    source_ref: Optional[str] = None
    source_type: str = "ir_html"
    as_of: Optional[str] = None
    speaker: Optional[str] = None
    thread_id: Optional[str] = None
    confidence: float = 0.85
    notes: Optional[str] = None
    guidance_source_url: Optional[str] = None
    guidance_source_ref: Optional[str] = None
    guidance_quote: Optional[str] = None
    guidance_as_of: Optional[str] = None


class LabelImportRequest(BaseModel):
    csv: str


class LabelRejectRequest(BaseModel):
    comment: str = ""


class GuidanceRevision(BaseModel):
    as_of: str
    guided_low: float
    guided_high: float
    source_url: Optional[str] = None
    source_ref: Optional[str] = None
    quote: Optional[str] = None


class OutcomeView(BaseModel):
    period: str
    metric: str
    outcome_index: Optional[int] = Field(
        default=None,
        description="Position in the stored outcome list. Review writes use this, not the display order.",
    )
    guided_value: float
    guided_low: Optional[float] = None
    guided_high: Optional[float] = None
    actual_value: Optional[float]
    delta_pct: Optional[float]
    guided_text: str
    confidence: float
    speaker: str
    contribution_score: Optional[float]
    label: str
    thread_id: Optional[str] = None
    source_url: Optional[str] = None
    source_ref: Optional[str] = None
    quote_span: Optional[str] = None
    as_of: Optional[str] = None
    guidance_source_url: Optional[str] = None
    guidance_source_ref: Optional[str] = None
    guidance_quote: Optional[str] = None
    guidance_as_of: Optional[str] = None
    revisions: List[GuidanceRevision] = Field(default_factory=list)
    revision_direction: Optional[str] = Field(
        default=None, description="raised | cut | unchanged — final vs opening band"
    )
    final_guided_low: Optional[float] = None
    final_guided_high: Optional[float] = None
    final_label: Optional[str] = Field(
        default=None, description="Outcome against the last revised band (not scored)"
    )
    dropped: bool = False
    actual_change_pct: Optional[float] = None
    actual_change_horizon: Optional[str] = None
    guided_change_pct: Optional[float] = None
    guided_change_horizon: Optional[str] = None
    citation_id: Optional[str] = None
    doc_id: Optional[str] = None
    citeable: bool = False
    cite_reason: Optional[str] = None
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    reporting_basis: Optional[str] = None
    actual_reporting_basis: Optional[str] = None
    unit: Optional[str] = None
    actual_unit: Optional[str] = None
    scope: Optional[str] = None
    actual_scope: Optional[str] = None
    evidence_hashes: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description=(
            "SHA-256 of the guidance quote, the results quote and the stored filing, "
            "plus when we ingested the filing. Look up a filing by hash at "
            "/api/v1/index/evidence."
        ),
    )


class CompanyGCIDetail(BaseModel):
    id: str
    name: str
    ticker: str
    sector: str
    gci_score: Optional[float]
    status: str = Field(description="ok | insufficient_data")
    data_quality: str
    by_metric: Dict[str, float] = Field(description="Metrics in the composite")
    context_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Metrics with < 2 closed periods — shown, not in the composite",
    )
    periods_by_metric: Dict[str, int] = Field(default_factory=dict)
    composite_weights: Dict[str, float] = Field(default_factory=dict)
    label_counts: Dict[str, int]
    outcomes: List[OutcomeView]
    trend: List[Dict[str, Any]]
    peer_rank_in_sector: Optional[int] = None
    sector_avg_gci: Optional[float] = None
    threads: Dict[str, List[OutcomeView]] = Field(default_factory=dict)
    gci_change_pct: Optional[float] = None
    # Index integrity (W1.3)
    confidence_tier: Optional[str] = None
    closed_periods: int = 0
    metrics_scored: int = 0
    as_of: Optional[str] = None
    algorithm_id: Optional[str] = None
    coverage_status: Optional[str] = None
    coverage_reason: Optional[str] = None
    reviewed_at: Optional[str] = None
    gci_change_horizon: Optional[str] = None
    by_metric_changes: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    # Audit / red-alert layer (v3 deductions — not forensic Beneish)
    audit_flags: List[str] = Field(default_factory=list)
    audit_deduction: float = 0.0
    audit_badges: List[Dict[str, Any]] = Field(default_factory=list)
    red_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    revision_timeline: List[Dict[str, Any]] = Field(default_factory=list)
    revision_summaries: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="In-year revision count, direction, and average move. Not part of GCI.",
    )
    guidance_profile: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Results vs guided range, in-year revision pattern, revenue/margin divergences. "
            "Counts always; labels from 6 closed figures. Not part of GCI."
        ),
    )
    audit_note: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str = "0.5.2"


class ExtractRequest(BaseModel):
    company_id: str
    text: Optional[str] = None
    period: str = "FY26"
    source_ref: str = "upload"


class AnalystRunRequest(BaseModel):
    skill_id: str
    company_id: str
    include_unreviewed: bool = False
    project_id: Optional[str] = None


class AnalystProjectRequest(BaseModel):
    name: str = Field(..., max_length=120)
    company_ids: List[str] = Field(default_factory=list)


class AnalystProjectPatch(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    company_ids: Optional[List[str]] = None


class AnalystMemoryRequest(BaseModel):
    text: str = Field(..., max_length=500)


class AnalystUploadRequest(BaseModel):
    filename: str = Field(..., max_length=200)
    content_base64: str = Field(..., max_length=14_500_000)


class AnalystOrgKeyRequest(BaseModel):
    label: str = Field("API key", max_length=80)
    role: Literal["analyst", "viewer"] = "analyst"


class AnalystDestinationRequest(BaseModel):
    kind: Literal["webhook", "slack", "teams"]
    url: str = Field(..., max_length=2000)
    events: List[str] = Field(default_factory=lambda: ["monitor.run", "digest.weekly"])
    label: Optional[str] = Field(None, max_length=80)


class PublicRunRequest(BaseModel):
    skill_id: str
    company_id: str
    project_id: Optional[str] = None


class AnalystHouseStyleRequest(BaseModel):
    firm_name: str = Field("", max_length=80)
    primary_color: str = Field("#0B3D5C", pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_color: str = Field("#C8102E", pattern=r"^#[0-9A-Fa-f]{6}$")
    font: Literal["Arial", "Calibri", "Georgia", "Helvetica", "Times New Roman", "Verdana"] = "Arial"
    footer: str = Field("", max_length=160)
    classification: str = Field("", max_length=60)
    logo_base64: Optional[str] = Field(None, max_length=700_000)


class AnalystHouseTemplateRequest(BaseModel):
    filename: str = Field(..., max_length=200, pattern=r"(?i)\.(pptx|potx)$")
    content_base64: str = Field(..., max_length=7_000_000)


class AnalystDigestRequest(BaseModel):
    enabled: bool = True
    emails: List[str] = Field(default_factory=list, max_length=10)


class AnalystMonitorRequest(BaseModel):
    skill_id: str
    scope: Literal["company", "watchlist", "project"] = "company"
    company_id: Optional[str] = None
    project_id: Optional[str] = None
    email: Optional[str] = Field(None, max_length=254)


class CommitmentProposal(BaseModel):
    company_id: str
    type: str
    subject: str
    outcome: str
    due_period: str
    quote: str
    source_url: str
    as_of: str
    doc_id: Optional[str] = None
    speaker: Optional[str] = None


class CommitmentProposeRequest(BaseModel):
    commitments: List[CommitmentProposal]


class CommitmentExtractRequest(BaseModel):
    doc_id: Optional[str] = None
    company_id: Optional[str] = None
    text: Optional[str] = None
    source_url: Optional[str] = None
    as_of: Optional[str] = None
    use_llm: Optional[bool] = None


class CommitmentReviewRequest(BaseModel):
    decision: str = Field(description="accepted | rejected")
    edits: Dict[str, Any] = Field(default_factory=dict)
    note: str = ""


class CommitmentTransitionRequest(BaseModel):
    new_state: str
    proof: Dict[str, Any] = Field(default_factory=dict)


class MatchRequest(BaseModel):
    statements: List[Dict[str, Any]]
    actuals: List[Dict[str, Any]]


class ImportFactsRequest(BaseModel):
    facts: List[Dict[str, Any]]
    merge_into_company: Optional[str] = None
    allow_custom: bool = False


class IngestMediaRequest(BaseModel):
    company_id: str
    media_type: str  # audio | video
    note: Optional[str] = None
    title: Optional[str] = None


class ActualsImportRequest(BaseModel):
    rows: List[Dict[str, Any]]
    allow_custom: bool = False


class ReviewRequest(BaseModel):
    company_id: str
    outcome_index: int
    action: str  # accept | edit | reject
    comment: Optional[str] = None
    edits: Optional[Dict[str, Any]] = None


class AlertItem(BaseModel):
    company_id: str
    ticker: str
    kind: str
    message: str
    severity: str
    period: Optional[str] = None
    metric: Optional[str] = None
    source_url: Optional[str] = None
    audit_flag: Optional[str] = None
    deduction_pts: Optional[float] = None


class PitPoint(BaseModel):
    as_of: str
    gci_score: Optional[float]
    prior_gci: Optional[float] = None
    change_pct: Optional[float] = None
    change_horizon: Optional[str] = None


class ResearchChatRequest(BaseModel):
    question: str
    company_id: Optional[str] = None
    expand: bool = False


class SightsAskRequest(BaseModel):
    question: str
    company_id: Optional[str] = None
    web_assist: bool = False


class SightsGridRequest(BaseModel):
    prompts: List[str]
    company_ids: Optional[List[str]] = None


class SightsDeepDiveRequest(BaseModel):
    topic: str
    company_id: Optional[str] = None


class IngestPasteRequest(BaseModel):
    company_id: str
    text: str
    title: str = "Pasted transcript"
    doc_type: str = "transcript"


class IngestUrlRequest(BaseModel):
    company_id: str
    url: str
    title: Optional[str] = None


class CommitExtractRequest(BaseModel):
    extract_id: str
    accepted_indices: List[int]
    # Optional per-statement corrections applied before commit,
    # keyed by statement index: {0: {"guided_low": 6, "guided_high": 8}}
    edits: Optional[Dict[int, Dict[str, Any]]] = None


class ConsensusImportRequest(BaseModel):
    rows: List[Dict[str, Any]]


class DocReviewRequest(BaseModel):
    doc_id: str
    action: str  # accept | reject


class DocDateRequest(BaseModel):
    as_of: str  # YYYY-MM-DD
    evidence: str  # verbatim snippet of the stored text, title or URL
    basis: str  # call_or_meeting_date | document_date | board_signing_date | cover_letter_date
    reviewer: str


class CrawlRequest(BaseModel):
    limit: int = 30
    dry_run: bool = False
    live: bool = False
    company_ids: Optional[List[str]] = None


class RefreshRequest(BaseModel):
    limit: int = 30
    live: Optional[bool] = None
    auto_extract: Optional[bool] = None
    warm_fmp: Optional[bool] = None
