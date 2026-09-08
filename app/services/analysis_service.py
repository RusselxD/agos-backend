import json
import logging

from groq import APIConnectionError, APIStatusError, AsyncGroq

from app.schemas import DailySummaryAnalysisRequest, DailySummaryResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

clients = [AsyncGroq(api_key=key) for key in settings.GROQ_API_KEYS]
MODELS = list(settings.GROQ_MODELS)

FALLBACK_STATUS_CODES = {
    401,  # an individual key is invalid
    403,  # an individual key lacks model access
    404,  # model is unavailable for this account/tier
    408,
    429,
    498,  # Groq flex-tier capacity exceeded
    500,
    502,
    503,
    504,
}
FALLBACK_ERROR_CODES = {
    "model_decommissioned",
    "model_not_found",
    "rate_limit_exceeded",
}


def _get_error_code(error: Exception) -> str | None:
    body = getattr(error, "body", None)
    if not isinstance(body, dict):
        return None

    error_details = body.get("error", body)
    if not isinstance(error_details, dict):
        return None

    code = error_details.get("code")
    return str(code) if code else None


def _should_try_fallback(error: Exception) -> bool:
    if isinstance(error, APIConnectionError):
        return True
    if not isinstance(error, APIStatusError):
        return False

    return (
        error.status_code in FALLBACK_STATUS_CODES
        or _get_error_code(error) in FALLBACK_ERROR_CODES
    )


def _sse_error(message: str) -> str:
    return f"data: {json.dumps({'error': message, 'done': True})}\n\n"

SYSTEM_PROMPT = """
You are an expert waterway monitoring analyst. Analyze daily sensor, visible surface-obstruction, and weather
summary data from a drainage/waterway monitoring system.

When given data, provide a concise analysis covering:
1. **Overall Risk Assessment** – What is the general risk level across this period?
2. **Critical Days** – Which days were most concerning and why?
3. **Water Level Patterns** – Notable trends or anomalies.
4. **Surface-Obstruction Concerns** – Evaluate visible surface-obstruction evidence without claiming a confirmed subsurface obstruction.
5. **Recommendations** – Actionable steps for operators/responders.

Formatting rules:
- Use **bold** for emphasis and section headings — never use ### or ## 
- Use - for bullet points
- Keep tone professional and actionable
- Never make up data — only reference what's given to you
""".strip()

class AnalysisService:

    async def _stream_with_fallback(self, messages: list, max_tokens: int):
        """
        Try each configured model/API-key pair until one starts producing a
        response. Provider availability errors fall through to the next pair;
        all failures are converted to SSE error events so the response iterator
        never leaks an exception into the ASGI server.
        """
        for model in MODELS:
            for client_index, client in enumerate(clients, start=1):
                emitted_text = False
                try:
                    stream = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        stream=True,
                        max_tokens=max_tokens,
                        temperature=0.4,
                    )

                    async for chunk in stream:
                        text = chunk.choices[0].delta.content
                        if text:
                            emitted_text = True
                            yield f"data: {json.dumps({'text': text})}\n\n"

                    yield f"data: {json.dumps({'done': True})}\n\n"
                    return  # success — stop trying

                except Exception as error:
                    if emitted_text:
                        logger.warning(
                            "Groq stream interrupted after output began "
                            "(model=%s, key=%d, error=%s)",
                            model,
                            client_index,
                            type(error).__name__,
                        )
                        yield _sse_error(
                            "AI analysis was interrupted. Please try again."
                        )
                        return

                    if _should_try_fallback(error):
                        logger.warning(
                            "Groq model/key unavailable; trying fallback "
                            "(model=%s, key=%d, status=%s, code=%s)",
                            model,
                            client_index,
                            getattr(error, "status_code", None),
                            _get_error_code(error),
                        )
                        continue

                    logger.exception(
                        "Groq analysis request failed (model=%s, key=%d)",
                        model,
                        client_index,
                    )
                    yield _sse_error(
                        "AI analysis is temporarily unavailable. Please try again later."
                    )
                    return

        logger.error("All configured Groq model/API-key combinations failed")
        yield _sse_error(
            "AI analysis is temporarily unavailable. Please try again later."
        )


    async def stream_analysis(self, payload: DailySummaryAnalysisRequest):
        """Initial Analysis - streams SSE chunks"""
        data_block = self._format_summaries(payload.summaries)

        prompt = f"""
            Analyze this daily monitoring data from {payload.start_date} to {payload.end_date}:

            {data_block}

            Cover:
            1. **Overall Risk Assessment**
            2. **Critical Days** — which days and why
            3. **Water Level Patterns**
            4. **Surface-Obstruction Concerns**
            5. **Recommendations**
            """.strip()

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        async for chunk in self._stream_with_fallback(messages, max_tokens=1024):
            yield chunk


    def _format_summaries(self, summaries: list[DailySummaryResponse]) -> str:
        """Turn the summary list into a readable block for the prompt"""
        lines = []
        for s in summaries:
            lines.append(
                f"Date: {s.summary_date}\n"
                f"  Risk Score   : {s.min_risk_score} → {s.max_risk_score}\n"
                f"  Water Level  : {s.min_water_level_cm} → {s.max_water_level_cm} cm\n"
                f"  Precipitation: {s.min_precipitation_mm} → {s.max_precipitation_mm} mm\n"
                f"  Surface Obstruction: {s.least_severe_blockage} → {s.most_severe_blockage}\n"
                f"  Weather Code : {s.most_severe_weather_code}\n"
            )
        return "\n".join(lines)
    

analysis_service = AnalysisService()
