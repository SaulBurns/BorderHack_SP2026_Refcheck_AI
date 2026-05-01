import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def _clean(value: str | None, fallback: str = "") -> str:
    if value is None:
        return fallback
    return value.strip() or fallback


def _config() -> dict[str, str] | None:
    url = _clean(os.getenv("SUPABASE_URL")).rstrip("/")
    key = _clean(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    bucket = _clean(os.getenv("SUPABASE_CLIPS_BUCKET"), "clips")
    table = _clean(os.getenv("SUPABASE_VERDICTS_TABLE"), "verdicts")

    if not url or not key:
        return None

    return {
        "url": url,
        "key": key,
        "bucket": bucket,
        "table": table,
    }


def _request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str],
    payload: Any | None = None,
) -> Any:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else None


def _upload_clip(config: dict[str, str], video_metadata: dict, clip_id: str) -> str | None:
    stored_path = video_metadata.get("stored_path")
    if not stored_path:
        return None

    path = Path(stored_path)
    if not path.exists():
        return None

    safe_filename = Path(video_metadata.get("filename") or path.name).name.replace(" ", "_")
    object_path = f"{clip_id}/{safe_filename}"
    encoded_path = urllib.parse.quote(object_path)
    upload_url = f"{config['url']}/storage/v1/object/{config['bucket']}/{encoded_path}"
    content_type = video_metadata.get("content_type") or "application/octet-stream"

    request = urllib.request.Request(
        upload_url,
        data=path.read_bytes(),
        headers={
            "Authorization": f"Bearer {config['key']}",
            "apikey": config["key"],
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=120):
        pass

    return f"{config['url']}/storage/v1/object/public/{config['bucket']}/{encoded_path}"


def _row_from_result(
    *,
    result: dict,
    video_url: str | None,
    sport: str,
    level_of_play: str,
    league: str,
    original_call: str,
    referee_name: str,
) -> dict:
    verdict = result.get("verdict") or {}
    perception = verdict.get("perception") or {}
    cited_rule = verdict.get("cited_rule") or {}

    return {
        "clip_id": result.get("clip_id"),
        "video_url": video_url or result.get("clip_url"),
        "sport": sport or "basketball",
        "level_of_play": level_of_play or None,
        "league": league or None,
        "original_call": original_call or None,
        "referee_name": referee_name or None,
        "verdict": verdict.get("verdict"),
        "confidence": verdict.get("confidence"),
        "call_type": perception.get("event_type"),
        "rule_id": cited_rule.get("rule_id"),
        "reasoning": verdict.get("reasoning"),
        "verdict_json": result,
    }


def persist_analysis(
    *,
    result: dict,
    video_metadata: dict,
    sport: str,
    level_of_play: str,
    league: str,
    original_call: str,
    referee_name: str,
) -> dict:
    config = _config()
    if not config:
        return result

    try:
        clip_id = result.get("clip_id")
        video_url = _upload_clip(config, video_metadata, clip_id) if clip_id else None
        if video_url:
            result["clip_url"] = video_url

        row = _row_from_result(
            result=result,
            video_url=video_url,
            sport=sport,
            level_of_play=level_of_play,
            league=league,
            original_call=original_call,
            referee_name=referee_name,
        )

        _request_json(
            f"{config['url']}/rest/v1/{config['table']}?on_conflict=clip_id",
            method="POST",
            headers={
                "Authorization": f"Bearer {config['key']}",
                "apikey": config["key"],
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            payload=row,
        )
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError) as exc:
        result["persistence_warning"] = str(exc)

    return result


def list_feed(limit: int = 20) -> list[dict]:
    config = _config()
    if not config:
        return []

    query = urllib.parse.urlencode(
        {
            "select": "clip_id,video_url,sport,level_of_play,league,original_call,referee_name,verdict,confidence,call_type,rule_id,reasoning,created_at,votes_fair,votes_bad,votes_inconclusive,verdict_json",
            "order": "created_at.desc",
            "limit": str(limit),
        }
    )
    try:
        rows = _request_json(
            f"{config['url']}/rest/v1/{config['table']}?{query}",
            headers={
                "Authorization": f"Bearer {config['key']}",
                "apikey": config["key"],
            },
        )
        return rows if isinstance(rows, list) else []
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError):
        return []
