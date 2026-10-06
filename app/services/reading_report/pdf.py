"""Render a self-contained, script-free report using Chromium's print engine."""
import asyncio
import base64
import json
import html
import math
import os
from pathlib import Path
import re
import shutil
import signal
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from fastapi import HTTPException
from app.core.config import settings
from app.utils.weather_mappers import get_weather_condition


def escape(value):
    return html.escape(str(value))


def number(value, unit=""):
    if value is None:
        return "N/A"
    displayed = str(int(value)) if value == int(value) else str(value)
    return displayed + unit


def one_decimal(value):
    # Match JavaScript Number.toFixed(1), including exact midpoint rounding.
    return str(Decimal.from_float(float(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def timestamp(value, offset):
    if not value:
        return "N/A"
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone(timedelta(hours=offset))).strftime("%Y-%m-%d %H:%M:%S")


def obstruction_label(status):
    labels = {"clear": "Clear", "partial": "Possible", "blocked": "Potential"}
    return labels.get((status or "").lower(), status or "N/A")


def analysis_html(text):
    # Match the admin's supported bold/bullet syntax; never interpret raw HTML,
    # images, links, scripts, or remote resources supplied by AI/provider data.
    lines, sections = [], []
    for line in text.splitlines():
        if not line.strip():
            lines.append('<div class="ai-spacer"></div>')
            continue
        parts = re.split(r"\*\*(.*?)\*\*", line)
        content = "".join(f"<strong>{escape(part)}</strong>" if i % 2 else escape(part)
                          for i, part in enumerate(parts))
        if line.strip().startswith("- "):
            content = "• " + content.lstrip()[2:]
        heading = bool(re.fullmatch(r"\*\*.+\*\*", line.strip()))
        if heading and lines:
            sections.append('<article class="ai-section">' + ''.join(lines) + '</article>')
            lines = []
        lines.append(f'<p class="{"ai-heading" if heading else "ai-line"}">{content}</p>')
    if lines:
        sections.append('<article class="ai-section">' + ''.join(lines) + '</article>')
    return "".join(sections)


def trend_svg(rows, metric, title, unit, bars=False):
    width, height, left, bottom, top = 700, 230, 52, 195, 18
    right = 686
    values = [r[f"{prefix}_{metric}"] for r in rows for prefix in ("min", "max") if r[f"{prefix}_{metric}"] is not None]
    ceiling = max([110 if metric == "risk_score" else 10] + values) * (1 if metric == "risk_score" else 1.1)
    floor = min([0] + values)
    span = ceiling - floor
    def x(i):
        return left + (i + .5) * (right-left)/len(rows)
    def y(v):
        return bottom - (v-floor)/span*(bottom-top)
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">']
    for i in range(5):
        value = floor + span*i/4
        yy = y(value)
        elements.append(f'<path d="M{left} {yy}H{right}" stroke="#e2e8f0"/><text x="{left-8}" y="{yy+4}" text-anchor="end" font-size="11" fill="#475569">{value:.0f}</text>')
    for i, row in enumerate(rows):
        if i % max(1, math.ceil(len(rows)/8)) == 0 or i == len(rows)-1:
            elements.append(f'<text x="{x(i)}" y="214" text-anchor="middle" font-size="10" fill="#475569">{escape(row["summary_date"][5:])}</text>')
    for prefix, color in (("min", "#38bdf8"), ("max", "#e34d59")):
        previous = None
        for i, row in enumerate(rows):
            value = row[f"{prefix}_{metric}"]
            if value is None:
                previous = None
                continue
            xx, yy = x(i), y(value)
            if bars:
                bw = min(12, (right-left)/len(rows)*.35)
                bx = xx + (-bw if prefix == "min" else 0)
                elements.append(f'<rect x="{bx}" y="{yy}" width="{bw}" height="{max(0, y(0)-yy)}" fill="{color}"/>')
            else:
                if previous:
                    elements.append(f'<path d="M{previous[0]} {previous[1]}L{xx} {yy}" stroke="{color}" stroke-width="2" fill="none"/>')
                elements.append(f'<circle cx="{xx}" cy="{yy}" r="2.5" fill="{color}"/>')
            previous = (xx, yy)
    elements.append('</svg>')
    if not values:
        elements.append('<p class="muted">No observed readings for this metric.</p>')
    return f'<div class="chart"><h3>{escape(title)} ({unit})</h3><p class="legend"><span class="minimum">● Daily minimum</span> <span class="maximum">● Daily maximum</span> · {rows[0]["summary_date"]} to {rows[-1]["summary_date"]}</p>{"".join(elements)}</div>'


def obstruction_svg(rows):
    labels = (("clear", "Clear", "#2ecc71"), ("partial", "Possible", "#f39c12"), ("blocked", "Potential surface obstruction", "#e74c3c"))
    counts = [sum((r["most_severe_blockage"] or "").lower() == key for r in rows) for key, _, _ in labels]
    total = sum(counts)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 160" role="img" aria-label="Surface obstruction distribution">', '<circle cx="100" cy="80" r="52" fill="none" stroke="#e2e8f0" stroke-width="24"/>']
    circumference, consumed = 2*math.pi*52, 0
    for count, (_, label, color), i in zip(counts, labels, range(3)):
        length = circumference*count/total if total else 0
        if count:
            svg.append(f'<circle cx="100" cy="80" r="52" fill="none" stroke="{color}" stroke-width="24" stroke-dasharray="{length} {circumference-length}" stroke-dashoffset="{-consumed}" transform="rotate(-90 100 80)"/>')
        consumed += length
        svg.append(f'<text x="220" y="{35+i*30}" font-size="14" fill="{color}">● {label}: {count} days</text>')
    svg.append(f'<text x="100" y="78" text-anchor="middle" font-size="24">{total}</text><text x="100" y="97" text-anchor="middle" font-size="10">observed days</text><text x="220" y="132" font-size="12" fill="#64748b">N/A: {len(rows)-total} days</text></svg>')
    return '<div class="chart"><h3>Surface obstruction distribution</h3>' + ''.join(svg) + '</div>'


CSS = """
@page {size:A4; margin:16mm 14mm 18mm;
 @bottom-left {content:'AGOS · Reading logs'; font:8pt 'DejaVu Sans',sans-serif;color:#64748b}
 @bottom-right {content:'Page ' counter(page) ' of ' counter(pages);font:8pt 'DejaVu Sans',sans-serif;color:#64748b}}
*{box-sizing:border-box}body{margin:0;color:#1e293b;font:10pt 'DejaVu Sans',sans-serif;line-height:1.45}
h1{font-size:26pt;line-height:1.15;margin:8px 0;color:#0c4a6e}h2{font-size:16pt;color:#0c4a6e;margin:20px 0 12px;break-after:avoid}h3{font-size:11pt;margin:8px 0;break-after:avoid}p{margin:6px 0;overflow-wrap:anywhere}
.brand{font-size:9pt;letter-spacing:2px;color:#0284c7;font-weight:bold}.muted,.legend{font-size:8pt;color:#64748b}.meta{padding:12px;background:#f1f5f9;border-left:3px solid #0284c7;margin:14px 0}.cards{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:18px 0}.card{border:1px solid #cbd5e1;border-radius:6px;padding:12px;break-inside:avoid}.card b{display:block;font-size:20pt;color:#0c4a6e}.card span{font-size:8pt;color:#64748b}
.chart{border:1px solid #e2e8f0;padding:8px;margin:12px 0;break-inside:avoid}svg{width:100%;display:block;font-family:'DejaVu Sans',sans-serif}.minimum{color:#0284c7}.maximum{color:#dc3545}.section{break-before:page}.ai-line{margin:5px 0;orphans:3;widows:3}.ai-heading{margin:14px 0 6px;break-after:avoid}.ai-spacer{height:4px}.ai-section,.provenance{break-inside:avoid}.chart-intro{break-inside:avoid;break-after:avoid}
table{border-collapse:collapse;width:100%;font-size:8pt;table-layout:fixed}thead{display:table-header-group}th{background:#e2e8f0;text-align:left}td,th{padding:7px 5px;border-bottom:1px solid #e2e8f0;overflow-wrap:anywhere}tr{break-inside:avoid}tbody tr:nth-child(even){background:#f8fafc}.details{font-size:7.5pt}.audit{font-size:8pt;padding-top:12px}.hash{font-family:monospace;word-break:break-all;font-size:7pt}
"""


def build_html(report, generated_at):
    s = report.snapshot
    rows, stats, offset = s["summaries"], s["stats"], s["utc_offset_hours"]
    highest, water = stats["highestRisk"], stats["peakWaterLevel"]
    cards = [
        ("Highest risk score", number(highest["value"]) if highest else "N/A", highest["date"] if highest else "No risk readings"),
        ("Peak water level", number(water["value"], " cm") if water else "N/A", water["date"] if water else "No water readings"),
        ("Average daily peak precipitation", "N/A" if stats["avgDailyPeakPrecipitation"] is None else f'{one_decimal(stats["avgDailyPeakPrecipitation"])} mm', f'Across {stats["precipDays"]} observed days'),
        ("Days with potential obstruction", str(stats["blockedDays"]) if stats["blockageDays"] else "N/A", f'of {stats["blockageDays"]} observed days'),
    ]
    card_html = ''.join(f'<div class="card">{escape(label)}<b>{escape(value)}</b><span>{escape(detail)}</span></div>' for label, value, detail in cards)
    # Include absent dates as null chart points so lines cannot bridge gaps.
    by_day = {r["summary_date"]: r for r in rows}
    chart_rows = []
    for i in range((report.end_date-report.start_date).days+1):
        day = (report.start_date+timedelta(days=i)).isoformat()
        chart_rows.append(by_day.get(day, {"summary_date": day, **{f"{p}_{m}": None for p in ("min", "max") for m in ("risk_score", "water_level_cm", "precipitation_mm")}}))
    charts = []
    for i in range(0, len(chart_rows), 30):
        part = chart_rows[i:i+30]
        charts.extend((trend_svg(part, "risk_score", "Risk score trend", "score"), trend_svg(part, "water_level_cm", "Water level trend", "cm"), trend_svg(part, "precipitation_mm", "Precipitation trend", "mm", True)))
    charts.append(obstruction_svg(rows))
    table_rows, details = [], []
    for row in rows:
        table_rows.append('<tr>' + ''.join(f'<td>{escape(value)}</td>' for value in (
            row["summary_date"], f'{number(row["min_risk_score"])} – {number(row["max_risk_score"])}',
            f'{number(row["min_water_level_cm"])} – {number(row["max_water_level_cm"])}',
            f'{number(row["min_precipitation_mm"])} – {number(row["max_precipitation_mm"])}',
            f'{obstruction_label(row["least_severe_blockage"])} → {obstruction_label(row["most_severe_blockage"])}',
            "N/A" if row["most_severe_weather_code"] is None else f'{get_weather_condition(row["most_severe_weather_code"])} ({row["most_severe_weather_code"]})',
        )) + '</tr>')
        for label, minimum, maximum in (("Risk score", "min_risk_timestamp", "max_risk_timestamp"), ("Water level", "min_water_timestamp", "max_water_timestamp"), ("Precipitation", "min_precip_timestamp", "max_precip_timestamp")):
            details.append('<tr>' + ''.join(f'<td>{escape(value)}</td>' for value in (row["summary_date"], label, timestamp(row[minimum], offset), timestamp(row[maximum], offset))) + '</tr>')
    missing = ", ".join(s["missing_dates"]) or "None"
    partial_note = ""
    if s.get("partial_dates"):
        partial_note = (
            '<p class="muted"><strong>Partial day: '
            + escape(", ".join(s["partial_dates"]))
            + '. This day was still in progress when the data was captured. '
            'Its saved summary may cover only part of the day; extrema and analysis are preliminary.</strong></p>'
        )
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src 'none'"><title>AGOS Reading Report</title><style>{CSS}</style></head><body>
<div class="brand">AGOS / WATERWAY MONITORING</div><h1>Reading logs report</h1><h3>{escape(s["location_name"])}</h3>
<div class="meta"><strong>Reporting period: {report.start_date} to {report.end_date} (inclusive)</strong><p>Data captured: {timestamp(report.created_at.isoformat(),offset)} · {escape(s["timezone"])}</p><p>PDF generated: {timestamp(generated_at.isoformat(),offset)} · {escape(s["timezone"])}</p><p>Coverage: {len(rows)} of {len(chart_rows)} days · {len(s["missing_dates"])} {"missing day" if len(s["missing_dates"]) == 1 else "missing days"}</p></div>
{partial_note}<div class="cards">{card_html}</div><p class="muted">{escape(s["metric_definitions"])}</p><p class="muted">Potential surface obstruction reflects visible evidence, not confirmed subsurface blockage.</p>
<h2>AI overview</h2><p class="muted">Completed: {timestamp(report.analysis_completed_at.isoformat() if report.analysis_completed_at else None,offset)} · {escape(s["timezone"])}. Model: {escape(report.analysis_model or "Not recorded")}.</p>{analysis_html(report.analysis_text)}
<div><div class="chart-intro"><h2>Trends and distribution</h2><p class="muted">Daily minimum and maximum from the saved summaries. Missing readings create gaps. Longer periods use consecutive 30-day panels.</p></div>{''.join(charts)}</div>
<div class="section"><h2>Daily readings</h2><p class="muted">All {len(rows)} observed days. Values show minimum – maximum; precipitation is in mm, not an accumulated total. Surface obstruction: Clear / Possible / Potential.</p><table><thead><tr><th>Date</th><th>Risk score</th><th>Water (cm)</th><th>Rain (mm)</th><th>Surface obstruction</th><th>Weather (code)</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
<div><h2>Observation times</h2><p class="muted">All timestamps use {escape(s["timezone"])} (UTC{offset:+g}). N/A means no observation.</p><table class="details"><thead><tr><th>Date</th><th>Metric</th><th>Minimum observed at</th><th>Maximum observed at</th></tr></thead><tbody>{''.join(details)}</tbody></table>
<div class="provenance"><h2>Data coverage and provenance</h2><p class="muted">Missing dates: {escape(missing)}</p><p class="audit">Report ID: {report.id}<br>Snapshot retained until: {timestamp(report.expires_at.isoformat(),offset)} · {escape(s["timezone"])}<br>Prompt version: {escape(report.prompt_version)} · Template version: {escape(report.template_version)}</p><p class="hash">Snapshot SHA-256: {escape(s["data_hash"])}</p></div></div></body></html>'''


class PDFRenderer:
    def __init__(self):
        self._lock = asyncio.Lock()

    async def _print(self, process, root, document):
        # Use an ephemeral, loopback-only DevTools connection to explicitly wait
        # for the document and fonts, and request CSS-sized/background printing.
        active_port = root / "profile" / "DevToolsActivePort"
        while not active_port.exists():
            if process.returncode is not None:
                raise RuntimeError("Chromium exited before renderer initialization")
            await asyncio.sleep(.1)
        port, browser_path = active_port.read_text().splitlines()[:2]
        if not 0 < int(port) < 65536 or not browser_path.startswith("/devtools/browser/"):
            raise RuntimeError("Invalid local renderer address")
        async with connect(f"ws://127.0.0.1:{port}{browser_path}", proxy=None,
                           max_size=30*1024*1024, open_timeout=10, close_timeout=2) as socket:
            sequence = 0
            async def rpc(method, params=None, session=None):
                nonlocal sequence
                sequence += 1
                await socket.send(json.dumps({"id": sequence, "method": method, "params": params or {},
                                              **({"sessionId": session} if session else {})}))
                while True:
                    message = json.loads(await socket.recv())
                    if message.get("id") == sequence:
                        if "error" in message:
                            raise RuntimeError(f"Renderer command failed: {method}")
                        return message.get("result", {})
            target = (await rpc("Target.createTarget", {"url": "about:blank"}))["targetId"]
            session = (await rpc("Target.attachToTarget", {"targetId": target, "flatten": True}))["sessionId"]
            await rpc("Page.enable", session=session)
            await rpc("Network.enable", session=session)
            await rpc("Network.setBlockedURLs", {"urls": ["http://*", "https://*", "ftp://*"]}, session)
            navigation = await rpc("Page.navigate", {"url": document.as_uri()}, session)
            if navigation.get("errorText"):
                raise RuntimeError("Could not load the local report document")
            expression = "document.readyState === 'complete' && location.href === " + json.dumps(document.as_uri())
            while True:
                ready = await rpc("Runtime.evaluate", {"expression": expression, "returnByValue": True}, session)
                if ready["result"].get("value") is True:
                    break
                await asyncio.sleep(.1)
            await rpc("Runtime.evaluate", {"expression": "document.fonts.ready", "awaitPromise": True}, session)
            result = await rpc("Page.printToPDF", {"printBackground": True, "preferCSSPageSize": True,
                                                   "displayHeaderFooter": False}, session)
            return base64.b64decode(result["data"], validate=True)

    async def render(self, report, generated_at):
        if self._lock.locked():
            raise HTTPException(503, "PDF generation is busy. Please retry shortly.", headers={"Retry-After": "10"})
        executable = settings.REPORT_CHROMIUM_EXECUTABLE_PATH or shutil.which("chromium") or shutil.which("google-chrome")
        if not executable or not Path(executable).is_file():
            raise HTTPException(503, "PDF generation is temporarily unavailable")
        async with self._lock:
            with tempfile.TemporaryDirectory(prefix="agos-report-") as directory:
                root = Path(directory)
                document = root / "report.html"
                document.write_text(build_html(report, generated_at), encoding="utf-8")
                command = [executable, "--headless", "--disable-gpu", "--disable-dev-shm-usage", "--disable-background-networking", "--disable-extensions", "--no-first-run", "--no-default-browser-check", "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=0", f"--user-data-dir={root / 'profile'}", "about:blank"]
                if settings.REPORT_CHROMIUM_NO_SANDBOX:
                    command.insert(1, "--no-sandbox")
                process = None
                try:
                    async with asyncio.timeout(settings.REPORT_PDF_TIMEOUT_SECONDS):
                        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL, start_new_session=True)
                        content = await self._print(process, root, document)
                    if not content.startswith(b"%PDF-") or len(content) > 20*1024*1024:
                        raise HTTPException(500, "Could not generate the PDF. Please try again.")
                    return content
                except TimeoutError:
                    raise HTTPException(504, "PDF generation timed out. Please try again.") from None
                except OSError:
                    raise HTTPException(503, "PDF generation is temporarily unavailable") from None
                except (RuntimeError, ValueError, KeyError, WebSocketException):
                    raise HTTPException(500, "Could not generate the PDF. Please try again.") from None
                finally:
                    if process:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        await process.wait()


pdf_renderer = PDFRenderer()
