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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = ""

Base = declarative_base()
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine)

class BudgetItem(Base):
    __tablename__ = "budget_items"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String, index=True)
    planned_amount = Column(Float)
    project_id = Column(String, index=True)
    created_at = Column(Date, default=datetime.utcnow)
    priority = Column(Float, default=1.0)  # New: Priority for reallocation
    flexible = Column(Float, default=0.15)  # New: How flexible this budget is (0-1)

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String, index=True)
    amount = Column(Float)
    date = Column(Date)
    project_id = Column(String, index=True)
    receipt_path = Column(String, nullable=True)
    created_at = Column(Date, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Film Budget Tracker with Dynamic Prediction")

def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

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
        receipt_text = pytesseract.image_to_string(img, config='--oem 3 --psm 6')
        
        configs = [
            '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.,$€£₹ ',
            '--oem 3 --psm 4 -c tessedit_char_whitelist=0123456789.,$€£₹ ',
            '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789.,$€£₹ ',
        ]
        
        all_text = []
        for config in configs:
            try:
                text = pytesseract.image_to_string(img, config=config)
                all_text.append(text)
            except Exception:
                continue
        
        combined_text = "\n".join(all_text)
        
        patterns = [
            r'(?:total\s*\(usd\)|total|grand total|final total)[:\s]*[₹$€£]?\s*([\d,]+\.?\d{0,2})',
            r'(?:total\s*\(usd\)|total|grand total|final total)\s*[₹$€£]?\s*([\d,]+\.?\d{0,2})',
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
        
        if not amounts:
            all_numbers = re.findall(r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b', combined_text)
            for num in all_numbers:
                try:
                    amt = float(num.replace(',', ''))
                    if 1.00 <= amt <= 1000000:
                        amounts.append(amt)
                except:
                    continue
        
        final_amount = max(amounts) if amounts else None
        return final_amount, receipt_text
        
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return None, ""

def categorize_expense_smart(text: str, available_categories: list) -> str:
    if not text:
        return "Misc"
    
    text_lower = text.lower()
    
    category_patterns = {
        "Food": [
            r'\bfood\b', r'\bcatering\b', r'\bmeal\b', r'\blunch\b', r'\bdinner\b', r'\bbreakfast\b',
            r'\bsnack\b', r'\brefreshment\b', r'\bcraft service\b', r'\bsandwich\b', r'\bsalad\b',
            r'\bdrink\b', r'\bbeverage\b', r'\bcoffee\b', r'\btea\b', r'\bsoda\b', r'\bcake\b',
            r'\bchicken\b', r'\bgrilled\b', r'\bcaesar\b', r'\bchocolate\b', r'\brestaurant\b',
            r'\bcafe\b', r'\bbakery\b', r'\bdeli\b', r'\beat\b', r'\bdining\b', r'\bmenu\b',
            r'\bfood truck\b', r'\bpizza\b', r'\bburger\b', r'\bfries\b'
        ],
        "Actors": [r'\bactor\b', r'\btalent\b', r'\bcast\b', r'\bstunt\b', r'\bextra\b', r'\bprincipal\b', r'\bperformer\b'],
        "Props": [r'\bprop\b', r'\bfurniture\b', r'\bset dressing\b', r'\bhand prop\b', r'\bweapon\b', r'\bdecor\b'],
        "Locations": [r'\blocation\b', r'\bvenue\b', r'\bsite\b', r'\bpermits\b', r'\blocation fee\b', r'\brental\b'],
        "Equipment": [r'\bequipment\b', r'\bcamera\b', r'\blight\b', r'\bsound\b', r'\bgrip\b', r'\blens\b', r'\btripod\b'],
        "VFX": [r'\bvfx\b', r'\bvisual effects\b', r'\bcg\b', r'\bcompositing\b', r'\b3d\b', r'\banimation\b'],
        "Costumes": [r'\bcostume\b', r'\bwardrobe\b', r'\boutfit\b', r'\bdress\b', r'\battire\b', r'\bfabric\b'],
        "Transportation": [r'\btransport\b', r'\bvehicle\b', r'\btruck\b', r'\bfuel\b', r'\bparking\b', r'\bgas\b'],
        "Post Production": [r'\bedit\b', r'\bcolor\b', r'\bsound mix\b', r'\bmusic\b', r'\bscore\b', r'\baudio\b'],
    }
    
    category_scores = {}
    
    for category, patterns_list in category_patterns.items():
        if category not in available_categories:
            continue
            
        score = 0
        for pattern in patterns_list:
            matches = re.findall(pattern, text_lower)
            score += len(matches) * 2
        
        if score > 0:
            category_scores[category] = score
    
    if "food receipt" in text_lower:
        category_scores["Food"] = category_scores.get("Food", 0) + 10
    
    if "grilled chicken" in text_lower or "caesar salad" in text_lower:
        category_scores["Food"] = category_scores.get("Food", 0) + 8
    
    if category_scores:
        best_category = max(category_scores.items(), key=lambda x: x[1])[0]
        return best_category
    
    return "Misc"

def get_available_categories(session, project_id: str) -> list:
    categories = session.query(BudgetItem.category).filter_by(project_id=project_id).distinct().all()
    return [cat[0] for cat in categories] if categories else ["Misc"]

def predict_category_spending(session, project_id: str, category: str, days_ahead: int = 30) -> dict:
    """
    Enhanced Prophet prediction with trend analysis and confidence intervals
    """
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
        
        # Enhanced Prophet with better parameters
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=False,
            changepoint_prior_scale=0.05,
            interval_width=0.80,  # 80% confidence interval
            seasonality_mode='multiplicative'
        )
        
        model.fit(df_exp)
        
        # Predict future
        future_dates = model.make_future_dataframe(periods=days_ahead)
        forecast = model.predict(future_dates)
        
        # Calculate predictions
        future_predictions = forecast[forecast['ds'] > max(df_exp['ds'])]
        predicted_future_spend = future_predictions['yhat'].sum()
        
        # Calculate trend
        recent_actual = df_exp.tail(5)['y'].mean()
        future_avg = future_predictions['yhat'].mean()
        trend_pct = ((future_avg - recent_actual) / recent_actual * 100) if recent_actual > 0 else 0
        
        if trend_pct > 20:
            trend = "accelerating"
        elif trend_pct > 5:
            trend = "increasing"
        elif trend_pct < -5:
            trend = "decreasing"
        else:
            trend = "stable"
        
        # Confidence based on variance
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
        return {
            "predicted_total": None,
            "daily_average": None,
            "trend": "error",
            "confidence": "low",
            "error": str(e)
        }

def calculate_reallocation_suggestions(session, project_id: str) -> list:
    """
    Smart budget reallocation based on predictions and priorities
    """
    budget_items = session.query(BudgetItem).filter_by(project_id=project_id).all()
    
    if len(budget_items) < 2:
        return []
    
    suggestions = []
    categories_analysis = []
    
    # Analyze each category
    for item in budget_items:
        total_spent = session.query(func.sum(Expense.amount)).filter_by(
            project_id=project_id, 
            category=item.category
        ).scalar() or 0
        
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
    
    # Find categories that need help
    deficit_categories = [c for c in categories_analysis if c["overspend_amount"] > 0]
    surplus_categories = [c for c in categories_analysis if c["overspend_amount"] < 0]
    
    # Sort by severity
    deficit_categories.sort(key=lambda x: x["overspend_pct"], reverse=True)
    surplus_categories.sort(key=lambda x: abs(x["overspend_amount"]), reverse=True)
    
    # Generate reallocation suggestions
    for deficit_cat in deficit_categories[:3]:  # Top 3 problem categories
        needed = deficit_cat["overspend_amount"]
        
        for surplus_cat in surplus_categories:
            available = abs(surplus_cat["overspend_amount"]) * surplus_cat["flexible"]
            
            if available < needed * 0.05:  # Must be at least 5% of needed
                continue
            
            transfer_amount = min(available, needed * 0.5)  # Max 50% at a time
            transfer_pct = (transfer_amount / surplus_cat["planned"]) * 100
            
            suggestion = {
                "from_category": surplus_cat["category"],
                "to_category": deficit_cat["category"],
                "amount": round(transfer_amount, 2),
                "percentage": round(transfer_pct, 2),
                "reason": f"{deficit_cat['category']} overspending +{deficit_cat['overspend_pct']:.1f}% ({deficit_cat['trend']} trend)",
                "impact": f"Reduces {deficit_cat['category']} deficit by {(transfer_amount/needed*100):.1f}%",
                "confidence": deficit_cat["confidence"],
                "priority": "high" if deficit_cat["overspend_pct"] > 20 else "medium"
            }
            
            suggestions.append(suggestion)
            
            needed -= transfer_amount
            if needed <= 0:
                break
    
    return suggestions

def check_budget_alerts(session, project_id: str, category: str, current_amount: float) -> list:
    """
    Enhanced alerts with predictive warnings
    """
    alerts = []
    planned = session.query(BudgetItem).filter_by(project_id=project_id, category=category).first()
    
    if not planned:
        return alerts
    
    total_spent = session.query(func.sum(Expense.amount)).filter_by(
        project_id=project_id, category=category
    ).scalar() or 0
    
    utilization = (total_spent / planned.planned_amount * 100) if planned.planned_amount > 0 else 0
    
    # Current overspend alert
    if total_spent > planned.planned_amount:
        alerts.append({
            "type": "overspend",
            "severity": "critical",
            "message": f"⚠️ '{category}' has EXCEEDED budget by {total_spent - planned.planned_amount:.2f} ({utilization - 100:.1f}%)",
            "planned": planned.planned_amount,
            "spent": total_spent
        })
    
    # High utilization warning
    elif utilization > 85:
        alerts.append({
            "type": "high_utilization",
            "severity": "warning",
            "message": f"⚠️ '{category}' is at {utilization:.1f}% utilization. Remaining: {planned.planned_amount - total_spent:.2f}",
            "planned": planned.planned_amount,
            "spent": total_spent
        })
    
    # Predictive alert
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
                "planned": planned.planned_amount,
                "predicted_total": predicted_end,
                "confidence": prediction["confidence"],
                "trend": prediction["trend"]
            })
    
    return alerts

