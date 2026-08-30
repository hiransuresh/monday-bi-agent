"""
Query Planning Module.
Uses Google Gemini to parse natural language questions into structured execution plans.
Falls back to heuristic rule-based intent resolution if LLM is unavailable.
"""

import os
import json
import re
from typing import Dict, Any, Optional
from google import genai
from google.genai import types


PLANNER_SYSTEM_PROMPT = """You are an expert BI Query Planner for Skylark Drones.
Analyze the user's question and map it to a structured JSON query plan.

Available Boards:
1. 'deals': Sales pipeline, stages, won/lost/dead/open status, probability, weighted pipeline, deal values.
2. 'work_orders': Execution status, project delivery, contracted amounts, billing status, collected amounts, receivables, at-risk projects.
3. 'cross_board': Combined commercial and operational performance, company-wide leadership briefings, sector-level end-to-end view.

Valid Metrics:
- 'pipeline_summary'
- 'weighted_pipeline'
- 'deals_by_sector'
- 'deals_by_stage'
- 'won_lost_summary'
- 'work_orders_summary'
- 'billing_collections'
- 'receivables_summary'
- 'at_risk_projects'
- 'leadership_update'
- 'data_quality_report'
- 'general_query'

Return ONLY a valid JSON object matching this exact schema:
{
  "board_scope": "deals" | "work_orders" | "cross_board",
  "metric": "<one of the valid metrics listed above>",
  "sector_filter": "<sector name like Mining, Renewables, Powerline, Railways, or null>",
  "status_filter": "<deal or execution status if specified, or null>",
  "is_leadership_summary": true | false,
  "user_intent_summary": "<concise 1-sentence summary of what the user wants>"
}
"""


class QueryPlanner:
    """Plans and structures user queries for deterministic metric execution."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception:
                self.client = None

    def plan_query(self, user_query: str) -> Dict[str, Any]:
        """Convert natural language query to structured plan via Gemini or heuristics."""
        if self.client:
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=user_query,
                    config=types.GenerateContentConfig(
                        system_instruction=PLANNER_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                if response.text:
                    return json.loads(response.text)
            except Exception:
                # Graceful fallback to deterministic heuristics
                pass

        return self._heuristic_planner(user_query)

    def _heuristic_planner(self, query: str) -> Dict[str, Any]:
        """Rule-based query understanding fallback."""
        q = query.lower()

        # Sector detection
        sector = None
        for s in ["mining", "renewables", "railways", "powerline", "construction", "dsp", "tender", "aviation"]:
            if s in q:
                sector = s.capitalize()
                break

        # Leadership / cross-board intent
        if any(k in q for k in ["leadership", "executive", "briefing", "overall", "combine", "company update"]):
            return {
                "board_scope": "cross_board",
                "metric": "leadership_update",
                "sector_filter": sector,
                "status_filter": None,
                "is_leadership_summary": True,
                "user_intent_summary": f"Generate leadership update{f' for {sector}' if sector else ''}.",
            }

        # Data quality intent
        if any(k in q for k in ["data quality", "missing data", "nulls", "anomalies", "hygiene", "audit"]):
            return {
                "board_scope": "cross_board",
                "metric": "data_quality_report",
                "sector_filter": sector,
                "status_filter": None,
                "is_leadership_summary": False,
                "user_intent_summary": "Review data quality and anomalies across boards.",
            }

        # Work orders intent
        if any(k in q for k in ["billed", "billing", "collected", "collection", "receivable", "ar", "work order", "execution", "project", "risk"]):
            if any(k in q for k in ["risk", "delayed", "stuck", "paused", "pending"]):
                metric = "at_risk_projects"
            elif any(k in q for k in ["receivable", "outstanding", "uncollected", "ar"]):
                metric = "receivables_summary"
            elif any(k in q for k in ["billed", "collected", "invoice"]):
                metric = "billing_collections"
            else:
                metric = "work_orders_summary"

            return {
                "board_scope": "work_orders",
                "metric": metric,
                "sector_filter": sector,
                "status_filter": None,
                "is_leadership_summary": False,
                "user_intent_summary": f"Calculate {metric} for work orders{f' in {sector}' if sector else ''}.",
            }

        # Deals pipeline intent (default)
        if "weighted" in q:
            metric = "weighted_pipeline"
        elif "stage" in q:
            metric = "deals_by_stage"
        elif "sector" in q or sector:
            metric = "deals_by_sector"
        elif any(k in q for k in ["won", "lost", "dead", "win rate"]):
            metric = "won_lost_summary"
        else:
            metric = "pipeline_summary"

        return {
            "board_scope": "deals",
            "metric": metric,
            "sector_filter": sector,
            "status_filter": None,
            "is_leadership_summary": False,
            "user_intent_summary": f"Analyze deals pipeline for {metric}{f' in {sector}' if sector else ''}.",
        }
