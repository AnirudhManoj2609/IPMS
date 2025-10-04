from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, String, Float, Date, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pandas as pd
import io
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from datetime import datetime, timedelta
import uuid
import re
from prophet import Prophet
import logging
import numpy as np
from typing import List, Dict, Optional, Any

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NOTE: Set your actual database URL here!
DATABASE_URL = "sqlite:///./budget_tracker.db"  # Example SQLite URL

# --- DATABASE SETUP ---
Base = declarative_base()
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine)

def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# --- SQLALCHEMY MODELS ---

class BudgetItem(Base):
    __tablename__ = "budget_items"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String, index=True)
    planned_amount = Column(Float)
    project_id = Column(String, index=True)
    created_at = Column(Date, default=datetime.utcnow)
    priority = Column(Float, default=1.0)  # Priority for reallocation (higher is more critical)
    flexible = Column(Float, default=0.15)  # How flexible this budget is (0-1, higher is more flexible)

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String, index=True)
    amount = Column(Float)
    date = Column(Date)
    project_id = Column(String, index=True)
    receipt_path = Column(String, nullable=True)
    created_at = Column(Date, default=datetime.utcnow)

class RentalItem(Base):
    __tablename__ = "rental_items"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    description = Column(String)
    vendor = Column(String)
    rental_fee = Column(Float)
    return_date = Column(Date, index=True)
    returned_on = Column(Date, nullable=True) # Actual return date (NULL if not returned)
    project_id = Column(String, index=True)
    created_at = Column(Date, default=datetime.utcnow)

class BudgetTimeline(Base):
    __tablename__ = "budget_timeline"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String, index=True)
    planned_daily_spend = Column(Float) # The amount planned to be spent on a specific day for a category
    target_date = Column(Date, index=True) # The date for this planned spend
    project_id = Column(String, index=True)
    created_at = Column(Date, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# --- FASTAPI APP INITIALIZATION ---
app = FastAPI(title="AI Film Budget Tracker with Dynamic Prediction")

# --- UTILITY FUNCTIONS (OCR & CATEGORIZATION) ---

def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    img = image.convert('L')
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    img = img.filter(ImageFilter.SHARPEN)
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.2)
    if img.size[0] < 300 or img.size[1] < 300:
        img = img.resize((img.size[0]*2, img.size[1]*2), Image.Resampling.LANCZOS)
    return img

def extract_amount_and_text_from_receipt(file: UploadFile) -> tuple:
    try:
        file.file.seek(0)
        img = Image.open(io.BytesIO(file.file.read()))
        img = preprocess_image_for_ocr(img)
        
        configs = [
            '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.,$€£₹ ',
            '--oem 3 --psm 4 -c tessedit_char_whitelist=0123456789.,$€£₹ ',
            '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789.,$€£₹ ',
        ]
        
        combined_text = "\n".join([pytesseract.image_to_string(img, config=config) for config in configs])
        
        patterns = [
            r'(?:total\s*\(usd\)|total|grand total|final total)[:\s]*[₹$€£]?\s*([\d,]+\.?\d{0,2})',
            r'[₹$€£]\s*([\d,]+\.?\d{0,2})',
            r'(?:subtotal|balance|amount due)[:\s]*[₹$€£]?\s*([\d,]+\.?\d{0,2})',
        ]
        
        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                clean_num = match.replace(',', '').replace(' ', '')
                clean_num = re.sub(r'[^\d.]', '', clean_num)
                try:
                    if clean_num and clean_num.count('.') <= 1:
                        amt = float(clean_num)
                        if 0.10 <= amt <= 1000000:
                            amounts.append(amt)
                except ValueError:
                    continue
        
        final_amount = max(amounts) if amounts else None
        return final_amount, combined_text
        
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return None, ""

