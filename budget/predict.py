from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import io
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from datetime import datetime, timedelta
import re
import logging
from prophet import Prophet
import uuid
import numpy as np
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Film Budget Tracker (MongoDB)")

# ----- MongoDB Setup -----
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "film_budget_db"

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
budgets_col = db["budgets"]
expenses_col = db["expenses"]

# ----- OCR & Expense Categorization -----
def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    img = image.convert('L')
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Brightness(img).enhance(1.2)
    if img.size[0] < 300 or img.size[1] < 300:
        img = img.resize((img.size[0]*2, img.size[1]*2), Image.Resampling.LANCZOS)
    return img

def extract_amount_and_text_from_receipt(file: UploadFile) -> tuple:
    try:
        file.file.seek(0)
        img = Image.open(io.BytesIO(file.file.read()))
        img = preprocess_image_for_ocr(img)
        receipt_text = pytesseract.image_to_string(img, config='--oem 3 --psm 6')

        amounts = [float(x.replace(',', '')) for x in re.findall(r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b', receipt_text)]
        final_amount = max(amounts) if amounts else None
        return final_amount, receipt_text
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return None, ""

def categorize_expense_smart(text: str, available_categories: list) -> str:
    if not text:
        return "Misc"
    text_lower = text.lower()
    categories_keywords = {
        "Food": ["food", "meal", "lunch", "dinner", "snack", "drink", "coffee", "tea"],
        "Actors": ["actor", "talent", "cast", "performer"],
        "Props": ["prop", "furniture", "decor", "set"],
        "Locations": ["location", "venue", "site", "rental"],
        "Equipment": ["camera", "light", "sound", "lens", "tripod"],
        "VFX": ["vfx", "animation", "visual effects"],
        "Costumes": ["costume", "wardrobe", "outfit", "dress"],
        "Transportation": ["transport", "vehicle", "fuel", "truck"],
        "Post Production": ["edit", "color", "audio", "music", "score"]
    }
    scores = {}
    for cat, keywords in categories_keywords.items():
        if cat not in available_categories:
            continue
        score = sum(text_lower.count(k) for k in keywords)
        if score > 0:
            scores[cat] = score
    return max(scores, key=scores.get) if scores else "Misc"

# ----- Helper functions -----
async def get_available_categories(project_id: str) -> list:
    budgets = await budgets_col.find({"project_id": project_id}).to_list(None)
    if not budgets:
        return ["Misc"]
    return [b["category"] for b in budgets]

async def predict_category_spending(project_id: str, category: str, days_ahead: int = 30) -> dict:
    expenses = await expenses_col.find({"project_id": project_id, "category": category}).to_list(None)
    if len(expenses) < 3:
        return {"predicted_total": None, "trend": "insufficient_data", "confidence": "low"}
    try:
        df_exp = pd.DataFrame([{"ds": e["date"], "y": e["amount"]} for e in expenses])
        model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False, changepoint_prior_scale=0.05, interval_width=0.8)
        model.fit(df_exp)
        future_dates = model.make_future_dataframe(periods=days_ahead)
        forecast = model.predict(future_dates)
        future_predictions = forecast[forecast['ds'] > max(df_exp['ds'])]
        predicted_total = future_predictions['yhat'].sum()
        trend_pct = ((future_predictions['yhat'].mean() - df_exp['y'].mean()) / df_exp['y'].mean() * 100)
        trend = "accelerating" if trend_pct > 20 else "increasing" if trend_pct > 5 else "decreasing" if trend_pct < -5 else "stable"
        confidence = "high" if future_predictions['yhat'].std() < future_predictions['yhat'].mean() * 0.3 else "medium"
        return {"predicted_total": round(predicted_total,2), "trend": trend, "confidence": confidence}
    except Exception as e:
        logger.warning(f"Prediction failed: {e}")
        return {"predicted_total": None, "trend": "error", "confidence": "low"}

# ----- Endpoints -----
@app.post("/upload_budget_csv/")
async def upload_budget_csv(file: UploadFile = File(...), project_id: str = Form(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV")

    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    required_columns = {"Category", "Planned_Amount"}
    if not required_columns.issubset(df.columns):
        raise HTTPException(status_code=400, detail="CSV must have Category and Planned_Amount columns")

    # Clear existing budgets for this project
    await budgets_col.delete_many({"project_id": project_id})

    # Insert new budget data
    budget_docs = []
    for _, row in df.iterrows():
        budget_docs.append({
            "project_id": project_id,
            "category": row["Category"].strip(),
            "planned_amount": float(row["Planned_Amount"]),
            "priority": float(row.get("Priority", 1.0)),
            "flexible": float(row.get("Flexible", 0.15))
        })
    if budget_docs:
        await budgets_col.insert_many(budget_docs)

    return {"message": f"{len(budget_docs)} budget items uploaded for project {project_id}", "categories": [b["category"] for b in budget_docs]}

@app.post("/upload_expense/")
async def upload_expense(
    project_id: str = Form(...),
    amount: float = Form(None),
    category: str = Form(None),
    receipt: UploadFile = File(None),
    description: str = Form(None),
    date: str = Form(None)
):
    expense_date = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.utcnow().date()
    extracted_amount, receipt_text = (None, "")
    if receipt and receipt.content_type.startswith('image/'):
        extracted_amount, receipt_text = extract_amount_and_text_from_receipt(receipt)
    final_amount = extracted_amount if extracted_amount is not None else amount
    if not final_amount or final_amount <= 0:
        raise HTTPException(status_code=400, detail="Valid amount is required.")

    available_categories = await get_available_categories(project_id)
    final_category = category or categorize_expense_smart(receipt_text if receipt_text else description, available_categories)
    expense_id = str(uuid.uuid4())

    expense_doc = {
        "_id": expense_id,
        "project_id": project_id,
        "category": final_category,
        "amount": final_amount,
        "date": expense_date.isoformat(),
        "description": description
    }
    await expenses_col.insert_one(expense_doc)
    return {"message": "Expense added", "expense_id": expense_id, "category": final_category, "amount": final_amount, "date": expense_date.isoformat()}

@app.get("/project/{project_id}/summary")
async def get_project_summary(project_id: str):
    budgets = await budgets_col.find({"project_id": project_id}).to_list(None)
    expenses = await expenses_col.find({"project_id": project_id}).to_list(None)
    expenses_by_category = {}
    for e in expenses:
        expenses_by_category[e["category"]] = expenses_by_category.get(e["category"], 0) + e["amount"]
    summary = []
    for item in budgets:
        spent = expenses_by_category.get(item["category"], 0)
        summary.append({
            "category": item["category"],
            "planned": item["planned_amount"],
            "spent": spent,
            "remaining": max(0, item["planned_amount"] - spent)
        })
    return {"project_id": project_id, "summary": summary}

@app.get("/project/{project_id}/predictions")
async def get_project_predictions(project_id: str, days_ahead: int = 30):
    budgets = await budgets_col.find({"project_id": project_id}).to_list(None)
    predictions = []
    for item in budgets:
        prediction = await predict_category_spending(project_id, item["category"], days_ahead)
        predictions.append({"category": item["category"], "prediction": prediction})
    return {"project_id": project_id, "predictions": predictions}
