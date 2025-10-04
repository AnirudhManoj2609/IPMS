from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from collections import defaultdict
import logging
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Film Budget Tracker - Department Report")
load_dotenv()

# --- MONGODB SETUP ---
MONGO_URL = os.getenv("MONGO")
DB_NAME = "budget_tracker"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
budgets_col = db["budgets"]
expenses_col = db["expenses"]
personnel_col = db["personnel"]  # assuming you have personnel collection

# ----- Helper Functions -----
async def get_expenses_by_head(project_id: str):
    """
    Aggregates expenses by department head (role lead).
    Returns a dict of {head_name: {category: [expenses]}}
    """
    # Fetch all personnel who are role leads
    role_heads = await personnel_col.find({"project_id": project_id, "is_role_lead": True}).to_list(None)
    head_map = {head["_id"]: head["name"] for head in role_heads}

    # Fetch all expenses for this project
    expenses = await expenses_col.find({"project_id": project_id}).to_list(None)

    # Group expenses by head and category
    report_data = defaultdict(lambda: defaultdict(list))
    for exp in expenses:
        reporter_id = exp.get("reporter_id")  # assuming each expense has reporter_id
        head_name = head_map.get(reporter_id, "Unassigned")
        report_data[head_name][exp["category"]].append({
            "amount": exp["amount"],
            "description": exp.get("description", ""),
            "date": exp["date"]
        })
    return report_data

async def get_budget_map(project_id: str):
    """
    Returns a map of {category: planned_amount} for comparison
    """
    budgets = await budgets_col.find({"project_id": project_id}).to_list(None)
    return {b["category"]: b["planned_amount"] for b in budgets}

# ----- Endpoint -----
@app.get("/project/{project_id}/department_report")
async def department_report(project_id: str):
    """
    Generates a structured report by department/role head
    """
    report_data = await get_expenses_by_head(project_id)
    if not report_data:
        raise HTTPException(status_code=404, detail="No expenses found for this project.")

    budget_map = await get_budget_map(project_id)

    formatted_report = []

    for head, categories in report_data.items():
        head_total = 0
        category_reports = []
        for cat, expenses in categories.items():
            cat_total = sum(e["amount"] for e in expenses)
            head_total += cat_total
            expense_details = [
                f"{e['date']}: {e['description']} - ${e['amount']:.2f}" for e in expenses
            ]
            category_reports.append({
                "category": cat,
                "planned_budget": budget_map.get(cat, None),
                "spent": cat_total,
                "remaining": max(0, budget_map.get(cat, 0) - cat_total if cat in budget_map else 0),
                "expenses": expense_details
            })
        formatted_report.append({
            "department_head": head,
            "total_spent": head_total,
            "categories": category_reports
        })

    return {"project_id": project_id, "department_report": formatted_report}
