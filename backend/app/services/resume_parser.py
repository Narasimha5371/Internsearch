import re
from io import BytesIO

import pdfplumber
from pydantic import ValidationError

from app.schemas.candidate import CandidateProfile
from app.services.llm_client import generate_candidate_profile_json


EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]

    return "\n".join(text.strip() for text in pages if text.strip())


def _extract_email(raw_text: str) -> str | None:
    match = EMAIL_PATTERN.search(raw_text)
    return match.group(0) if match else None


def _extract_phone(raw_text: str) -> str | None:
    match = PHONE_PATTERN.search(raw_text)
    return match.group(0) if match else None


def _extract_name(raw_text: str) -> tuple[str, str] | None:
    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if "@" in cleaned:
            continue
        if len(cleaned) > 80:
            continue
        tokens = cleaned.split()
        if len(tokens) < 2:
            continue
        return tokens[0], tokens[-1]

    return None


def _extract_skills(raw_text: str) -> list[str]:
    lines = [line.strip() for line in raw_text.splitlines()]
    for idx, line in enumerate(lines):
        if line.lower().startswith("skills"):
            if ":" in line:
                _, chunk = line.split(":", 1)
                return [item.strip() for item in chunk.split(",") if item.strip()]
            if idx + 1 < len(lines):
                return [item.strip() for item in lines[idx + 1].split(",") if item.strip()]

    return []


def _fallback_profile(raw_text: str) -> CandidateProfile:
    email = _extract_email(raw_text)
    if not email:
        raise ValueError("Unable to extract an email address from the resume.")

    name_parts = _extract_name(raw_text)
    if name_parts:
        first_name, last_name = name_parts
    else:
        first_name, last_name = "Unknown", "Unknown"

    return CandidateProfile(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=_extract_phone(raw_text),
        skills=_extract_skills(raw_text),
        experience=[],
    )


async def parse_candidate_profile(raw_text: str) -> CandidateProfile:
    parsed_json = await generate_candidate_profile_json(raw_text)
    if parsed_json:
        try:
            return CandidateProfile.model_validate(parsed_json)
        except ValidationError:
            parsed_json = None

    return _fallback_profile(raw_text)
