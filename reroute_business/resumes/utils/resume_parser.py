# resumes/utils/resume_parser.py
"""
Robust resume parsing helpers. Production-safe:
- PDF text extraction prefers pure-Python (pypdf) and uses PyMuPDF (fitz) only if installed.
- DOCX parsing via python-docx (if installed). Legacy .doc is NOT supported.
- Strict JSON shaping for LLM output so downstream code doesn't crash.
- Ollama call is optional, env-controlled, and never takes the site down.

Exposed functions (kept stable for views):
  validate_file_extension(file) -> str
  validate_file_size(file) -> bool
  read_upload_file(file, ext) -> str
  extract_resume_information(text) -> dict
  analyze_with_ollama(prompt, model="mistral:latest") -> str
"""

from __future__ import annotations

import io
import json
import logging
import os
from typing import Any, Dict, List

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

# --- Optional dependencies (do NOT crash at import time) ---------------------
try:
    import fitz  # PyMuPDF (fast/accurate if present)
except Exception:
    fitz = None  # type: ignore

try:
    import docx  # python-docx for DOCX files
    HAS_DOCX = True
except Exception:
    docx = None  # type: ignore
    HAS_DOCX = False

# requests is used only if analyze_with_ollama is enabled
try:
    import requests  # type: ignore
except Exception:
    requests = None  # type: ignore

log = logging.getLogger(__name__)

# === Allowed inputs ===
# NOTE: python-docx cannot parse legacy .doc files. Keep it to PDF/DOCX.
VALID_EXTENSIONS = [".pdf", ".docx"]
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


# ---------- Validation --------------------------------------------------------

def validate_file_extension(file_object: UploadedFile) -> str:
    """
    Ensure we accept only expected file types, and return normalized extension.
    """
    ext = os.path.splitext(file_object.name or "")[1].lower()
    if ext not in VALID_EXTENSIONS:
        raise ValidationError(f"Unsupported file extension: {ext}. Allowed: {', '.join(VALID_EXTENSIONS)}")
    if ext == ".docx" and not HAS_DOCX:
        raise ValidationError("DOCX parsing is not enabled on this server. Please upload a PDF.")
    return ext


def validate_file_size(file_object: UploadedFile) -> bool:
    """Reject very large resumes to protect server memory."""
    if getattr(file_object, "size", 0) > MAX_UPLOAD_SIZE:
        raise ValidationError("File size exceeds the 10MB limit.")
    return True


# ---------- File reading ------------------------------------------------------

def _read_pdf_with_fitz(data: bytes) -> str:
    """Extract text from PDF using PyMuPDF (if installed)."""
    if not fitz:
        raise RuntimeError("PyMuPDF not available")
    text_parts: List[str] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text() or "")
    return "\n".join(text_parts)


def _read_pdf_with_pypdf(data: bytes) -> str:
    """Extract text from PDF using pypdf (pure Python, always safe on Render)."""
    try:
        from pypdf import PdfReader  # import inside to avoid hard dep if unused
    except Exception as e:
        raise RuntimeError("pypdf not available") from e
    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _read_pdf(file_object: UploadedFile) -> str:
    """
    Extract text from PDF, choosing the best available backend.
    Order: PyMuPDF (if installed) -> pypdf (fallback).
    """
    # Read the file bytes once
    file_object.seek(0)
    data = file_object.read()
    # Try PyMuPDF first (better layout accuracy)
    if fitz:
        try:
            return _read_pdf_with_fitz(data)
        except Exception as e:
            log.warning("PyMuPDF failed, falling back to pypdf: %s", e)
    # Fallback to pypdf
    try:
        return _read_pdf_with_pypdf(data)
    except Exception as e:
        log.error("All PDF parsers failed: %s", e)
        raise ValidationError("Unable to extract text from PDF on this server.")