def categorize_expense_smart(text: str, available_categories: list) -> str:
    if not text:
        return "Misc"
    
    text_lower = text.lower()
    
    category_patterns = {
        "Food": [r'\bfood\b', r'\bcatering\b', r'\bmeal\b', r'\blunch\b', r'\bdinner\b', r'\bbreakfast\b', r'\bsnack\b', r'\brestaurant\b'],
        "Actors": [r'\bactor\b', r'\btalent\b', r'\bcast\b', r'\bstunt\b', r'\bextra\b'],
        "Props": [r'\bprop\b', r'\bfurniture\b', r'\bset dressing\b'],
        "Locations": [r'\blocation\b', r'\bvenue\b', r'\bsite\b', r'\bpermits\b'],
        "Equipment": [r'\bequipment\b', r'\bcamera\b', r'\blight\b', r'\bsound\b'],
        "Transportation": [r'\btransport\b', r'\bvehicle\b', r'\btruck\b', r'\bfuel\b', r'\bparking\b', r'\bgas\b'],
    }
    
    category_scores = {}
    
    for category, patterns_list in category_patterns.items():
        if category not in available_categories:
            continue
            
        score = sum(len(re.findall(pattern, text_lower)) for pattern in patterns_list) * 2
        
        if score > 0:
            category_scores[category] = score
    
    if category_scores:
        return max(category_scores.items(), key=lambda x: x[1])[0]
    
    return "Misc"

def get_available_categories(session, project_id: str) -> list:
    categories = session.query(BudgetItem.category).filter_by(project_id=project_id).distinct().all()
    return [cat[0] for cat in categories] if categories else ["Misc"]

# --- AI & PREDICTION FUNCTIONS ---

def predict_category_spending(session, project_id: str, category: str, days_ahead: int = 30) -> dict:
    """Prophet prediction for future category spending."""
    expenses = session.query(Expense).filter_by(
        project_id=project_id, 
        category=category
    ).order_by(Expense.date).all()
    
    if len(expenses) < 3:
        return {
            "predicted_total": None,
            "daily_average": None,
            "trend": "insufficient_data",
            "confidence": "low",
            "error": "Need at least 3 expenses for prediction"
        }
    
    try:
        df_exp = pd.DataFrame([{"ds": e.date, "y": e.amount} for e in expenses])
        
        # Prophet model setup
        model = Prophet(
            daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False,
            changepoint_prior_scale=0.05, interval_width=0.80, seasonality_mode='multiplicative'
        )
        model.fit(df_exp)
        
        # Predict future
        future_dates = model.make_future_dataframe(periods=days_ahead)
        forecast = model.predict(future_dates)
        
        future_predictions = forecast[forecast['ds'] > max(df_exp['ds'])]
        predicted_future_spend = future_predictions['yhat'].sum()
        future_avg = future_predictions['yhat'].mean()
        
        # Trend and Confidence Calculation
        recent_actual = df_exp.tail(5)['y'].mean()
        trend_pct = ((future_avg - recent_actual) / recent_actual * 100) if recent_actual > 0 else 0
        trend = "accelerating" if trend_pct > 20 else ("increasing" if trend_pct > 5 else ("decreasing" if trend_pct < -5 else "stable"))
        prediction_variance = future_predictions['yhat'].std()
        confidence = "high" if prediction_variance < future_avg * 0.3 else "medium" if prediction_variance < future_avg * 0.6 else "low"
        
        return {
            "predicted_total": round(predicted_future_spend, 2),
            "daily_average": round(future_avg, 2),
            "trend": trend,
            "trend_percentage": round(trend_pct, 2),
            "confidence": confidence,
            "upper_bound": round(future_predictions['yhat_upper'].sum(), 2),
            "lower_bound": round(future_predictions['yhat_lower'].sum(), 2)
        }
        
    except Exception as e:
        logger.warning(f"Prophet prediction failed for {category}: {e}")
        return {"predicted_total": None, "daily_average": None, "trend": "error", "confidence": "low", "error": str(e)}

