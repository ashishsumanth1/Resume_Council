"""Build compact packs (token-saving context) from raw inputs."""

from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List


_STOPWORDS = {
    "the", "and", "or", "to", "of", "in", "for", "a", "an", "on", "with", "as", "at",
    "by", "is", "are", "be", "this", "that", "you", "we", "our", "your", "from", "will",
    "must", "should", "can", "may", "have", "has", "had", "i", "me", "my", "their", "they",
    "it", "its", "into", "over", "within", "across", "etc",
}


def compact_text(text: str, max_chars: int) -> str:
    t = (text or "").strip()
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 120].rstrip() + "\n\n[TRUNCATED FOR BUDGET]"


def normalize_text(text: str) -> str:
    t = (text or "").strip()
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


def _extract_section(text: str, section_name: str) -> str:
    """Extract a section by heading name (best-effort, markdown/plaintext)."""
    lines = (text or "").splitlines()

    def _normalize_heading(line: str) -> str:
        s = (line or "").strip()
        # Strip markdown heading markers.
        if s.startswith("#"):
            s = s.lstrip("#").strip()
        # Strip common trailing punctuation.
        s = s.rstrip(":").rstrip("-").rstrip("–").rstrip("—").strip()
        return s.lower()

    target = section_name.strip().lower()
    known_headings = {
        "summary",
        "education",
        "technical skills",
        "skills",
        "professional experience",
        "experience",
        "projects",
        "certifications",
    }

    start = None
    for i, line in enumerate(lines):
        if _normalize_heading(line) == target:
            start = i
            break
    if start is None:
        return ""

    out = [lines[start].strip()]
    for j in range(start + 1, len(lines)):
        if _normalize_heading(lines[j]) in known_headings:
            break
        out.append(lines[j].rstrip())

    section = "\n".join(out).strip()
    # Best-effort: return whatever we captured, even if sparse.
    # Downstream code can decide whether to use it.
    return section


def extract_profile_section(text: str, section_name: str) -> str:
    """Public wrapper for best-effort section extraction."""
    return _extract_section(text, section_name)


def build_profile_pack(master_profile: str, max_chars: int | None = 60000) -> str:
    """A compact, reusable truth source.

    Note: If this is too aggressively truncated, downstream models may think
    sections like Projects/Certifications are missing and omit them.
    """
    raw = master_profile or ""
    if max_chars is None:
        base = normalize_text(raw)
    else:
        base = compact_text(raw, max_chars=max_chars)

    pinned_parts = []
    for name in ("Projects", "Certifications"):
        extracted = _extract_section(raw, name)
        if extracted:
            pinned_parts.append(extracted)

    if not pinned_parts:
        return base

    pinned = "\n\n".join(pinned_parts)
    # If truncation removed these sections, append them explicitly.
    lower_base = base.lower()
    need_append = any(name.lower() not in lower_base for name in ("projects", "certifications"))
    if not need_append:
        return base

    return base + "\n\n---\nPINNED FROM MASTER PROFILE:\n" + pinned


def extract_keywords(text: str, max_keywords: int = 40) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+.#/-]{1,}", (text or "").lower())
    tokens = [t for t in tokens if t not in _STOPWORDS and len(t) >= 2]
    counts = Counter(tokens)
    # Prefer longer technical-ish tokens
    ranked = sorted(counts.items(), key=lambda x: (x[1], len(x[0])), reverse=True)
    out: List[str] = []
    for word, _ in ranked:
        if word not in out:
            out.append(word)
        if len(out) >= max_keywords:
            break
    return out


def build_jd_pack(job_description: str, max_chars: int = 3500) -> Dict[str, object]:
    jd_compact = compact_text(job_description, max_chars=max_chars)
    keywords = extract_keywords(jd_compact, max_keywords=40)
    return {
        "jd_compact": jd_compact,
        "keywords": keywords,
    }


def basic_resume_heuristics(resume_markdown: str, jd_keywords: List[str]) -> Dict[str, object]:
    text = (resume_markdown or "").lower()
    hits = [kw for kw in jd_keywords if kw.lower() in text]
    hit_rate = (len(hits) / max(1, len(jd_keywords)))

    required_headings = [
        "summary",
        "education",
        "technical skills",
        "professional experience",
        "projects",
        "certifications",
    ]
    headings_present = {h: (h in text) for h in required_headings}
    completeness = sum(1 for v in headings_present.values() if v) / len(required_headings)

    length_chars = len(resume_markdown or "")

    return {
        "keyword_hits": hits,
        "keyword_hit_rate": round(hit_rate, 3),
        "headings_present": headings_present,
        "section_completeness": round(completeness, 3),
        "length_chars": length_chars,
    }
