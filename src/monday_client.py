"""
Resilient Monday.com GraphQL API v2 Client.
Safely handles cursor pagination, schema discovery, mixed column types,
and authentication validation.
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional
import pandas as pd


class MondayDataClient:
    """Client for querying Monday.com GraphQL API v2 with type safety."""

    API_URL = "https://api.monday.com/v2"
    API_VERSION = "2024-01"

    def __init__(self, api_token: Optional[str] = None):
        raw_token = api_token or os.getenv("MONDAY_API_TOKEN", "")
        # Clean quotes and extra whitespace
        self.api_token = raw_token.strip().strip("'").strip('"')
        
        self.headers = {
            "Authorization": self.api_token,
            "API-Version": self.API_VERSION,
            "Content-Type": "application/json",
        }

    def _execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GraphQL query against Monday.com."""
        if not self.api_token:
            raise ValueError("Monday.com API Token is missing. Please provide a valid token.")

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = requests.post(
                self.API_URL,
                headers=self.headers,
                json=payload,
                timeout=45
            )
            
            # If plain token gave 401, retry once with Bearer prefix
            if response.status_code == 401 and not self.api_token.startswith("Bearer "):
                bearer_headers = {**self.headers, "Authorization": f"Bearer {self.api_token}"}
                response = requests.post(
                    self.API_URL,
                    headers=bearer_headers,
                    json=payload,
                    timeout=45
                )

            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "errors" in data:
                err_msg = "; ".join([e.get("message", str(e)) if isinstance(e, dict) else str(e) for e in data["errors"]])
                raise RuntimeError(f"Monday API Error: {err_msg}")

            if not isinstance(data, dict):
                raise RuntimeError(f"Unexpected response format from Monday.com: {data}")

            return data.get("data", {})
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Network error communicating with Monday.com: {str(e)}")

    def health_check(self) -> Dict[str, Any]:
        """Verify API token validity."""
        query = "query { me { id name email } }"
        try:
            data = self._execute_query(query)
            me = data.get("me") if isinstance(data, dict) else None
            if me and isinstance(me, dict):
                return {"status": "connected", "user": me}
            return {"status": "connected", "user": {"name": "Monday.com User"}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_board_metadata(self, board_id: str) -> Dict[str, Any]:
        """Fetch board columns and metadata."""
        clean_id = str(board_id).strip()
        query = """
        query ($board_id: [ID!]) {
            boards (ids: $board_id) {
                id
                name
                columns {
                    id
                    title
                    type
                }
            }
        }
        """
        data = self._execute_query(query, {"board_id": [clean_id]})
        boards = data.get("boards", []) if isinstance(data, dict) else []
        if not boards or not isinstance(boards, list):
            raise ValueError(f"Board ID {board_id} not found or inaccessible with current token.")
        return boards[0]

    def get_all_items(self, board_id: str) -> List[Dict[str, Any]]:
        """Fetch all items from Monday board using cursor pagination."""
        clean_id = str(board_id).strip()
        board_meta = self.get_board_metadata(clean_id)
        
        col_id_to_title: Dict[str, str] = {}
        if isinstance(board_meta, dict):
            for col in board_meta.get("columns", []):
                if isinstance(col, dict) and "id" in col and "title" in col:
                    col_id_to_title[col["id"]] = col["title"]

        items: List[Dict[str, Any]] = []
        cursor = None

        while True:
            if cursor:
                query = """
                query ($cursor: String!) {
                    next_items_page (cursor: $cursor, limit: 100) {
                        cursor
                        items {
                            id
                            name
                            column_values {
                                id
                                text
                                value
                            }
                        }
                    }
                }
                """
                data = self._execute_query(query, {"cursor": cursor})
                page = data.get("next_items_page", {}) if isinstance(data, dict) else {}
            else:
                query = """
                query ($board_id: [ID!]) {
                    boards (ids: $board_id) {
                        items_page (limit: 100) {
                            cursor
                            items {
                                id
                                name
                                column_values {
                                    id
                                    text
                                    value
                                }
                            }
                        }
                    }
                }
                """
                data = self._execute_query(query, {"board_id": [clean_id]})
                boards = data.get("boards", []) if isinstance(data, dict) else []
                if not boards or not isinstance(boards[0], dict):
                    break
                page = boards[0].get("items_page", {})

            if not isinstance(page, dict):
                break

            raw_items = page.get("items", [])
            if not isinstance(raw_items, list):
                break

            for item in raw_items:
                if not isinstance(item, dict):
                    continue

                record = {
                    "Item ID": item.get("id"),
                    "Item Name": item.get("name")
                }

                col_vals = item.get("column_values", [])
                if isinstance(col_vals, list):
                    for col in col_vals:
                        if isinstance(col, dict):
                            c_id = col.get("id", "")
                            title = col_id_to_title.get(c_id, c_id)
                            text_val = col.get("text")
                            record[title] = text_val if text_val is not None else col.get("value")

                items.append(record)

            cursor = page.get("cursor")
            if not cursor or not raw_items:
                break

        return items

    def get_board_dataframe(self, board_id: str) -> pd.DataFrame:
        """Fetch items into DataFrame."""
        items = self.get_all_items(board_id)
        if not items:
            return pd.DataFrame()
        return pd.DataFrame(items)