"""
Core AI Agent Module for Skylark Drones BI.
Executes deterministic metric routines based on planned queries and
synthesizes founder-grade executive briefings via Gemini.
"""

import os
import json
from typing import Dict, Any, Optional
import pandas as pd
from google import genai
from google.genai import types

from src.query_planner import QueryPlanner
from src.metrics import (
    calculate_pipeline_summary,
    calculate_weighted_pipeline,
    calculate_deals_by_sector,
    calculate_deals_by_stage,
    calculate_work_orders_summary,
    calculate_billing_and_collections,
    calculate_receivables_summary,
    calculate_at_risk_projects,
    calculate_leadership_summary,
    audit_data_quality,
)

SYNTHESIS_SYSTEM_PROMPT = """You are a senior Executive Business Intelligence advisor to the Founders of Skylark Drones.
Your mission is to communicate business performance clearly, concisely, and with strategic precision.

Rules:
1. ALWAYS base your numbers strictly on the verified deterministic evidence provided. NEVER invent or recalculate numerical values.
2. Structure your response in the standard Executive format:
   - ## Executive Answer (1-2 crisp takeaway sentences)
   - ## Key Numbers (Bullet list with formatted metrics and context)
   - ## Strategic Context & Implications (What this means for the business)
   - ## Data Quality & Caveats (State any exclusions, missing probabilities, or negative balance anomalies)
   - ## Recommended Action (Specific next operational/sales step)
3. For Leadership Updates, provide a multi-dimensional summary covering the Sales Funnel, Project Execution, Billing & Collections, and Key Risks.
4. Keep the tone executive, objective, and transparent regarding data limitations.
"""


class SkylarkBIAgent:
    """End-to-end conversational BI agent."""

    def __init__(self, gemini_api_key: Optional[str] = None):
        self.api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.planner = QueryPlanner(api_key=self.api_key)
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception:
                self.client = None

    def execute_plan(
        self,
        plan: Dict[str, Any],
        deals_df: pd.DataFrame,
        wo_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Execute deterministic metrics calculation according to query plan."""
        metric_name = plan.get("metric", "pipeline_summary")
        sector = plan.get("sector_filter")

        if metric_name == "leadership_update" or plan.get("is_leadership_summary"):
            return calculate_leadership_summary(deals_df, wo_df, sector=sector)
        elif metric_name == "weighted_pipeline":
            return calculate_weighted_pipeline(deals_df, sector=sector)
        elif metric_name == "deals_by_sector":
            return calculate_deals_by_sector(deals_df)
        elif metric_name == "deals_by_stage":
            return calculate_deals_by_stage(deals_df, sector=sector)
        elif metric_name == "billing_collections":
            return calculate_billing_and_collections(wo_df, sector=sector)
        elif metric_name == "receivables_summary":
            return calculate_receivables_summary(wo_df, sector=sector)
        elif metric_name == "at_risk_projects":
            return calculate_at_risk_projects(wo_df, sector=sector)
        elif metric_name == "work_orders_summary":
            return calculate_work_orders_summary(wo_df, sector=sector)
        elif metric_name == "data_quality_report":
            return audit_data_quality(deals_df, wo_df)
        else:
            return calculate_pipeline_summary(deals_df, sector=sector)

    def answer_query(
        self,
        user_query: str,
        deals_df: pd.DataFrame,
        wo_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Full BI workflow:
        1. Plan query intent.
        2. Compute deterministic evidence in Python.
        3. Synthesize founder-level answer using Gemini.
        """
        # Step 1: Query planning
        plan = self.planner.plan_query(user_query)

        # Step 2: Deterministic calculation
        evidence = self.execute_plan(plan, deals_df, wo_df)

        # Step 3: Executive synthesis
        answer_text = self._synthesize_answer(user_query, plan, evidence)

        return {
            "query": user_query,
            "plan": plan,
            "evidence": evidence,
            "answer": answer_text,
            "caveats": evidence.get("caveats", [])
        }

    def _synthesize_answer(
        self,
        query: str,
        plan: Dict[str, Any],
        evidence: Dict[str, Any]
    ) -> str:
        """Call Gemini to format structured evidence into an executive briefing."""
        prompt = f"""User Question: "{query}"

Structured Plan:
{json.dumps(plan, indent=2)}

Verified Deterministic Evidence:
{json.dumps(evidence, default=str, indent=2)}

Generate the executive briefing following the required sections."""

        if self.client:
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYNTHESIS_SYSTEM_PROMPT,
                        temperature=0.2,
                    ),
                )
                if response.text:
                    return response.text
            except Exception:
                pass

        # Fallback markdown template if Gemini is unavailable
        return self._format_fallback_response(query, evidence)

    def _format_fallback_response(self, query: str, evidence: Dict[str, Any]) -> str:
        """Deterministic markdown formatter when LLM is offline."""
        lines = [
            "## Executive Answer",
            f"Analysis completed for query: *'{query}'* based on live Monday.com operational data.",
            "",
            "## Key Numbers",
        ]

        for k, v in evidence.items():
            if k not in ["caveats", "sector_breakdown", "stage_breakdown", "at_risk_projects", "anomalous_receivable_records"]:
                if isinstance(v, (int, float)):
                    lines.append(f"- **{k.replace('_', ' ').title()}**: {v:,.2f}" if isinstance(v, float) else f"- **{k.replace('_', ' ').title()}**: {v:,}")
                else:
                    lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")

        caveats = evidence.get("caveats", [])
        if caveats:
            lines.extend(["", "## Data Quality & Caveats"])
            for c in caveats:
                lines.append(f"- ⚠️ {c}")

        lines.extend([
            "",
            "## Recommended Action",
            "- Review high-priority pipeline records and verify unbilled work orders with the operations team."
        ])

        return "\n".join(lines)
