"""Analysis pipeline internals (Sprint 7).

Cohesive modules extracted from the former monolithic ``ai_analyzer`` so each
concern (prompts, frame extraction, rule corpus, mock result, diagnostics,
caching) lives in its own file. ``services.ai_analyzer`` re-imports these and
remains the single orchestration entrypoint, so all existing import paths and
test seams keep working.
"""
