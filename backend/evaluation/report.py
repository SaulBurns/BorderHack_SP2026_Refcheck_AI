"""Render a BenchmarkReport as Markdown or self-contained HTML (Sprint 5).

Both renderers cover: a provider comparison table (accuracy, macro-F1, kappa,
ECE, latency), and per-provider confusion matrix, per-class precision/recall/F1,
calibration reliability bins, and latency summary. Pure string builders — no I/O.
"""

from __future__ import annotations

from html import escape

from evaluation.benchmark import BenchmarkReport, BenchmarkResult
from evaluation.models import VERDICTS


def _f3(value: float | int | None) -> str:
    return "—" if value is None else f"{float(value):.3f}"


def _pct(value: float | int | None) -> str:
    return "—" if value is None else f"{round(float(value) * 100)}%"


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def _comparison_rows(report: BenchmarkReport) -> list[tuple[str, ...]]:
    recommended = report.recommended_provider()
    rows: list[tuple[str, ...]] = []
    for result in report.results:
        ev = result.evaluation
        provider = f"{result.provider} ★" if result.provider == recommended else result.provider
        rows.append(
            (
                provider,
                _pct(ev.accuracy),
                _f3(ev.macro.get("f1")),
                _f3(ev.cohens_kappa),
                _f3(ev.ece),
                _f3(ev.mcc),
                _f3(ev.brier),
                _f3(result.latency.mean_ms),
                _f3(result.latency.p95_ms),
            )
        )
    return rows