def _read_docx(file_object: UploadedFile) -> str:
    """Extract text from DOCX using python-docx (if enabled)."""
    if not HAS_DOCX or not docx:
        raise ValidationError("DOCX parsing is not enabled on this server.")
    file_object.seek(0)
    d = docx.Document(file_object)  # python-docx accepts a file-like object
    return "\n".join([p.text for p in d.paragraphs])


def read_upload_file(file_object: UploadedFile, file_extension: str) -> str:
    """
    Unify file reading. PDFs via PyMuPDF/pypdf; DOCX via python-docx.
    """
    if file_extension == ".pdf":
        return _read_pdf(file_object)
    if file_extension == ".docx":
        return _read_docx(file_object)
    raise ValidationError(f"Cannot parse files with extension: {file_extension}")


# ---------- LLM helpers (Ollama) ---------------------------------------------

def _safe_json_loads(s: str) -> Dict[str, Any]:
    """
    Parse model output strictly as JSON. If it isn't valid JSON, raise.
    We also try to strip non-JSON noise (common LLM failure mode).
    """
    s = (s or "").strip()
    try:
        first = s.index("{")
        last = s.rindex("}")
        s = s[first:last + 1]
    except ValueError:
        raise ValueError("Model returned non-JSON content.")
    return json.loads(s)


