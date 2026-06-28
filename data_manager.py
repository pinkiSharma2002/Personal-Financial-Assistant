"""
CSV-based Finance Data Manager
All income/expense records stored in data/transactions.csv
Multiple users' data in one file, filtered by user_id.
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime, date
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
TRANSACTIONS_FILE = DATA_DIR / "transactions.csv"
BUDGETS_FILE = DATA_DIR / "budgets.csv"

COLUMNS = [
    "id", "user_id", "date", "type", "category",
    "amount", "description", "month", "year"
]

BUDGET_COLUMNS = ["user_id", "category", "month", "year", "budget_amount"]

INCOME_CATEGORIES = [
    "Salary", "Freelance", "Business", "Investment",
    "Rental Income", "Bonus", "Other Income"
]

EXPENSE_CATEGORIES = [
    "Home/Rent", "Food & Groceries", "Transport/Car",
    "Utilities", "Healthcare", "Education", "Entertainment",
    "Shopping", "Insurance", "EMI/Loan", "Savings/Investment",
    "Travel", "Other Expense"
]


def _ensure_files():
    DATA_DIR.mkdir(exist_ok=True)
    if not TRANSACTIONS_FILE.exists():
        pd.DataFrame(columns=COLUMNS).to_csv(TRANSACTIONS_FILE, index=False)
    if not BUDGETS_FILE.exists():
        pd.DataFrame(columns=BUDGET_COLUMNS).to_csv(BUDGETS_FILE, index=False)


def load_transactions(user_id: int) -> pd.DataFrame:
    _ensure_files()
    df = pd.read_csv(TRANSACTIONS_FILE)
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    df = df[df["user_id"] == user_id].copy()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    return df


def add_transaction(user_id: int, txn_date: date, txn_type: str,
                    category: str, amount: float, description: str) -> bool:
    _ensure_files()
    df = pd.read_csv(TRANSACTIONS_FILE)
    new_id = int(df["id"].max() + 1) if not df.empty and not pd.isna(df["id"].max()) else 1
    new_row = {
        "id": new_id,
        "user_id": user_id,
        "date": txn_date.strftime("%Y-%m-%d"),
        "type": txn_type,
        "category": category,
        "amount": round(amount, 2),
        "description": description,
        "month": txn_date.month,
        "year": txn_date.year,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(TRANSACTIONS_FILE, index=False)
    return True


def delete_transaction(user_id: int, txn_id: int) -> bool:
    _ensure_files()
    df = pd.read_csv(TRANSACTIONS_FILE)
    original_len = len(df)
    df = df[~((df["user_id"] == user_id) & (df["id"] == txn_id))]
    if len(df) < original_len:
        df.to_csv(TRANSACTIONS_FILE, index=False)
        return True
    return False


def get_monthly_summary(user_id: int, year: int, month: int) -> dict:
    df = load_transactions(user_id)
    if df.empty:
        return {"income": 0, "expense": 0, "balance": 0, "savings_rate": 0}
    m_df = df[(df["year"] == year) & (df["month"] == month)]
    income = m_df[m_df["type"] == "Income"]["amount"].sum()
    expense = m_df[m_df["type"] == "Expense"]["amount"].sum()
    balance = income - expense
    savings_rate = (balance / income * 100) if income > 0 else 0
    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "balance": round(balance, 2),
        "savings_rate": round(savings_rate, 1),
    }


def get_yearly_summary(user_id: int, year: int) -> dict:
    df = load_transactions(user_id)
    if df.empty:
        return {"income": 0, "expense": 0, "balance": 0}
    y_df = df[df["year"] == year]
    income = y_df[y_df["type"] == "Income"]["amount"].sum()
    expense = y_df[y_df["type"] == "Expense"]["amount"].sum()
    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "balance": round(income - expense, 2),
    }


def get_category_breakdown(user_id: int, year: int, month: int = None,
                           txn_type: str = "Expense") -> pd.DataFrame:
    df = load_transactions(user_id)
    if df.empty:
        return pd.DataFrame()
    filtered = df[df["year"] == year]
    if month:
        filtered = filtered[filtered["month"] == month]
    filtered = filtered[filtered["type"] == txn_type]
    if filtered.empty:
        return pd.DataFrame()
    return filtered.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)


def get_monthly_trend(user_id: int, year: int) -> pd.DataFrame:
    df = load_transactions(user_id)
    if df.empty:
        return pd.DataFrame()
    y_df = df[df["year"] == year]
    result = []
    for m in range(1, 13):
        m_df = y_df[y_df["month"] == m]
        result.append({
            "month": m,
            "month_name": datetime(year, m, 1).strftime("%b"),
            "income": m_df[m_df["type"] == "Income"]["amount"].sum(),
            "expense": m_df[m_df["type"] == "Expense"]["amount"].sum(),
        })
    trend_df = pd.DataFrame(result)
    trend_df["balance"] = trend_df["income"] - trend_df["expense"]
    return trend_df


# ── BUDGET MANAGEMENT ────────────────────────────────────────────────────────

def save_budget(user_id: int, category: str, month: int, year: int, amount: float):
    _ensure_files()
    df = pd.read_csv(BUDGETS_FILE)
    mask = (
        (df["user_id"] == user_id) &
        (df["category"] == category) &
        (df["month"] == month) &
        (df["year"] == year)
    )
    if mask.any():
        df.loc[mask, "budget_amount"] = amount
    else:
        df = pd.concat([df, pd.DataFrame([{
            "user_id": user_id, "category": category,
            "month": month, "year": year, "budget_amount": amount
        }])], ignore_index=True)
    df.to_csv(BUDGETS_FILE, index=False)


def get_budgets(user_id: int, month: int, year: int) -> pd.DataFrame:
    _ensure_files()
    df = pd.read_csv(BUDGETS_FILE)
    if df.empty:
        return pd.DataFrame(columns=BUDGET_COLUMNS)
    return df[(df["user_id"] == user_id) & (df["month"] == month) & (df["year"] == year)]