def render_markdown(report: BenchmarkReport) -> str:
    lines = [
        "# RefCheck AI — Evaluation Benchmark",
        "",
        f"- Dataset: `{report.dataset}`  ·  Detector: `{report.detector}`  ·  Clips: {report.clip_count}",
        f"- Generated: `{report.generated_at}`",
        "",
        "## Provider comparison",
        "",
        "| Provider | Accuracy | Macro F1 | Kappa | ECE | MCC | Brier | Mean latency (ms) | p95 (ms) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in _comparison_rows(report):
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    recommended = report.recommended_provider()
    if recommended:
        lines += [
            f"**Recommended provider: `{recommended}`** ★ — highest accuracy, then "
            "Matthews correlation, then best-calibrated (lowest Brier), then fastest.",
            "",
        ]

    for result in report.results:
        lines += _provider_section_md(result)
    return "\n".join(lines)


def _provider_section_md(result: BenchmarkResult) -> list[str]:
    ev = result.evaluation
    lines = [
        f"## Provider: {result.provider}",
        "",
        f"- Clips: {ev.count}  ·  Accuracy: {_pct(ev.accuracy)}  ·  "
        f"Macro P/R/F1: {_f3(ev.macro.get('precision'))} / {_f3(ev.macro.get('recall'))} / {_f3(ev.macro.get('f1'))}",
        f"- Cohen's kappa: {_f3(ev.cohens_kappa)}  ·  MCC: {_f3(ev.mcc)}  ·  "
        f"ECE: {_f3(ev.ece)}  ·  Brier: {_f3(ev.brier)}  ·  "
        f"Mean confidence: {_f3(ev.mean_confidence)}",
        f"- Latency ms — mean {_f3(result.latency.mean_ms)} · p50 {_f3(result.latency.p50_ms)} · "
        f"p95 {_f3(result.latency.p95_ms)} · max {_f3(result.latency.max_ms)}",
        "",
        "### Confusion matrix (rows = ground truth, cols = predicted)",
        "",
        "| GT \\ Pred | " + " | ".join(VERDICTS) + " |",
        "| --- | " + " | ".join("---" for _ in VERDICTS) + " |",
    ]
    for gt in VERDICTS:
        cells = " | ".join(str(ev.confusion_matrix.get(gt, {}).get(pred, 0)) for pred in VERDICTS)
        lines.append(f"| {gt} | {cells} |")
    lines += [
        "",
        "### Per-class metrics",
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "| --- | --- | --- | --- | --- |",
    ]
    for verdict in VERDICTS:
        pc = ev.per_class.get(verdict, {})
        lines.append(
            f"| {verdict} | {_f3(pc.get('precision'))} | {_f3(pc.get('recall'))} | "
            f"{_f3(pc.get('f1'))} | {int(pc.get('support', 0))} |"
        )
    lines += [
        "",
        "### Confidence calibration (reliability)",
        "",
        "| Confidence bin | Count | Avg confidence | Accuracy |",
        "| --- | --- | --- | --- |",
    ]
    for b in ev.reliability:
        if not b["count"]:
            continue
        lines.append(
            f"| {b['bin_lower']:.1f}–{b['bin_upper']:.1f} | {int(b['count'])} | "
            f"{_f3(b['avg_confidence'])} | {_f3(b['accuracy'])} |"
        )
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# HTML (self-contained)
# ---------------------------------------------------------------------------

_HTML_STYLE = """
body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; color: #111; }
h1 { margin-bottom: .25rem; } h2 { margin-top: 2rem; } h3 { margin-top: 1.25rem; }
table { border-collapse: collapse; margin: .5rem 0 1rem; }
th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: center; font-variant-numeric: tabular-nums; }
th { background: #f5f5f5; }
td.label, th.label { text-align: left; font-weight: 600; background: #fafafa; }
.meta { color: #666; font-size: .9rem; }
.cm-hit { background: #e5ffe5; } .cm-miss { background: #ffecec; }
""".strip()


def _cell(value: str) -> str:
    return f"<td>{escape(value)}</td>"


def _table(headers: list[str], rows: list[list[str]], first_col_label: bool = False) -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = []
    for row in rows:
        cells = []
        for i, value in enumerate(row):
            klass = ' class="label"' if (first_col_label and i == 0) else ""
            cells.append(f"<td{klass}>{escape(value)}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _confusion_html(result: BenchmarkResult) -> str:
    ev = result.evaluation
    head = "<th class='label'>GT \\ Pred</th>" + "".join(f"<th>{escape(v)}</th>" for v in VERDICTS)
    rows = []
    for gt in VERDICTS:
        cells = [f"<td class='label'>{escape(gt)}</td>"]
        for pred in VERDICTS:
            n = ev.confusion_matrix.get(gt, {}).get(pred, 0)
            klass = "cm-hit" if gt == pred and n else ("cm-miss" if n else "")
            cells.append(f"<td class='{klass}'>{n}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def render_html(report: BenchmarkReport) -> str:
    comparison = _table(
        ["Provider", "Accuracy", "Macro F1", "Kappa", "ECE", "MCC", "Brier",
         "Mean latency (ms)", "p95 (ms)"],
        [list(row) for row in _comparison_rows(report)],
        first_col_label=True,
    )
    recommended = report.recommended_provider()
    recommended_html = (
        f"<p class='meta'><strong>Recommended provider: <code>{escape(recommended)}</code></strong> ★ "
        "— highest accuracy, then Matthews correlation, then best-calibrated (lowest Brier), then fastest.</p>"
        if recommended
        else ""
    )

    sections: list[str] = []
    for result in report.results:
        ev = result.evaluation
        per_class = _table(
            ["Class", "Precision", "Recall", "F1", "Support"],
            [
                [
                    v,
                    _f3(ev.per_class.get(v, {}).get("precision")),
                    _f3(ev.per_class.get(v, {}).get("recall")),
                    _f3(ev.per_class.get(v, {}).get("f1")),
                    str(int(ev.per_class.get(v, {}).get("support", 0))),
                ]
                for v in VERDICTS
            ],
            first_col_label=True,
        )
        reliability = _table(
            ["Confidence bin", "Count", "Avg confidence", "Accuracy"],
            [
                [f"{b['bin_lower']:.1f}–{b['bin_upper']:.1f}", str(int(b["count"])),
                 _f3(b["avg_confidence"]), _f3(b["accuracy"])]
                for b in ev.reliability
                if b["count"]
            ],
        )
        sections.append(
            f"<h2>Provider: {escape(result.provider)}</h2>"
            f"<p class='meta'>Accuracy {_pct(ev.accuracy)} · Macro F1 {_f3(ev.macro.get('f1'))} · "
            f"Kappa {_f3(ev.cohens_kappa)} · ECE {_f3(ev.ece)} · "
            f"Latency mean {_f3(result.latency.mean_ms)}ms / p95 {_f3(result.latency.p95_ms)}ms</p>"
            f"<h3>Confusion matrix</h3>{_confusion_html(result)}"
            f"<h3>Per-class metrics</h3>{per_class}"
            f"<h3>Confidence calibration</h3>{reliability}"
        )

    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>RefCheck AI — Evaluation Benchmark</title>"
        f"<style>{_HTML_STYLE}</style></head><body>"
        "<h1>RefCheck AI — Evaluation Benchmark</h1>"
        f"<p class='meta'>Dataset <code>{escape(report.dataset)}</code> · "
        f"Detector <code>{escape(report.detector)}</code> · Clips {report.clip_count} · "
        f"Generated {escape(report.generated_at)}</p>"
        "<h2>Provider comparison</h2>"
        f"{comparison}"
        f"{recommended_html}"
        f"{''.join(sections)}"
        "</body></html>"
    )