def _coerce_to_schema(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforce a stable schema so the rest of your pipeline never breaks.
    Missing fields become empty; incorrect types are normalized.
    """
    def as_str(x) -> str:
        return (x or "").strip() if isinstance(x, str) else ""

    def as_list(x) -> List[Any]:
        return x if isinstance(x, list) else []

    out: Dict[str, Any] = {
        "contact_info": {
            "full_name": "",
            "email": "",
            "phone": "",
            "city": "",
            "state": "",
        },
        "skills": [],
        "experience": [],
        "education": [],
    }

    ci = (parsed.get("contact_info") or {}) if isinstance(parsed, dict) else {}
    out["contact_info"]["full_name"] = as_str(ci.get("full_name"))
    out["contact_info"]["email"] = as_str(ci.get("email"))
    out["contact_info"]["phone"] = as_str(ci.get("phone"))
    out["contact_info"]["city"] = as_str(ci.get("city"))
    st = as_str(ci.get("state"))
    out["contact_info"]["state"] = st[:2].upper() if st else ""

    out["skills"] = [as_str(s) for s in as_list(parsed.get("skills")) if as_str(s)]

    exp_out: List[Dict[str, str]] = []
    for e in as_list(parsed.get("experience")):
        if isinstance(e, dict):
            exp_out.append({
                "job_title": as_str(e.get("job_title")),
                "company": as_str(e.get("company")),
                "dates": as_str(e.get("dates")),
            })
    out["experience"] = exp_out

    edu_out: List[Dict[str, str]] = []
    for ed in as_list(parsed.get("education")):
        if isinstance(ed, dict):
            edu_out.append({
                "school_name": as_str(ed.get("school_name") or ed.get("institution")),
                "degree": as_str(ed.get("degree")),
                "graduation_year": as_str(ed.get("graduation_year") or ed.get("year"))[:4],
            })
    out["education"] = edu_out

    return out


def _basic_parse_resume(text: str) -> Dict[str, Any]:
    """
    Heuristic, dependency-free parser used when AI is disabled/unavailable.
    Tries to pull reasonable fields from plain text resumes.
    """
    import re

    # --- Section helpers ---------------------------------------------------
    SECTION_SYNONYMS = {
        "summary": ["summary", "professional summary", "objective", "profile", "about me"],
        "experience": ["experience", "work experience", "employment", "work history", "professional experience"],
        "education": ["education", "education & training", "academic background", "academics"],
        "skills": ["skills", "technical skills", "key skills", "core competencies", "competencies"],
        "projects": ["projects", "selected projects"],
        "certifications": ["certifications", "licenses", "certificates"],
    }

    # Precompute regex for all headings
    heading_patterns = {
        key: [re.compile(rf"^\s*{re.escape(lbl)}\s*:??\s*$", re.I | re.M) for lbl in labels]
        for key, labels in SECTION_SYNONYMS.items()
    }

    def first_index_for_any(patterns) -> int:
        pos = -1
        for pat in patterns:
            m = pat.search(text)
            if m:
                pos = m.start() if pos == -1 else min(pos, m.start())
        return pos

    def slice_any(section_key: str) -> str:
        start_patterns = heading_patterns.get(section_key, [])
        start = first_index_for_any(start_patterns)
        if start == -1:
            return ""
        # Find the nearest subsequent heading of any known section
        all_positions = []
        for k, pats in heading_patterns.items():
            for pat in pats:
                m = pat.search(text)
                if m and m.start() > start:
                    all_positions.append(m.start())
        end = min(all_positions) if all_positions else len(text)
        return text[start:end]

    # Contact info
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone_match = re.search(r"(\+?\d{1,2}[\s.-])?(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})", text)
    # Heuristic name: first non-empty line at top (avoid headings)
    first_lines = [ln.strip() for ln in text.splitlines()[:10] if ln.strip()]
    full_name = ""
    for ln in first_lines:
        if len(ln.split()) in (2, 3) and not any(w.lower() in ln.lower() for w in ("resume", "objective", "summary", "skills")):
            full_name = ln
            break

    # City, State (e.g., Philadelphia, PA)
    loc_match = re.search(r"([A-Za-z .'-]{2,}),\s*([A-Z]{2})\b", text)
    city = loc_match.group(1) if loc_match else ""
    state = loc_match.group(2) if loc_match else ""

    # Skills section: split by comma/newlines after heading
    skills_block = slice_any("skills")
    skills: List[str] = []
    if skills_block:
        body = re.sub(r"(?is)^\s*[A-Za-z ]+skills\s*:?\s*", "", skills_block).strip()
        # Split on newlines, commas, bullets, pipes, middots, slashes
        raw = re.split(r"[\n,\u2022\u00b7\|/]+", body)
        skills = [s.strip(" •-*–\t").strip() for s in raw if len(s.strip()) >= 2]
        # De-dup while preserving order
        seen = set(); dedup = []
        for s in skills:
            key = s.lower()
            if key in seen:
                continue
            seen.add(key); dedup.append(s)
        skills = dedup[:40]

    # Experience: gather bullet-ish lines under experience section
    exp_block = slice_any("experience")
    experiences: List[Dict[str, str]] = []
    if exp_block:
        lines = [ln.strip() for ln in exp_block.splitlines() if ln.strip()]
        # crude grouping by blank lines or date patterns
        current: List[str] = []
        def flush():
            if current:
                # Merge lines, collapse spaces
                joined = re.sub(r"\s+", " ", " ".join(current)).strip()
                # Try to split "Title at Company" or "Company – Title"
                title = ""; company = ""; dates = ""
                # Dates common patterns
                dm = re.search(r"(\bJan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec\b\.?\s+\d{4}|\b(19|20)\d{2}\b).*?(Present|\b(19|20)\d{2}\b)", joined, re.I)
                if dm:
                    dates = dm.group(0)
                am = re.search(r"(.+?)\s+at\s+(.+)", joined, re.IGNORECASE)
                if am:
                    title, company = am.group(1).strip(), am.group(2).strip()
                else:
                    bm = re.search(r"(.+?)\s+[–\-]\s+(.+)", joined)
                    if bm:
                        left, right = bm.group(1).strip(), bm.group(2).strip()
                        # Guess which is company vs title by capitalization
                        if left.isupper() or left.istitle() and right.islower():
                            company, title = left, right
                        else:
                            title, company = left, right
                # Clean dates for duplicates / spacing
                if dates:
                    # Normalize Present and dashes, deduplicate repeated tokens
                    dates = re.sub(r'\bpresent\b', 'Present', dates, flags=re.I)
                    dates = re.sub(r'\s*[\-\u2013\u2014]+\s*', ' - ', dates)
                    dates = re.sub(r'\b((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{4})\b(\s+\1\b)+', r'\1', dates, flags=re.I)
                    dates = re.sub(r'\b((19|20)\d{2})\b(\s+\1\b)+', r'\1', dates)
                experiences.append({
                    "job_title": title[:255],
                    "company": company[:255],
                    "dates": dates[:100],
                })
                current.clear()
        for ln in lines:
            # Start a new block on strong separators (blank lines already removed), or accumulate bullets/title/company lines
            if re.match(r"^(?:\s*\-|\s*\*|\s*•|\s*–)\s*", ln) or len(current) < 3 or re.search(r"\b(at|\u2013|\u2014|\-|\d{4})\b", ln, re.I):
                current.append(ln)
            else:
                # separator
                flush()
                current.append(ln)
        flush()
        # Trim empties
        experiences = [e for e in experiences if any(e.values())][:10]

    # Education: try to extract common patterns "School – Degree, 2022"
    edu_block = slice_any("education")
    education: List[Dict[str, str]] = []
    if edu_block:
        for ln in [l.strip() for l in edu_block.splitlines() if l.strip()]:
            # Year
            ym = re.search(r"\b(19|20)\d{2}\b", ln)
            year = ym.group(0) if ym else ""
            parts = re.split(r"\s+[–\-]\s+|,", ln, maxsplit=2)
            school = parts[0].strip() if parts else ""
            degree = parts[1].strip() if len(parts) > 1 else ""
            if school:
                education.append({
                    "school_name": school[:255],
                    "degree": degree[:255],
                    "graduation_year": year[:4],
                })
        # de-dup consecutive duplicates and cap
        dedup = []
        for ed in education:
            if not dedup or ed != dedup[-1]:
                dedup.append(ed)
        education = dedup[:10]

    return _coerce_to_schema({
        "contact_info": {
            "full_name": (full_name or "")[:255],
            "email": (email_match.group(0) if email_match else "")[:254],
            "phone": (phone_match.group(0) if phone_match else "")[:20],
            "city": city[:100],
            "state": state[:2],
        },
        "skills": skills,
        "experience": experiences,
        "education": education,
    })


def extract_resume_information(file_content: str) -> Dict[str, Any]:
    """
    Backwards-compatible function name. Uses a strict prompt and returns a dict
    conforming to our schema (even if model output is imperfect).
    """
    prompt = f"""
Extract the following fields from the resume text.
Return ONLY valid JSON in this EXACT structure. No prose.

{{
  "contact_info": {{
    "full_name": "",
    "email": "",
    "phone": "",
    "city": "",
    "state": ""
  }},
  "skills": [],
  "experience": [{{ "job_title": "", "company": "", "dates": "" }}],
  "education": [{{ "school_name": "", "degree": "", "graduation_year": "" }}]
}}

Resume text:
{file_content}
    """.strip()

    raw = analyze_with_ollama(prompt, model="mistral:latest")
    try:
        parsed = _safe_json_loads(raw)
        coerced = _coerce_to_schema(parsed)
    except Exception:
        coerced = _basic_parse_resume(file_content or "")
    # If still empty (very short text), just return schema
    if not any([
        coerced.get("contact_info", {}).get("email"),
        coerced.get("skills"),
        coerced.get("experience"),
        coerced.get("education"),
    ]):
        return _coerce_to_schema({})
    return coerced


def analyze_with_ollama(prompt: str, model: str = "mistral:latest") -> str:
    """
    Call an Ollama server if enabled. Never crash the site if it's not available.
    Control via env:
      ENABLE_RESUME_PARSER_AI=1 to enable
      OLLAMA_URL=http://localhost:11434 (or remote endpoint)
    """
    if os.getenv("ENABLE_RESUME_PARSER_AI", "0") not in ("1", "true", "True"):
        return ""  # AI disabled in this environment

    base_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    if not requests:
        log.warning("requests not installed; skipping Ollama call.")
        return ""

    try:
        resp = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return (data.get("response") or "").strip()
    except Exception as e:
        log.warning("Ollama call failed (%s); returning empty string.", e)
        return ""