@app.post("/upload_budget_csv/")
async def upload_budget_csv(file: UploadFile = File(...), project_id: str = Form(...)):
    session = next(get_db_session())
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        
        required_columns = {"Category", "Planned_Amount"}
        if not required_columns.issubset(df.columns):
            raise HTTPException(
                status_code=400, 
                detail="CSV must have Category and Planned_Amount columns"
            )
        
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
        
        return {
            "message": f"{len(new_items)} budget items uploaded for project {project_id}",
            "categories": [item.category for item in new_items]
        }
        
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
            raise HTTPException(
                status_code=400, 
                detail="Valid amount is required. Could not extract from receipt or form data."
            )
        
        available_categories = get_available_categories(session, project_id)
        
        final_category = category
        if not final_category:
            categorization_text = receipt_text if receipt_text else description
            if categorization_text:
                final_category = categorize_expense_smart(categorization_text, available_categories)
            else:
                final_category = "Misc"
        
        expense = Expense(
            project_id=project_id,
            amount=final_amount,
            category=final_category,
            date=expense_date
        )
        
        session.add(expense)
        session.commit()
        
        alerts = check_budget_alerts(session, project_id, final_category, final_amount)
        
        total_spent = session.query(func.sum(Expense.amount)).filter_by(
            project_id=project_id, category=final_category
        ).scalar() or 0
        
        return {
            "message": "Expense added successfully",
            "expense_id": expense.id,
            "category": final_category,
            "amount": final_amount,
            "date": expense_date.isoformat(),
            "total_spent_in_category": round(total_spent, 2),
            "alerts": alerts,
            "amount_source": "ocr" if extracted_amount else "form"
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
            Expense.category,
            func.sum(Expense.amount).label('total_spent')
        ).filter_by(project_id=project_id).group_by(Expense.category).all()
        
        summary = []
        for item in budget_items:
            spent = next(
                (expense.total_spent for expense in expenses_by_category 
                 if expense.category == item.category), 
                0.0
            )
            remaining = max(0, item.planned_amount - spent)
            
            summary.append({
                "category": item.category,
                "planned": item.planned_amount,
                "spent": spent,
                "remaining": remaining,
                "utilization_percentage": (spent / item.planned_amount * 100) if item.planned_amount > 0 else 0
            })
        
        total_planned = sum(item.planned_amount for item in budget_items)
        total_spent = sum(expense.total_spent for expense in expenses_by_category)
        total_remaining = max(0, total_planned - total_spent)
        
        return {
            "project_id": project_id,
            "summary": summary,
            "overall": {
                "total_planned": total_planned,
                "total_spent": total_spent,
                "total_remaining": total_remaining,
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
    """
    NEW ENDPOINT: Get spending predictions for all categories
    """
    session = next(get_db_session())
    try:
        budget_items = session.query(BudgetItem).filter_by(project_id=project_id).all()
        
        predictions = []
        for item in budget_items:
            total_spent = session.query(func.sum(Expense.amount)).filter_by(
                project_id=project_id, 
                category=item.category
            ).scalar() or 0
            
            prediction = predict_category_spending(session, project_id, item.category, days_ahead)
            
            predictions.append({
                "category": item.category,
                "current_spent": round(total_spent, 2),
                "planned_budget": item.planned_amount,
                "prediction": prediction,
                "status": "on_track" if prediction.get("predicted_total") and 
                         (total_spent + prediction["predicted_total"]) <= item.planned_amount 
                         else "at_risk"
            })
        
        return {
            "project_id": project_id,
            "forecast_days": days_ahead,
            "predictions": predictions
        }
        
    except Exception as e:
        logger.error(f"Predictions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/project/{project_id}/reallocation_suggestions")
async def get_reallocation_suggestions(project_id: str):
    """
    NEW ENDPOINT: Get smart budget reallocation suggestions
    """
    session = next(get_db_session())
    try:
        suggestions = calculate_reallocation_suggestions(session, project_id)
        
        if not suggestions:
            return {
                "project_id": project_id,
                "message": "No reallocation needed. Budget is balanced!",
                "suggestions": []
            }
        
        # Calculate total impact
        total_reallocated = sum(s["amount"] for s in suggestions)
        
        return {
            "project_id": project_id,
            "total_suggested_reallocation": round(total_reallocated, 2),
            "suggestion_count": len(suggestions),
            "suggestions": suggestions
        }
        
    except Exception as e:
        logger.error(f"Reallocation suggestions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/project/{project_id}/health_check")
async def project_health_check(project_id: str):
    """
    NEW ENDPOINT: Comprehensive project budget health check
    """
    session = next(get_db_session())
    try:
        budget_items = session.query(BudgetItem).filter_by(project_id=project_id).all()
        
        all_alerts = []
        health_score = 100
        
        for item in budget_items:
            total_spent = session.query(func.sum(Expense.amount)).filter_by(
                project_id=project_id, 
                category=item.category
            ).scalar() or 0
            
            alerts = check_budget_alerts(session, project_id, item.category, 0)
            all_alerts.extend(alerts)
            
            # Deduct health score for problems
            for alert in alerts:
                if alert["severity"] == "critical":
                    health_score -= 15
                elif alert["severity"] == "warning":
                    health_score -= 5
        
        health_score = max(0, health_score)
        
        if health_score >= 85:
            status = "excellent"
        elif health_score >= 70:
            status = "good"
        elif health_score >= 50:
            status = "concerning"
        else:
            status = "critical"
        
        return {
            "project_id": project_id,
            "health_score": health_score,
            "status": status,
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