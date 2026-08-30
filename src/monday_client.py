import os
import requests
import pandas as pd
from typing import Dict, Any, List, Optional
from src.normalization import normalize_deals_df, normalize_work_orders_df

MONDAY_API_URL = "https://api.monday.com/v2"

class MondayDataClient:
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("MONDAY_API_TOKEN", "")
        self.headers = {
            "Authorization": self.api_token,
            "Content-Type": "application/json",
            "API-Version": "2024-01"
        }

    def health_check(self) -> Dict[str, Any]:
        """Verify Monday API credentials."""
        if not self.api_token:
            return {"status": "error", "message": "MONDAY_API_TOKEN is not configured."}
        
        query = "query { me { id name email } }"
        try:
            resp = requests.post(MONDAY_API_URL, json={"query": query}, headers=self.headers, timeout=10)
            data = resp.json()
            if "errors" in data:
                return {"status": "error", "message": data["errors"][0].get("message", "API Error")}
            return {"status": "ok", "user": data.get("data", {}).get("me", {})}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_board_items(self, board_id: str) -> List[Dict[str, Any]]:
        """Fetch all items from a Monday board using cursor pagination."""
        if not self.api_token:
            raise ValueError("MONDAY_API_TOKEN is missing.")

        all_items = []
        cursor = None
        
        while True:
            if cursor:
                query = """
                query ($cursor: String!) {
                    next_items_page(cursor: $cursor, limit: 100) {
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
                variables = {"cursor": cursor}
            else:
                query = """
                query ($boardId: [ID!]) {
                    boards(ids: $boardId) {
                        items_page(limit: 100) {
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
                variables = {"boardId": [str(board_id)]}

            resp = requests.post(
                MONDAY_API_URL, 
                json={"query": query, "variables": variables}, 
                headers=self.headers, 
                timeout=20
            )
            data = resp.json()
            
            if "errors" in data:
                raise RuntimeError(f"Monday API Error: {data['errors'][0].get('message')}")
            
            if not cursor:
                boards = data.get("data", {}).get("boards", [])
                if not boards:
                    break
                page_data = boards[0].get("items_page", {})
            else:
                page_data = data.get("data", {}).get("next_items_page", {})

            items = page_data.get("items", [])
            all_items.extend(items)
            
            cursor = page_data.get("cursor")
            if not cursor or len(items) == 0:
                break
                
        return all_items

    def fetch_deals_board(self, board_id: str) -> pd.DataFrame:
        """Fetch Deals from Monday and convert to normalized DataFrame."""
        items = self.get_board_items(board_id)
        records = []
        for item in items:
            rec = {"Deal Name": item.get("name")}
            for col in item.get("column_values", []):
                col_id = col.get("id", "")
                text_val = col.get("text")
                rec[col_id] = text_val
            records.append(rec)
        
        raw_df = pd.DataFrame(records)
        return normalize_deals_df(raw_df)

    def fetch_work_orders_board(self, board_id: str) -> pd.DataFrame:
        """Fetch Work Orders from Monday and convert to normalized DataFrame."""
        items = self.get_board_items(board_id)
        records = []
        for item in items:
            rec = {"Deal name masked": item.get("name")}
            for col in item.get("column_values", []):
                col_id = col.get("id", "")
                text_val = col.get("text")
                rec[col_id] = text_val
            records.append(rec)
            
        raw_df = pd.DataFrame(records)
        return normalize_work_orders_df(raw_df)
