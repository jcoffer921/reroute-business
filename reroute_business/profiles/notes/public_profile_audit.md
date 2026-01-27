# Public Profile Audit (pre-overwrite)

Date: 2026-01-27

## Routes
- Canonical user public profile: `profiles:public_profile` → `/profile/view/<username>/` (in `profiles/urls.py`).
- Employer public profile: `employer_public_profile` → `/profile/employer/view/<username>/` (in `profiles/urls.py` + alias in `reroute/urls.py`).
- Owner profile alias: `profiles:my_profile` → `/profile/` (redirects to settings).

## View
- `public_profile_view` in `profiles/views.py` (currently gated to employers only; login required).

## Templates
- User public profile template: `profiles/templates/profiles/public_profile.html`.
- Employer public profile template: `profiles/templates/profiles/employer_public_profile.html`.

## Assets
- CSS: `profiles/static/css/public_profile.css` and `profiles/static/css/employer_public_profile.css` (both linked in `public_profile.html`).
- JS: `profiles/static/js/employer_public_profile.js` is included by `public_profile.html`.

## Navigation / entry points
- Employer-facing lists link to `profiles:public_profile` from:
  - `dashboard/templates/dashboard/employer_job_matches.html`
  - `dashboard/templates/dashboard/employer_dashboard.html`
  - `dashboard/templates/dashboard/employer_matcher.html`

## Current access behavior
- `public_profile_view` blocks non-employer users and redirects them home with an error message.
- Login is required (no anonymous access).
