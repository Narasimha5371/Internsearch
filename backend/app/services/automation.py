from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from app.core.config import settings
from app.schemas.candidate import CandidateProfile
from app.services.llm_client import generate_form_answer


FIELD_MAP = {
    "first_name": ["first", "given"],
    "last_name": ["last", "family", "surname"],
    "email": ["email"],
    "phone": ["phone", "mobile", "tel"],
    "linkedin_url": ["linkedin"],
    "github_url": ["github"],
    "website_url": ["website", "portfolio"],
    "location": ["location", "city"],
    "headline": ["title", "headline"],
}


async def _fill_selector(page, selector: str, value: str | None, key: str, filled: list[str]) -> None:
    if not value:
        return
    locator = page.locator(selector)
    if await locator.count() == 0:
        return
    await locator.first.fill(value)
    filled.append(key)


async def _fill_greenhouse(page, candidate: CandidateProfile) -> list[str]:
    filled: list[str] = []
    await _fill_selector(page, "input#first_name, input[name='first_name']", candidate.first_name, "first_name", filled)
    await _fill_selector(page, "input#last_name, input[name='last_name']", candidate.last_name, "last_name", filled)
    await _fill_selector(page, "input#email, input[name='email']", candidate.email, "email", filled)
    await _fill_selector(page, "input#phone, input[name='phone']", candidate.phone, "phone", filled)
    await _fill_selector(page, "input[name*='linkedin']", candidate.linkedin_url, "linkedin_url", filled)
    await _fill_selector(page, "input[name*='github']", candidate.github_url, "github_url", filled)
    await _fill_selector(page, "input[name*='website'], input[name*='portfolio']", candidate.website_url, "website_url", filled)
    return filled


async def _fill_lever(page, candidate: CandidateProfile) -> list[str]:
    filled: list[str] = []
    full_name = f"{candidate.first_name} {candidate.last_name}".strip()
    await _fill_selector(page, "input[name='name'], input[aria-label*='name']", full_name, "name", filled)
    await _fill_selector(page, "input[name='email']", candidate.email, "email", filled)
    await _fill_selector(page, "input[name='phone']", candidate.phone, "phone", filled)
    await _fill_selector(page, "input[aria-label*='LinkedIn']", candidate.linkedin_url, "linkedin_url", filled)
    await _fill_selector(page, "input[aria-label*='GitHub']", candidate.github_url, "github_url", filled)
    await _fill_selector(page, "input[aria-label*='Portfolio'], input[aria-label*='Website']", candidate.website_url, "website_url", filled)
    return filled


def _match_field_key(text: str) -> str | None:
    lowered = text.lower()
    for field, keys in FIELD_MAP.items():
        for key in keys:
            if key in lowered:
                return field
    return None


def _field_value(candidate: CandidateProfile, field: str) -> str | None:
    value = getattr(candidate, field, None)
    if value is None:
        return None
    return str(value)


async def _label_for_input(page, input_handle) -> str:
    input_id = await input_handle.get_attribute("id")
    if not input_id:
        return ""

    label = page.locator(f"label[for='{input_id}']")
    if await label.count() == 0:
        return ""

    return (await label.first.inner_text()).strip()


async def _fill_inputs(page, candidate: CandidateProfile) -> list[str]:
    filled_fields: list[str] = []
    inputs = page.locator("input")
    count = await inputs.count()

    for idx in range(count):
        handle = inputs.nth(idx)
        input_type = (await handle.get_attribute("type")) or "text"
        if input_type in {"hidden", "checkbox", "radio", "submit", "button"}:
            continue

        label_text = await _label_for_input(page, handle)
        attrs = " ".join(
            filter(
                None,
                [
                    await handle.get_attribute("name"),
                    await handle.get_attribute("id"),
                    await handle.get_attribute("placeholder"),
                    await handle.get_attribute("aria-label"),
                    label_text,
                ],
            )
        )
        field_key = _match_field_key(attrs)
        if not field_key:
            continue

        value = _field_value(candidate, field_key)
        if not value:
            continue

        await handle.fill(value)
        filled_fields.append(field_key)

    return filled_fields


async def _fill_textareas(page, candidate: CandidateProfile) -> int:
    answered = 0
    textareas = page.locator("textarea")
    count = await textareas.count()
    candidate_json = candidate.model_dump()

    for idx in range(min(count, 8)):
        handle = textareas.nth(idx)
        placeholder = (await handle.get_attribute("placeholder")) or ""
        label_text = await _label_for_input(page, handle)
        question = label_text or placeholder
        if not question:
            question = "Please answer this application question."

        response = await generate_form_answer(candidate_json, question)
        if not response:
            response = "Not provided."

        await handle.fill(response)
        answered += 1

    return answered


async def _attach_resume(page, resume_file_path: str | None) -> bool:
    if not resume_file_path:
        return False

    path = Path(resume_file_path)
    if not path.exists():
        return False

    file_inputs = page.locator("input[type='file']")
    if await file_inputs.count() == 0:
        return False

    await file_inputs.first.set_input_files(str(path))
    return True


async def run_application(
    application_url: str,
    candidate: CandidateProfile,
    resume_file_path: str | None,
    auto_submit: bool,
    artifacts_dir: Path,
) -> dict[str, Any]:
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.playwright_headless)
        page = await browser.new_page()
        await page.goto(application_url, wait_until="domcontentloaded")

        page_text = await page.content()
        if re.search(r"captcha", page_text, re.IGNORECASE):
            await browser.close()
            return {"status": "captcha_detected"}

        domain = application_url.lower()
        filled_fields: list[str] = []
        if "greenhouse" in domain:
            filled_fields.extend(await _fill_greenhouse(page, candidate))
        elif "lever.co" in domain:
            filled_fields.extend(await _fill_lever(page, candidate))

        filled_fields.extend(await _fill_inputs(page, candidate))
        questions_answered = await _fill_textareas(page, candidate)
        resume_attached = await _attach_resume(page, resume_file_path)

        if auto_submit:
            submit = page.locator("button[type='submit'], input[type='submit']")
            if await submit.count() > 0:
                await submit.first.click()
                await page.wait_for_load_state("networkidle")

        screenshot_path = artifacts_dir / "application.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        await browser.close()

    return {
        "status": "completed" if not auto_submit else "submitted",
        "application_url": application_url,
        "fields_filled": list(set(filled_fields)),
        "questions_answered": questions_answered,
        "resume_attached": resume_attached,
        "screenshot": str(screenshot_path),
    }
