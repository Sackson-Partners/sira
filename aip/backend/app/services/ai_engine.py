"""
AI Engine: integrates with Anthropic Claude (primary) or OpenAI (fallback)
for auto-generating PIS, PESTEL, EIN analyses, and deal summaries.
"""
import json
import asyncio
from typing import Any, Optional

from ..core.config import settings


async def _call_claude(system: str, user: str, model: Optional[str] = None) -> str:
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=model or settings.AI_MODEL,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text
    except Exception as e:
        raise RuntimeError(f"Claude API error: {e}")


async def _call_openai(system: str, user: str) -> str:
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=4096,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {e}")


async def _ai_call(system: str, user: str) -> str:
    """Try Claude first, fall back to OpenAI if Claude key not set."""
    if settings.ANTHROPIC_API_KEY:
        return await _call_claude(system, user)
    elif settings.OPENAI_API_KEY:
        return await _call_openai(system, user)
    else:
        raise RuntimeError("No AI API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")


def _parse_json_response(text: str) -> dict:
    """Extract JSON from AI response, handling markdown code blocks."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


async def generate_pis(project) -> dict:
    """Generate Project Information Summary using AI."""
    system = """You are an expert investment analyst at a private equity / alternative investment firm.
Generate a structured Project Information Summary (PIS) in JSON format.
Return ONLY valid JSON with no extra text or markdown."""

    user = f"""Generate a PIS for the following investment project:
- Name: {project.name}
- Type: {project.project_type}
- Sector: {project.sector or 'Not specified'}
- Country: {project.country or 'Not specified'}
- Description: {project.description or 'Not provided'}
- Target Raise: {project.target_raise} {project.currency if project.target_raise else ''}
- IRR Target: {project.irr_target}%
- Hold Period: {project.hold_period_years} years

Return JSON with these exact keys:
{{
  "executive_summary": "...",
  "investment_thesis": "...",
  "key_highlights": ["bullet 1", "bullet 2", "bullet 3"],
  "market_description": "...",
  "business_model": "...",
  "revenue_model": "...",
  "competitive_advantages": ["...", "..."],
  "key_risks": ["...", "..."],
  "risk_mitigants": ["...", "..."],
  "deal_structure": "...",
  "use_of_proceeds": "...",
  "exit_strategy": "...",
  "exit_options": ["...", "..."]
}}"""

    try:
        raw = await _ai_call(system, user)
        return _parse_json_response(raw)
    except Exception as e:
        return {"executive_summary": f"AI generation failed: {e}. Please fill in manually."}


async def generate_pestel(project) -> dict:
    """Generate PESTEL analysis using AI."""
    system = """You are an expert investment and macro analyst.
Generate a comprehensive PESTEL analysis for an investment project.
Return ONLY valid JSON."""

    user = f"""Generate a PESTEL analysis for:
- Project: {project.name}
- Sector: {project.sector or 'General'}
- Country/Region: {project.country or 'Global'}
- Project Type: {project.project_type}
- Description: {project.description or ''}

Return JSON:
{{
  "political_factors": [{{"factor": "...", "description": "...", "impact": "high/medium/low", "likelihood": "high/medium/low"}}],
  "political_score": 7.5,
  "political_summary": "...",
  "economic_factors": [...],
  "economic_score": 7.0,
  "economic_summary": "...",
  "social_factors": [...],
  "social_score": 6.5,
  "social_summary": "...",
  "technological_factors": [...],
  "technological_score": 8.0,
  "technological_summary": "...",
  "environmental_factors": [...],
  "environmental_score": 7.0,
  "environmental_summary": "...",
  "legal_factors": [...],
  "legal_score": 6.0,
  "legal_summary": "...",
  "overall_score": 7.0,
  "overall_assessment": "...",
  "overall_impact": "medium"
}}"""

    try:
        raw = await _ai_call(system, user)
        return _parse_json_response(raw)
    except Exception as e:
        return {"overall_assessment": f"AI generation failed: {e}. Please fill in manually."}


async def generate_ein(project) -> dict:
    """Generate Economic Impact Note using AI."""
    system = """You are an impact investment analyst specializing in economic and social impact measurement.
Generate an Economic Impact Note (EIN) for an investment project.
Return ONLY valid JSON."""

    user = f"""Generate an EIN for:
- Project: {project.name}
- Sector: {project.sector or 'General'}
- Country: {project.country or 'Not specified'}
- Target Raise: {project.target_raise} {project.currency if project.target_raise else 'USD'}
- Description: {project.description or ''}

Return JSON:
{{
  "impact_thesis": "...",
  "jobs_created_direct": 150,
  "jobs_created_indirect": 450,
  "gdp_contribution": 25.5,
  "gdp_unit": "USD M",
  "local_procurement_percent": 60.0,
  "communities_impacted": 5,
  "population_benefited": 50000,
  "social_impact_areas": ["education", "employment", "infrastructure"],
  "sdg_alignment": [8, 9, 11],
  "esg_score": 72.0,
  "co2_reduction_tonnes": 5000.0,
  "leverage_ratio": 3.5,
  "impact_measurement_framework": "...",
  "impact_kpis": [{{"kpi": "...", "baseline": "...", "target": "...", "unit": "..."}}],
  "impact_risks": [{{"risk": "...", "mitigation": "..."}}]
}}"""

    try:
        raw = await _ai_call(system, user)
        return _parse_json_response(raw)
    except Exception as e:
        return {"impact_thesis": f"AI generation failed: {e}. Please fill in manually."}


async def generate_deal_summary(project, pis=None, pestel=None) -> str:
    """Generate a 1-page deal summary memo."""
    system = "You are a senior investment professional. Generate a concise deal summary memo."
    context = f"Project: {project.name}\nSector: {project.sector}\nCountry: {project.country}\nType: {project.project_type}\nTarget: {project.target_raise} {project.currency}"
    if pis and pis.investment_thesis:
        context += f"\nThesis: {pis.investment_thesis}"
    user = f"Write a 300-word deal summary memo for:\n{context}"
    try:
        return await _ai_call(system, user)
    except Exception as e:
        return f"AI summary unavailable: {e}"


async def ai_chat(question: str, context: str = "") -> str:
    """General AI Q&A for the platform."""
    system = """You are an expert AI assistant for an Alternative Investment Platform (AIP).
Help users understand investment data, analyze deals, and make informed decisions.
Be concise, professional, and data-driven."""
    user = f"{('Context:\n' + context + '\n\n') if context else ''}Question: {question}"
    try:
        return await _ai_call(system, user)
    except Exception as e:
        return f"AI assistant unavailable: {e}"
