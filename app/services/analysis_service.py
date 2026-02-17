from groq import AsyncGroq
from app.schemas import DailySummaryAnalysisRequest, DailySummaryResponse, FollowUpRequest
from app.core.config import settings

import json

client = AsyncGroq(api_key=settings.GROQ_API_KEY)
MODELS = [
    "llama-3.1-8b-instant",      # smallest, try first
    "gemma2-9b-it",              # Google's model, separate quota
    "mixtral-8x7b-32768",        # Mistral, separate quota
]

SYSTEM_PROMPT = """
You are an expert flood monitoring analyst. Analyze daily sensor and weather 
summary data from a drainage/flood monitoring system.

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

class AnalysisService:

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

        for model in MODELS:
            try:
                stream = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    stream=True,
                    max_tokens=1024,
                    temperature=0.4,
                )

                async for chunk in stream:
                    text = chunk.choices[0].delta.content
                    if text:
                        yield f"data: {json.dumps({'text': text})}\n\n"

                yield f"data: {json.dumps({'done': True})}\n\n"
                return

            except Exception as e:
                if "rate_limit_exceeded" in str(e) or "429" in str(e):
                    continue
                raise

        yield f"data: {json.dumps({'error': 'Rate limit reached on all models. Try again later.'})}\n\n"


    async def stream_follow_up(self, payload: FollowUpRequest):
        """Follow-up chat — includes conversation history + data context."""
        data_block = self._format_summaries(payload.summaries)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Here is the monitoring data for context:\n{data_block}"
            },
            {"role": "assistant", "content": "Understood. I have the monitoring data. What would you like to know?"},
            *payload.history,
            {"role": "user", "content": payload.question},
        ]

        for model in MODELS:
            try:
                stream = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    max_tokens=512,
                    temperature=0.4,
                )

                async for chunk in stream:
                    text = chunk.choices[0].delta.content
                    if text:
                        yield f"data: {json.dumps({'text': text})}\n\n"

                yield f"data: {json.dumps({'done': True})}\n\n"
                return

            except Exception as e:
                if "rate_limit_exceeded" in str(e) or "429" in str(e):
                    continue
                raise

        yield f"data: {json.dumps({'error': 'Rate limit reached on all models. Try again later.'})}\n\n"


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