# Skylark Drones — Monday.com Executive BI Agent

An AI-powered Business Intelligence Agent that answers founder-level commercial and operational queries by querying Monday.com Deals and Work Orders boards dynamically[cite: 1].

## Architecture
- **UI Layer**: Streamlit web application with conversational executive chat and live health monitors.
- **Query Planner**: Maps natural language prompts to structured JSON query intents using Gemini.
- **Data Client**: Direct GraphQL API v2 integration with Monday.com featuring cursor pagination.
- **Normalization Layer**: Resilient schema mapping, header deduplication, and anomaly isolation.
- **Deterministic BI Engine**: Pure Python calculation engine for weighted pipeline, billing, AR, and win rates.
- **Executive Synthesizer**: Formats deterministic metrics into founder-ready briefings.

## Local Setup

1. **Clone Repository**:
   ```bash
   git clone [https://github.com/hiransuresh/monday-bi-agent.git](https://github.com/hiransuresh/monday-bi-agent.git)
   cd monday-bi-agent
