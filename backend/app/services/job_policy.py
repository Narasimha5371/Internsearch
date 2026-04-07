from __future__ import annotations

from dataclasses import dataclass, field
import re
from urllib.parse import urlparse

INTERNSHIP_HINTS = (
    "intern",
    "internship",
    "co-op",
    "coop",
    "apprentice",
)

PAID_HINTS = (
    "paid internship",
    "paid role",
    "stipend",
    "salary",
    "hourly",
    "compensation",
    "per hour",
    "per week",
    "per month",
    "per year",
)

UNPAID_HINTS = (
    "unpaid",
    "without pay",
    "for college credit",
    "credit only",
    "volunteer",
)

PAY_TO_APPLY_HINTS = (
    "application fee",
    "registration fee",
    "processing fee",
    "training fee",
    "security deposit",
    "refundable deposit",
    "pay to apply",
)

NO_FEE_HINTS = (
    "no application fee",
    "free to apply",
    "no fee",
)

SCAM_HINTS = (
    "wire transfer",
    "crypto",
    "gift card",
    "telegram",
    "whatsapp",
)

MONEY_REGEX = re.compile(r"(?:\$|usd|eur|gbp|cad|aud)\s?\d", re.IGNORECASE)
IPV4_HOST_REGEX = re.compile(r"^\d+\.\d+\.\d+\.\d+$")

LOCAL_HOSTS = {"localhost", "127.0.0.1"}

TRUSTED_ATS_HOSTS = (
    "greenhouse.io",
    "lever.co",
    "workdayjobs.com",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "ashbyhq.com",
    "icims.com",
)


@dataclass(slots=True)
class JobPolicyResult:
    is_internship: bool
    is_legit: bool
    requires_candidate_payment: bool
    is_paid: bool | None
    compensation_summary: str | None
    safety_notes: list[str] = field(default_factory=list)


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _is_trusted_host(host: str) -> bool:
    return any(host == trusted or host.endswith(f".{trusted}") for trusted in TRUSTED_ATS_HOSTS)


def analyze_job(
    title: str,
    description: str | None,
    employment_type: str | None,
    application_url: str,
) -> JobPolicyResult:
    title_text = (title or "").strip().lower()
    description_text = (description or "").strip().lower()
    employment_text = (employment_type or "").strip().lower()
    combined_text = " ".join(part for part in (title_text, description_text, employment_text) if part)

    is_internship = _contains_any(title_text, INTERNSHIP_HINTS) or _contains_any(
        combined_text,
        INTERNSHIP_HINTS,
    )

    looks_paid = _contains_any(combined_text, PAID_HINTS) or bool(MONEY_REGEX.search(combined_text))
    looks_unpaid = _contains_any(combined_text, UNPAID_HINTS)

    is_paid: bool | None
    compensation_summary: str | None
    if looks_unpaid:
        is_paid = False
        compensation_summary = "Marked unpaid in posting"
    elif looks_paid:
        is_paid = True
        compensation_summary = "Paid compensation detected"
    else:
        is_paid = None
        compensation_summary = "Compensation not clearly specified"

    requires_candidate_payment = _contains_any(combined_text, PAY_TO_APPLY_HINTS) and not _contains_any(
        combined_text,
        NO_FEE_HINTS,
    )

    has_scam_signal = _contains_any(combined_text, SCAM_HINTS)

    parsed_url = urlparse(application_url)
    host = (parsed_url.hostname or "").lower()

    invalid_or_local_host = not host or host in LOCAL_HOSTS or bool(IPV4_HOST_REGEX.match(host))
    insecure_transport = parsed_url.scheme.lower() != "https"

    safety_notes: list[str] = []
    if not is_internship:
        safety_notes.append("Posting does not clearly appear to be an internship.")
    if requires_candidate_payment:
        safety_notes.append("Posting appears to require candidate payment to apply.")
    if has_scam_signal:
        safety_notes.append("Posting contains scam-like language (payment app, wire, or chat app prompts).")
    if invalid_or_local_host:
        safety_notes.append("Application host is missing or local/private.")
    if insecure_transport:
        safety_notes.append("Application URL is not HTTPS.")
    if host and not invalid_or_local_host and not _is_trusted_host(host):
        safety_notes.append("Application host is not a known ATS domain; review manually.")

    is_legit = not (requires_candidate_payment or has_scam_signal or invalid_or_local_host or insecure_transport)

    return JobPolicyResult(
        is_internship=is_internship,
        is_legit=is_legit,
        requires_candidate_payment=requires_candidate_payment,
        is_paid=is_paid,
        compensation_summary=compensation_summary,
        safety_notes=safety_notes,
    )
