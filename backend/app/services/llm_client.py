import json
import re
from typing import Any

import httpx

from app.core.config import settings

MAX_PROMPT_CHARS = 12000


def _build_prompt(raw_text: str) -> str:
    trimmed = raw_text[:MAX_PROMPT_CHARS]
    return (
        "You extract resume data into strict JSON only.\n"
        "Return only JSON with these keys: first_name, last_name, email, phone, location, "
        "headline, summary, github_url, linkedin_url, website_url, skills, education_history, "
        "experience, projects, certifications.\n"
        "Lists must be arrays, unknown values should be null or empty arrays.\n"
        "Resume text:\n<<<\n"
        f"{trimmed}\n"
        ">>>"
    )


def _build_match_prompt(candidate: dict[str, Any], job: dict[str, Any]) -> str:
    candidate_json = json.dumps(candidate, ensure_ascii=True)
    job_json = json.dumps(job, ensure_ascii=True)
    return (
        "You compare a candidate profile to a job listing and return JSON only.\n"
        "Return JSON with keys: match_score (0-100 integer), reasoning (string).\n"
        "Candidate:\n"
        f"{candidate_json}\n"
        "Job:\n"
        f"{job_json}"
    )


def _extract_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    return None


async def _call_ollama(prompt: str) -> str | None:
    url = settings.ollama_host.rstrip("/") + "/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload)
    except httpx.HTTPError:
        return None

    if response.status_code != 200:
        return None

    data = response.json()
    return data.get("response")


async def _call_groq(prompt: str) -> str | None:
    if not settings.groq_api_key:
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    payload = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError:
        return None

    if response.status_code != 200:
        return None

    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        return None

    return choices[0].get("message", {}).get("content")


async def generate_candidate_profile_json(raw_text: str) -> dict[str, Any] | None:
    prompt = _build_prompt(raw_text)
    provider = settings.llm_provider.lower().strip()
    response: str | None = None

    if provider == "ollama":
        response = await _call_ollama(prompt)
        if response is None and settings.groq_api_key:
            response = await _call_groq(prompt)
    elif provider == "groq":
        response = await _call_groq(prompt)
        if response is None:
            response = await _call_ollama(prompt)
    else:
        response = None

    return _extract_json(response or "")


async def generate_match_result_json(
    candidate: dict[str, Any],
    job: dict[str, Any],
) -> dict[str, Any] | None:
    prompt = _build_match_prompt(candidate, job)
    provider = settings.llm_provider.lower().strip()
    response: str | None = None

    if provider == "ollama":
        response = await _call_ollama(prompt)
        if response is None and settings.groq_api_key:
            response = await _call_groq(prompt)
    elif provider == "groq":
        response = await _call_groq(prompt)
        if response is None:
            response = await _call_ollama(prompt)
    else:
        response = None

    return _extract_json(response or "")


def _build_question_prompt(candidate: dict[str, Any], question: str) -> str:
    candidate_json = json.dumps(candidate, ensure_ascii=True)
    return (
        "Answer the job application question using only the candidate data.\n"
        "Be concise, factual, and avoid adding new claims.\n"
        "If data is missing, say 'Not provided.'\n"
        "Candidate:\n"
        f"{candidate_json}\n"
        "Question:\n"
        f"{question}"
    )


async def generate_form_answer(candidate: dict[str, Any], question: str) -> str | None:
    prompt = _build_question_prompt(candidate, question)
    provider = settings.llm_provider.lower().strip()
    response: str | None = None

    if provider == "ollama":
        response = await _call_ollama(prompt)
        if response is None and settings.groq_api_key:
            response = await _call_groq(prompt)
    elif provider == "groq":
        response = await _call_groq(prompt)
        if response is None:
            response = await _call_ollama(prompt)
    else:
        response = None

    return response.strip() if response else None