def calculate_reallocation_suggestions(session, project_id: str) -> list:
    """
    Smart budget reallocation suggestions for cost cutting and optimization.
    """
    budget_items = session.query(BudgetItem).filter_by(project_id=project_id).all()
    if len(budget_items) < 2: return []
    
    categories_analysis = []
    
    for item in budget_items:
        total_spent = session.query(func.sum(Expense.amount)).filter_by(project_id=project_id, category=item.category).scalar() or 0
        prediction = predict_category_spending(session, project_id, item.category, days_ahead=30)
        
        if prediction.get("predicted_total") is not None:
            predicted_total_end = total_spent + prediction["predicted_total"]
            overspend_amount = predicted_total_end - item.planned_amount
            overspend_pct = (overspend_amount / item.planned_amount * 100) if item.planned_amount > 0 else 0
            
            categories_analysis.append({
                "category": item.category,
                "planned": item.planned_amount,
                "spent": total_spent,
                "predicted_total": predicted_total_end,
                "overspend_amount": overspend_amount,
                "overspend_pct": overspend_pct,
                "trend": prediction["trend"],
                "confidence": prediction["confidence"],
                "priority": item.priority,
                "flexible": item.flexible
            })
    
    deficit_categories = [c for c in categories_analysis if c["overspend_amount"] > 0]
    surplus_categories = [c for c in categories_analysis if c["overspend_amount"] < 0]
    
    # Prioritize: Deficits by severity (highest overspend), Surpluses by flexibility (lowest priority/highest flexibility)
    deficit_categories.sort(key=lambda x: x["overspend_pct"], reverse=True)
    surplus_categories.sort(key=lambda x: (x["priority"], -x["flexible"]), reverse=False) # Lower priority, higher flexibility first
    
    suggestions = []
    for deficit_cat in deficit_categories:
        needed = deficit_cat["overspend_amount"]
        
        for surplus_cat in surplus_categories:
            # Funds available to transfer: Based on unspent surplus * flexibility factor
            available = abs(surplus_cat["overspend_amount"]) * surplus_cat["flexible"]
            
            if available < needed * 0.05: continue # Must be a meaningful transfer
            
            # Transfer max 50% of the deficit needed from one source at a time
            transfer_amount = min(available, needed * 0.5) 
            
            suggestions.append({
                "from_category": surplus_cat["category"],
                "to_category": deficit_cat["category"],
                "amount": round(transfer_amount, 2),
                "reason": f"{deficit_cat['category']} needs funding ({deficit_cat['overspend_pct']:.1f}% over budget, {deficit_cat['trend']} trend).",
                "cost_cutting_tip": f"Reduce {surplus_cat['category']} expenditures by **{round(transfer_amount, 2)}** (estimated surplus funds are available and flexible)."
            })
            
            needed -= transfer_amount
            if needed <= 0: break
            
    return suggestions

def check_budget_alerts(session, project_id: str, category: str, current_amount: float) -> list:
    """Enhanced alerts with predictive warnings."""
    alerts = []
    planned = session.query(BudgetItem).filter_by(project_id=project_id, category=category).first()
    if not planned: return alerts
    
    total_spent = session.query(func.sum(Expense.amount)).filter_by(project_id=project_id, category=category).scalar() or 0
    utilization = (total_spent / planned.planned_amount * 100) if planned.planned_amount > 0 else 0
    
    if total_spent > planned.planned_amount:
        alerts.append({
            "type": "overspend", "severity": "critical",
            "message": f"⚠️ '{category}' has EXCEEDED budget by {total_spent - planned.planned_amount:.2f} ({utilization - 100:.1f}%)",
            "planned": planned.planned_amount, "spent": total_spent
        })
    elif utilization > 85:
        alerts.append({
            "type": "high_utilization", "severity": "warning",
            "message": f"⚠️ '{category}' is at {utilization:.1f}% utilization. Remaining: {planned.planned_amount - total_spent:.2f}",
            "planned": planned.planned_amount, "spent": total_spent
        })
    
    prediction = predict_category_spending(session, project_id, category, days_ahead=30)
    
    if prediction.get("predicted_total") is not None:
        predicted_end = total_spent + prediction["predicted_total"]
        if predicted_end > planned.planned_amount:
            overshoot = predicted_end - planned.planned_amount
            overshoot_pct = (overshoot / planned.planned_amount * 100)
            alerts.append({
                "type": "predictive_overspend", 
                "severity": "warning" if overshoot_pct < 20 else "critical",
                "message": f"🔮 '{category}' PREDICTED to exceed budget by {overshoot:.2f} ({overshoot_pct:.1f}%) - Trend: {prediction['trend']}",
                "confidence": prediction["confidence"]
            })
    
    return alerts

# --- FASTAPI ENDPOINTS ---

