import os
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "history")

# Ensure history directory exists
os.makedirs(HISTORY_DIR, exist_ok=True)

class SaveHistoryRequest(BaseModel):
    ticker: str
    markdown: str
    raw_data: dict = None
    valuation_results: dict = None

@router.post("/")
async def save_history(req: SaveHistoryRequest):
    """
    Saves a report to the local history directory.
    """
    report_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    file_path = os.path.join(HISTORY_DIR, f"{report_id}.json")
    
    data = {
        "id": report_id,
        "ticker": req.ticker.upper(),
        "date": timestamp,
        "markdown": req.markdown,
        "raw_data": req.raw_data,
        "valuation_results": req.valuation_results
    }
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return {"id": report_id, "message": "History saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save history: {e}")

@router.get("/")
async def list_history():
    """
    Lists all saved reports in the history directory.
    """
    history_list = []
    
    try:
        if not os.path.exists(HISTORY_DIR):
            return []
            
        for filename in os.listdir(HISTORY_DIR):
            if filename.endswith(".json"):
                file_path = os.path.join(HISTORY_DIR, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    history_list.append({
                        "id": data.get("id"),
                        "ticker": data.get("ticker"),
                        "date": data.get("date")
                    })
        
        # Sort by date descending
        history_list.sort(key=lambda x: x["date"], reverse=True)
        return history_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list history: {e}")

@router.get("/{report_id}")
async def get_history(report_id: str):
    """
    Retrieves a specific report by its ID.
    """
    file_path = os.path.join(HISTORY_DIR, f"{report_id}.json")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report: {e}")

@router.delete("/{report_id}")
async def delete_history(report_id: str):
    """
    Deletes a specific report by its ID.
    """
    file_path = os.path.join(HISTORY_DIR, f"{report_id}.json")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")
        
    try:
        os.remove(file_path)
        return {"id": report_id, "message": "History deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {e}")
