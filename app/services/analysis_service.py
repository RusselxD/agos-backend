from groq import AsyncGroq
from app.schemas import DailySummaryAnalysisRequest, DailySummaryResponse, FollowUpRequest
from app.core.config import settings

import json

clients = [AsyncGroq(api_key=key) for key in settings.GROQ_API_KEYS]
MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
]

SYSTEM_PROMPT = """
You are an expert waterway monitoring analyst. Analyze daily sensor, blockage, and weather 
summary data from a drainage/waterway monitoring system.

When given data, provide a concise analysis covering:
1. **Overall Risk Assessment** – What is the general risk level across this period?
2. **Critical Days** – Which days were most concerning and why?
3. **Water Level Patterns** – Notable trends or anomalies.
4. **Blockage Concerns** – Evaluate blockage progression and debris buildup.
5. **Recommendations** – Actionable steps for operators/responders.

Formatting rules:
- Use **bold** for emphasis and section headings — never use ### or ## 
- Use - for bullet points
- Keep tone professional and actionable
- Never make up data — only reference what's given to you
""".strip()

FOLLOW_UP_SYSTEM_PROMPT = """
You are an expert waterway monitoring analyst in an ongoing chat.

For follow-up questions:
- Answer the user's latest question directly first
- Use prior conversation history and provided monitoring data as context
- Keep responses concise unless the user asks for more detail
- Do not force the 5-section report format unless the user explicitly asks for a full report
- Never make up data; only reference provided context
""".strip()

class AnalysisService:

    async def _stream_with_fallback(self, messages: list, max_tokens: int):
        """
        Tries every model first, then when each primary model exhausts its rate limit, it falls back to the next one.
        Yields SSE chunks.
        """
        for model in MODELS:
            for client in clients:
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
                            yield f"data: {json.dumps({'text': text})}\n\n"

                    yield f"data: {json.dumps({'done': True})}\n\n"
                    return  # success — stop trying

                except Exception as e:
                    error = str(e)
                    if any(code in error for code in ["rate_limit_exceeded", "429", "model_decommissioned"]):
                        continue  # try next model/client
                    raise  # unexpected error — bubble up

        # every client + model combination exhausted
        yield f"data: {json.dumps({'error': 'All models and API keys are rate limited. Try again later.'})}\n\n"


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
            4. **Blockage Concerns**
            5. **Recommendations**
            """.strip()

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        async for chunk in self._stream_with_fallback(messages, max_tokens=1024):
            yield chunk


    async def stream_follow_up(self, payload: FollowUpRequest):
        """Follow-up chat — includes conversation history + data context."""
        data_block = self._format_summaries(payload.summaries)

        messages = [
            {"role": "system", "content": FOLLOW_UP_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Here is the monitoring data for context. Use it when relevant to answer follow-up questions.\n"
                    f"{data_block}"
                ),
            },
            *payload.history,
            {"role": "user", "content": payload.question},
        ]

        async for chunk in self._stream_with_fallback(messages, max_tokens=512):
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
                f"  Blockage     : {s.least_severe_blockage} → {s.most_severe_blockage}\n"
                f"  Debris Count : {s.min_debris_count} → {s.max_debris_count}\n"
                f"  Weather Code : {s.most_severe_weather_code}\n"
            )
        return "\n".join(lines)
    

analysis_service = AnalysisService()