@app.post("/upload_budget_csv/")
async def upload_budget_csv(file: UploadFile = File(...), project_id: str = Form(...)):
    session = next(get_db_session())
    try:
        if not file.filename.endswith('.csv'): raise HTTPException(status_code=400, detail="File must be a CSV")
        
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        
        required_columns = {"Category", "Planned_Amount"}
        if not required_columns.issubset(df.columns):
            raise HTTPException(status_code=400, detail="CSV must have Category and Planned_Amount columns")
        
        # Clear existing budget items for the project
        session.query(BudgetItem).filter_by(project_id=project_id).delete()
        
        new_items = []
        for _, row in df.iterrows():
            item = BudgetItem(
                category=row["Category"].strip(),
                planned_amount=float(row["Planned_Amount"]),
                project_id=project_id,
                priority=float(row.get("Priority", 1.0)),
                flexible=float(row.get("Flexible", 0.15))
            )
            new_items.append(item)
        
        session.add_all(new_items)
        session.commit()
        
        return {"message": f"{len(new_items)} budget items uploaded for project {project_id}"}
        
    except Exception as e:
        session.rollback()
        logger.error(f"Budget CSV upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/upload_expense/")
async def upload_expense(
    project_id: str = Form(...),
    amount: float = Form(None),
    category: str = Form(None),
    receipt: UploadFile = File(None),
    description: str = Form(None),
    date: str = Form(None)
):
    session = next(get_db_session())
    try:
        expense_date = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.utcnow().date()
        
        extracted_amount = None
        receipt_text = ""
        
        if receipt and receipt.content_type and receipt.content_type.startswith('image/'):
            extracted_amount, receipt_text = extract_amount_and_text_from_receipt(receipt)
        
        final_amount = extracted_amount if extracted_amount is not None else amount
        
        if not final_amount or final_amount <= 0:
            raise HTTPException(status_code=400, detail="Valid amount is required.")
        
        available_categories = get_available_categories(session, project_id)
        
        final_category = category
        if not final_category:
            categorization_text = receipt_text if receipt_text else description
            final_category = categorize_expense_smart(categorization_text, available_categories) if categorization_text else "Misc"
        
        expense = Expense(project_id=project_id, amount=final_amount, category=final_category, date=expense_date)
        
        session.add(expense)
        session.commit()
        
        alerts = check_budget_alerts(session, project_id, final_category, final_amount)
        
        total_spent = session.query(func.sum(Expense.amount)).filter_by(project_id=project_id, category=final_category).scalar() or 0
        
        return {
            "message": "Expense added successfully", "category": final_category, "amount": final_amount,
            "total_spent_in_category": round(total_spent, 2), "alerts": alerts
        }
        
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Expense upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/project/{project_id}/summary")
async def get_project_summary(project_id: str):
    session = next(get_db_session())
    try:
        budget_items = session.query(BudgetItem).filter_by(project_id=project_id).all()
        expenses_by_category = session.query(
            Expense.category, func.sum(Expense.amount).label('total_spent')
        ).filter_by(project_id=project_id).group_by(Expense.category).all()
        
        summary = []
        for item in budget_items:
            spent = next((e.total_spent for e in expenses_by_category if e.category == item.category), 0.0)
            remaining = max(0, item.planned_amount - spent)
            
            summary.append({
                "category": item.category, "planned": item.planned_amount, "spent": spent,
                "remaining": remaining, "utilization_percentage": (spent / item.planned_amount * 100) if item.planned_amount > 0 else 0
            })
        
        total_planned = sum(item.planned_amount for item in budget_items)
        total_spent = sum(e.total_spent for e in expenses_by_category)
        
        return {
            "project_id": project_id, "summary": summary,
            "overall": {
                "total_planned": total_planned, "total_spent": total_spent,
                "total_remaining": max(0, total_planned - total_spent),
                "overall_utilization": (total_spent / total_planned * 100) if total_planned > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Project summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/project/{project_id}/predictions")
async def get_project_predictions(project_id: str, days_ahead: int = 30):
    session = next(get_db_session())
    try:
        budget_items = session.query(BudgetItem).filter_by(project_id=project_id).all()
        predictions = []
        for item in budget_items:
            total_spent = session.query(func.sum(Expense.amount)).filter_by(project_id=project_id, category=item.category).scalar() or 0
            prediction = predict_category_spending(session, project_id, item.category, days_ahead)
            
            status = "on_track"
            if prediction.get("predicted_total") and (total_spent + prediction["predicted_total"]) > item.planned_amount:
                status = "at_risk"
                
            predictions.append({
                "category": item.category, "current_spent": round(total_spent, 2), "planned_budget": item.planned_amount,
                "prediction": prediction, "status": status
            })
        
        return {"project_id": project_id, "forecast_days": days_ahead, "predictions": predictions}
        
    except Exception as e:
        logger.error(f"Predictions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/project/{project_id}/reallocation_suggestions")
async def get_reallocation_suggestions(project_id: str):
    """
    Returns smart budget reallocation suggestions and cost-cutting tips.
    """
    session = next(get_db_session())
    try:
        suggestions = calculate_reallocation_suggestions(session, project_id)
        
        if not suggestions:
            return {"project_id": project_id, "message": "No reallocation needed. Budget is balanced!", "suggestions": []}
        
        total_reallocated = sum(s["amount"] for s in suggestions)
        
        return {
            "project_id": project_id, "total_suggested_reallocation": round(total_reallocated, 2),
            "suggestion_count": len(suggestions), "suggestions": suggestions
        }
        
    except Exception as e:
        logger.error(f"Reallocation suggestions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/project/{project_id}/health_check")
async def project_health_check(project_id: str):
    session = next(get_db_session())
    try:
        budget_items = session.query(BudgetItem).filter_by(project_id=project_id).all()
        all_alerts = []
        health_score = 100
        
        for item in budget_items:
            alerts = check_budget_alerts(session, project_id, item.category, 0)
            all_alerts.extend(alerts)
            
            for alert in alerts:
                if alert["severity"] == "critical": health_score -= 15
                elif alert["severity"] == "warning": health_score -= 5
        
        health_score = max(0, health_score)
        status = "excellent" if health_score >= 85 else ("good" if health_score >= 70 else ("concerning" if health_score >= 50 else "critical"))
        
        return {
            "project_id": project_id, "health_score": health_score, "status": status,
            "total_alerts": len(all_alerts),
            "critical_alerts": len([a for a in all_alerts if a.get("severity") == "critical"]),
            "warnings": len([a for a in all_alerts if a.get("severity") == "warning"]),
            "alerts": all_alerts
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# --- NEW RENTAL ENDPOINTS ---

@app.post("/upload_rental_item/")
async def upload_rental_item(
    project_id: str = Form(...),
    description: str = Form(...),
    vendor: str = Form(...),
    rental_fee: float = Form(...),
    return_date: str = Form(...)
):
    session = next(get_db_session())
    try:
        r_date = datetime.strptime(return_date, "%Y-%m-%d").date()
        rental = RentalItem(
            project_id=project_id,
            description=description,
            vendor=vendor,
            rental_fee=rental_fee,
            return_date=r_date
        )
        session.add(rental)
        session.commit()
        return {"message": "Rental item tracked successfully", "rental_id": rental.id}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add rental: {str(e)}")
    finally:
        session.close()

@app.post("/mark_rental_returned/")
async def mark_rental_returned(rental_id: str = Form(...)):
    session = next(get_db_session())
    try:
        rental = session.query(RentalItem).filter_by(id=rental_id).first()
        if not rental:
            raise HTTPException(status_code=404, detail="Rental item not found.")
        
        if rental.returned_on is not None:
            return {"message": "Rental already marked as returned."}
        
        rental.returned_on = datetime.utcnow().date()
        session.commit()
        return {"message": f"Rental item '{rental.description}' marked as returned on {rental.returned_on.isoformat()}"}
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to mark rental as returned: {str(e)}")
    finally:
        session.close()

@app.get("/project/{project_id}/rental_check")
async def get_rental_status(project_id: str):
    """
    Checks the status of all equipment rentals to ensure proper, timely return.
    """
    session = next(get_db_session())
    today = datetime.utcnow().date()
    
    try:
        rentals = session.query(RentalItem).filter_by(project_id=project_id).order_by(RentalItem.return_date).all()
        
        status_list = []
        
        for rental in rentals:
            is_overdue = rental.return_date < today and rental.returned_on is None
            is_due_soon = rental.return_date >= today and (rental.return_date - today).days <= 3 and rental.returned_on is None
            
            status = "Returned"
            severity = "info"
            if is_overdue:
                status = "CRITICAL: OVERDUE"
                severity = "critical"
            elif is_due_soon:
                status = "WARNING: DUE SOON"
                severity = "warning"
            elif rental.returned_on is None:
                status = "Active"
                severity = "info"
                
            status_list.append({
                "rental_id": rental.id,
                "description": rental.description,
                "vendor": rental.vendor,
                "return_date": rental.return_date.isoformat(),
                "status": status,
                "severity": severity,
                "days_until_due": (rental.return_date - today).days if rental.returned_on is None else 0
            })
            
        return {
            "project_id": project_id,
            "rental_status": status_list,
            "overdue_count": len([s for s in status_list if s['severity'] == 'critical'])
        }
    except Exception as e:
        logger.error(f"Rental check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# --- NEW TIMELINE ENDPOINT ---

@app.get("/project/{project_id}/timeline_comparison")
async def get_timeline_comparison(project_id: str):
    """
    Compares preplanned expenditure (BudgetTimeline) against current expenditure (Expense) 
    across the entire film production timeline.
    """
    session = next(get_db_session())
    
    try:
        # 1. Aggregate Planned Daily Spend
        planned_spend = session.query(
            BudgetTimeline.target_date,
            func.sum(BudgetTimeline.planned_daily_spend).label('planned')
        ).filter_by(project_id=project_id).group_by(BudgetTimeline.target_date).order_by(BudgetTimeline.target_date).all()
        
        # 2. Aggregate Actual Daily Spend
        actual_spend = session.query(
            Expense.date,
            func.sum(Expense.amount).label('actual')
        ).filter_by(project_id=project_id).group_by(Expense.date).order_by(Expense.date).all()
        
        # 3. Merge data for comparison
        timeline_data: Dict[str, Dict] = {}
        for date, planned in planned_spend:
            timeline_data[date.isoformat()] = {"planned": planned, "actual": 0.0, "diff": planned * -1}
            
        for date, actual in actual_spend:
            date_str = date.isoformat()
            if date_str not in timeline_data:
                # Actual expense on a day with no explicitly planned spend, treat planned as 0
                timeline_data[date_str] = {"planned": 0.0, "actual": 0.0, "diff": 0.0}
                
            timeline_data[date_str]['actual'] = actual
            timeline_data[date_str]['diff'] = actual - timeline_data[date_str]['planned']
        
        # 4. Format output and calculate cumulative data
        final_comparison = []
        cumulative_planned = 0.0
        cumulative_actual = 0.0
        
        sorted_dates = sorted(timeline_data.keys())
        
        for date_str in sorted_dates:
            data = timeline_data[date_str]
            cumulative_planned += data['planned']
            cumulative_actual += data['actual']
            
            final_comparison.append({
                "date": date_str,
                "planned_daily": round(data['planned'], 2),
                "actual_daily": round(data['actual'], 2),
                "daily_difference": round(data['diff'], 2), # Positive means overspent that day
                "cumulative_planned": round(cumulative_planned, 2),
                "cumulative_actual": round(cumulative_actual, 2),
                "cumulative_difference": round(cumulative_actual - cumulative_planned, 2) # Positive means over budget
            })

        current_status = "Over Budget" if cumulative_actual > cumulative_planned else "Under Budget"
        
        return {
            "project_id": project_id,
            "comparison_by_date": final_comparison,
            "total_production_days_tracked": len(final_comparison),
            "cumulative_total_difference": round(cumulative_actual - cumulative_planned, 2),
            "current_status": current_status
        }
        
    except Exception as e:
        logger.error(f"Timeline comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# Example endpoint for uploading timeline data (can be refined via CSV upload like the budget)
@app.post("/upload_timeline_data/")
async def upload_timeline_data(
    project_id: str = Form(...),
    category: str = Form(...),
    planned_daily_spend: float = Form(...),
    target_date: str = Form(...)
):
    session = next(get_db_session())
    try:
        t_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        timeline_item = BudgetTimeline(
            project_id=project_id,
            category=category,
            planned_daily_spend=planned_daily_spend,
            target_date=t_date
        )
        session.add(timeline_item)
        session.commit()
        return {"message": "Timeline item added successfully"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add timeline item: {str(e)}")
    finally:
        session.close()