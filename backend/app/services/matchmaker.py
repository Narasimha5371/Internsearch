from __future__ import annotations

from pydantic import ValidationError

from app.schemas.candidate import CandidateProfile
from app.schemas.job import JobListing
from app.schemas.match import MatchResult
from app.services.llm_client import generate_match_result_json


def _heuristic_score(candidate: CandidateProfile, job: JobListing) -> MatchResult:
    skills = [skill.lower() for skill in candidate.skills]
    if not skills:
        return MatchResult(match_score=0, reasoning="No skills listed in profile.")

    text = " ".join(
        filter(
            None,
            [
                job.job_title,
                job.description or "",
                " ".join(job.required_skills or []),
            ],
        )
    ).lower()

    hits = sum(1 for skill in skills if skill in text)
    score = int(100 * hits / max(1, len(skills)))
    score = max(0, min(100, score))

    reasoning = f"Matched {hits} of {len(skills)} listed skills in the job description."
    return MatchResult(match_score=score, reasoning=reasoning)


async def score_match(candidate: CandidateProfile, job: JobListing) -> MatchResult:
    llm_payload = await generate_match_result_json(
        candidate=candidate.model_dump(),
        job=job.model_dump(),
    )

    if llm_payload:
        try:
            return MatchResult.model_validate(llm_payload)
        except ValidationError:
            llm_payload = None

    return _heuristic_score(candidate, job)
