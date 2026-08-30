# Skylark Drones BI Agent — Decision Log

## 1. Key Assumptions
- **Read-Only Scope**: The agent operates strictly in read-only mode over Monday.com boards. It never mutates or writes back records.
- **Closure Probability Weights**: Deals missing explicit probabilities (74.6% of records) are excluded from the *weighted* pipeline to prevent arbitrary bias, while standard *unweighted* pipeline aggregates all valid open deal values. Probability categories are mapped deterministically (`High` = 0.80, `Medium` = 0.50, `Low` = 0.20).
- **Cross-Board Entity Matching**: Deals and Work Orders share common clients and deal concepts but do not have an enforced foreign key. Matches are established by normalizing client code numeric suffixes (e.g., `COMPANY089` <-> `WOCOMPANY_089`) and sector dimensions, surfacing non-1:1 caveats.
- **Financial Granularity**: Contract amounts, billed values, collected totals, and accounts receivable (AR) are treated independently. Revenue is never conflated with pipeline or contracted values.

## 2. Technical Stack & Trade-Offs
- **Frontend / Application Framework**: Streamlit was chosen for its fast deployment, native session state, responsive chat elements, and built-in metric rendering within a 6-hour assessment window.
- **API vs. MCP**: Selected direct Monday.com GraphQL API v2 over MCP. Direct GraphQL enables seamless cursor-based pagination, dynamic column title resolution, zero-daemon cloud deployment on Streamlit Community Cloud, and fine-grained error control.
- **Deterministic Python vs. LLM Arithmetic**: All metric calculations, filters, groupings, and sums are computed strictly in Python via Pandas. Google Gemini (`gemini-2.5-flash`) is utilized exclusively for query planning, intent understanding, and executive briefing synthesis, eliminating hallucination risks.

## 3. Handling Messy Data & Anomalies
- **Mid-Sheet Repeated Headers**: Deals dataset contained duplicate header rows where `Deal Status == 'Deal Status'`. The normalization layer strips these dynamically.
- **Negative AR & To-Be-Billed Balances**: 11 work orders with negative receivables and 6 with negative to-be-billed balances (e.g., over-billing/credit notes) are retained in calculations while surfacing an explicit anomaly caveat.
- **Null Safety**: All currency values are cleaned via regex to remove symbols and safely cast to floats without dropping records.

## 4. Interpretation of Leadership Updates
"Leadership updates" is interpreted as a holistic cross-board briefing:
1. **Commercial Funnel**: Total open pipeline value, weighted forecast, win rate, and sector leadership.
2. **Operational Execution**: Delivery progress, active vs. completed projects, and at-risk operational bottlenecks.
3. **Financial Health**: Total contracted volume, billed value, cash collected, and outstanding receivables.
4. **Strategic Risks & Anomalies**: Transparent enumeration of unpopulated probabilities and negative balance accounts.

## 5. What Would Be Improved With More Time
- Implement bi-directional write-backs or task creation in Monday.com for flagged at-risk work orders.
- Add persistent time-series tracking to monitor pipeline velocity and billing conversion week-over-week.
- Integrate vector-based fuzzy matching for unstructured deal-to-project narrative matching.
