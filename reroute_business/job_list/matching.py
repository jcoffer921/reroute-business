from job_list.models import Job


def _normalize_skills(qs):
    return {s.name.strip().lower() for s in qs}


def match_jobs_for_user(user, origin_zip: str | None = None, radius: int = 25):
    """
    Return a list of Job objects ordered by a composite score:
      - skill coverage ratio (up to 70 pts)
      - distance bonus within 25mi (+20) or 50mi (+10) if origin_zip provided
      - recency bonus if posted within 14 days (+10)
    """
    from resumes.models import Resume
    from django.utils import timezone
    from job_list.utils.geo import is_within_radius

    resume = (
        Resume.objects.filter(user=user)
        .order_by("-created_at")
        .first()
    )
    if not resume or not getattr(resume, "skills", None) or not resume.skills.exists():
        return []

    seeker_skills = _normalize_skills(resume.skills.all())
    if not seeker_skills:
        return []

    matches = []
    for job in (
        Job.objects.filter(is_active=True)
        .prefetch_related("skills_required")
        .select_related("employer")
    ):
        job_skills = _normalize_skills(job.skills_required.all())
        if not job_skills:
            continue

        overlap = seeker_skills & job_skills
        if not overlap:
            continue

        # Skill coverage relative to job requirements
        overlap_pct = len(overlap) / max(len(job_skills), 1)
        score = overlap_pct * 70

        # Distance bonus
        if origin_zip and job.zip_code:
            try:
                if is_within_radius(origin_zip, job.zip_code, 25):
                    score += 20
                elif is_within_radius(origin_zip, job.zip_code, 50):
                    score += 10
            except Exception:
                pass

        # Recency bonus
        try:
            if (timezone.now() - job.created_at).days <= 14:
                score += 10
        except Exception:
            pass

        matches.append((score, job))

    matches.sort(key=lambda t: (-t[0], t[1].id))
    return [m[1] for m in matches]


def match_seekers_for_employer(employer_user, limit_per_job: int = 3):
    """
    For an employer, return a list of candidate matches across their jobs.
    Each item is a dict:
      { 'job': Job, 'profile': UserProfile, 'user': User, 'score': float }
    Sorted by score desc, limited per job to avoid flooding the dashboard.
    """
    from profiles.models import UserProfile
    from resumes.models import Resume

    jobs = Job.objects.filter(employer=employer_user, is_active=True).prefetch_related("skills_required")
    if not jobs.exists():
        return []

    # Preload all user profiles and resumes once
    profiles = (
        UserProfile.objects.select_related("user")
    )
    # Map user -> latest resume (portable across DBs)
    resume_by_user: dict[int, Resume] = {}
    for r in Resume.objects.order_by("-created_at").only("id", "user_id"):
        if r.user_id not in resume_by_user:
            resume_by_user[r.user_id] = r

    results: list[dict] = []
    for job in jobs:
        job_skills = _normalize_skills(job.skills_required.all())
        if not job_skills:
            continue

        scored_candidates: list[tuple[float, UserProfile]] = []
        for profile in profiles:
            resume = resume_by_user.get(profile.user_id)
            if not resume or not resume.skills.exists():
                continue

            seeker_skills = _normalize_skills(resume.skills.all())
            if not seeker_skills:
                continue

            overlap = seeker_skills & job_skills
            if not overlap:
                continue

            overlap_pct = len(overlap) / max(len(job_skills), 1)
            score = overlap_pct * 100  # full scale for employer view
            scored_candidates.append((score, profile))

        # Top candidates for this job
        scored_candidates.sort(key=lambda t: t[0], reverse=True)
        for score, profile in scored_candidates[:limit_per_job]:
            results.append({
                "job": job,
                "profile": profile,
                "user": profile.user,
                "score": round(score, 1),
            })

    # Overall order by score
    results.sort(key=lambda d: d["score"], reverse=True)
    return results
