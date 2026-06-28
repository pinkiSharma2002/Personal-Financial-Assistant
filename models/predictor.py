"""
ML Prediction Module
- Next month expense prediction (Linear Regression + trend)
- Savings goal calculator
- Budget recommendations
"""
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import warnings
warnings.filterwarnings("ignore")


def predict_next_month_expense(df: pd.DataFrame) -> dict:
    """
    Predict next month's expenses using Linear Regression on historical data.
    Returns prediction dict with confidence interval.
    """
    if df.empty:
        return {"predicted": 0, "confidence": "low", "trend": "neutral", "message": "Not enough data"}

    expense_df = df[df["type"] == "Expense"].copy()
    if expense_df.empty:
        return {"predicted": 0, "confidence": "low", "trend": "neutral", "message": "No expense data"}

    monthly = expense_df.groupby(["year", "month"])["amount"].sum().reset_index()
    monthly = monthly.sort_values(["year", "month"]).reset_index(drop=True)
    monthly["time_idx"] = range(len(monthly))

    if len(monthly) < 2:
        avg = monthly["amount"].mean()
        return {
            "predicted": round(avg, 2),
            "confidence": "low",
            "trend": "neutral",
            "message": "Based on limited data (1 month). Add more records for better predictions.",
        }

    X = monthly[["time_idx"]].values
    y = monthly["amount"].values

    # Use polynomial features for better fit if enough data
    if len(monthly) >= 4:
        poly = PolynomialFeatures(degree=2)
        X_poly = poly.fit_transform(X)
        model = LinearRegression()
        model.fit(X_poly, y)
        next_idx = np.array([[len(monthly)]])
        prediction = model.predict(poly.transform(next_idx))[0]
    else:
        model = LinearRegression()
        model.fit(X, y)
        prediction = model.predict([[len(monthly)]])[0]

    prediction = max(0, prediction)

    # Trend detection
    recent_avg = monthly["amount"].tail(3).mean()
    earlier_avg = monthly["amount"].head(max(1, len(monthly) - 3)).mean()
    if recent_avg > earlier_avg * 1.1:
        trend = "increasing"
    elif recent_avg < earlier_avg * 0.9:
        trend = "decreasing"
    else:
        trend = "stable"

    # Confidence based on data points
    confidence = "high" if len(monthly) >= 6 else ("medium" if len(monthly) >= 3 else "low")

    # Std deviation for range
    std = monthly["amount"].std()
    return {
        "predicted": round(prediction, 2),
        "lower_bound": round(max(0, prediction - std), 2),
        "upper_bound": round(prediction + std, 2),
        "confidence": confidence,
        "trend": trend,
        "months_of_data": len(monthly),
        "message": f"Prediction based on {len(monthly)} months of data.",
    }


def predict_next_month_income(df: pd.DataFrame) -> dict:
    """Predict next month income."""
    if df.empty:
        return {"predicted": 0}
    income_df = df[df["type"] == "Income"].copy()
    if income_df.empty:
        return {"predicted": 0}
    monthly = income_df.groupby(["year", "month"])["amount"].sum().reset_index()
    avg = monthly["amount"].mean()
    return {"predicted": round(avg, 2)}


def savings_goal_calculator(
    current_monthly_income: float,
    current_monthly_expense: float,
    goals: list[dict],
) -> dict:
    """
    Calculate how much to save and how long to reach goals.
    goals: [{"name": "Car", "amount": 500000, "months": 24}, ...]
    """
    current_savings = max(0, current_monthly_income - current_monthly_expense)
    savings_rate = (current_savings / current_monthly_income * 100) if current_monthly_income > 0 else 0

    results = []
    total_monthly_needed = 0

    for goal in goals:
        monthly_needed = goal["amount"] / goal["months"] if goal["months"] > 0 else goal["amount"]
        total_monthly_needed += monthly_needed
        shortfall = max(0, monthly_needed - current_savings)
        achievable = current_savings >= monthly_needed

        results.append({
            "name": goal["name"],
            "target": goal["amount"],
            "months": goal["months"],
            "monthly_needed": round(monthly_needed, 2),
            "achievable": achievable,
            "shortfall": round(shortfall, 2),
            "expense_cut_needed": round(shortfall, 2) if not achievable else 0,
        })

    recommended_expense = max(0, current_monthly_income - total_monthly_needed)

    return {
        "current_monthly_income": round(current_monthly_income, 2),
        "current_monthly_expense": round(current_monthly_expense, 2),
        "current_savings": round(current_savings, 2),
        "savings_rate": round(savings_rate, 1),
        "total_monthly_savings_needed": round(total_monthly_needed, 2),
        "recommended_max_expense": round(recommended_expense, 2),
        "goals": results,
    }


def get_category_predictions(df: pd.DataFrame) -> pd.DataFrame:
    """Predict next month expense per category."""
    if df.empty:
        return pd.DataFrame()
    expense_df = df[df["type"] == "Expense"]
    if expense_df.empty:
        return pd.DataFrame()

    cats = expense_df["category"].unique()
    results = []
    for cat in cats:
        cat_df = expense_df[expense_df["category"] == cat]
        monthly = cat_df.groupby(["year", "month"])["amount"].sum().reset_index()
        if len(monthly) >= 2:
            monthly["time_idx"] = range(len(monthly))
            model = LinearRegression()
            model.fit(monthly[["time_idx"]], monthly["amount"])
            pred = max(0, model.predict([[len(monthly)]])[0])
        else:
            pred = monthly["amount"].mean()
        results.append({"category": cat, "predicted_amount": round(pred, 2)})

    return pd.DataFrame(results).sort_values("predicted_amount", ascending=False)


def anomaly_detection(df: pd.DataFrame) -> pd.DataFrame:
    """Flag unusually high expense transactions (>2 std from category mean)."""
    if df.empty:
        return pd.DataFrame()
    expense_df = df[df["type"] == "Expense"].copy()
    if expense_df.empty:
        return pd.DataFrame()

    anomalies = []
    for cat in expense_df["category"].unique():
        cat_data = expense_df[expense_df["category"] == cat]["amount"]
        if len(cat_data) < 3:
            continue
        mean, std = cat_data.mean(), cat_data.std()
        outliers = expense_df[
            (expense_df["category"] == cat) &
            (expense_df["amount"] > mean + 2 * std)
        ]
        anomalies.append(outliers)

    if not anomalies:
        return pd.DataFrame()
    return pd.concat(anomalies).sort_values("amount", ascending=False).head(10)