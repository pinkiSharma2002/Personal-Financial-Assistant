"""
Charts & Visualization Module
Uses Matplotlib, Seaborn, Plotly
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime

# ─── Color Palette ────────────────────────────────────────────────────────────
INCOME_COLOR  = "#16a34a"
EXPENSE_COLOR = "#dc2626"
BALANCE_COLOR = "#2563eb"
ACCENT_COLORS = ["#6366f1","#f59e0b","#10b981","#ef4444","#8b5cf6",
                 "#ec4899","#14b8a6","#f97316","#84cc16","#06b6d4",
                 "#a855f7","#64748b","#d97706"]

sns.set_theme(style="whitegrid", palette="muted")


def monthly_trend_chart(trend_df: pd.DataFrame) -> go.Figure:
    """Plotly interactive bar+line chart for monthly income/expense."""
    if trend_df.empty:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=trend_df["month_name"], y=trend_df["income"],
        name="Income", marker_color=INCOME_COLOR, opacity=0.85,
    ))
    fig.add_trace(go.Bar(
        x=trend_df["month_name"], y=trend_df["expense"],
        name="Expense", marker_color=EXPENSE_COLOR, opacity=0.85,
    ))
    fig.add_trace(go.Scatter(
        x=trend_df["month_name"], y=trend_df["balance"],
        name="Net Balance", mode="lines+markers",
        line=dict(color=BALANCE_COLOR, width=2.5),
        marker=dict(size=7),
    ))
    fig.update_layout(
        barmode="group",
        title="Monthly Income vs Expense",
        xaxis_title="Month",
        yaxis_title="Amount (₹)",
        legend=dict(orientation="h", y=1.1),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="white",
        height=400,
        margin=dict(t=50, b=40),
    )
    return fig


def expense_pie_chart(breakdown_df: pd.DataFrame, title: str = "Expense Breakdown") -> go.Figure:
    """Donut chart for category breakdown."""
    if breakdown_df.empty:
        return go.Figure()
    fig = go.Figure(go.Pie(
        labels=breakdown_df["category"],
        values=breakdown_df["amount"],
        hole=0.45,
        marker=dict(colors=ACCENT_COLORS[:len(breakdown_df)]),
        textinfo="label+percent",
        hovertemplate="%{label}<br>₹%{value:,.2f}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        height=400,
        margin=dict(t=50, b=30),
        showlegend=True,
        legend=dict(orientation="v", x=1.05),
    )
    return fig


def income_expense_area_chart(trend_df: pd.DataFrame) -> go.Figure:
    """Area chart showing cumulative savings."""
    if trend_df.empty:
        return go.Figure()
    trend_df = trend_df.copy()
    trend_df["cumulative_balance"] = trend_df["balance"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend_df["month_name"], y=trend_df["income"],
        fill="tozeroy", name="Income", line=dict(color=INCOME_COLOR),
        fillcolor="rgba(22,163,74,0.15)",
    ))
    fig.add_trace(go.Scatter(
        x=trend_df["month_name"], y=trend_df["expense"],
        fill="tozeroy", name="Expense", line=dict(color=EXPENSE_COLOR),
        fillcolor="rgba(220,38,38,0.15)",
    ))
    fig.update_layout(
        title="Income vs Expense (Area)",
        xaxis_title="Month", yaxis_title="Amount (₹)",
        height=350, plot_bgcolor="#f8fafc", paper_bgcolor="white",
        legend=dict(orientation="h", y=1.1),
    )
    return fig


def savings_gauge(savings_rate: float) -> go.Figure:
    """Gauge chart for savings rate."""
    color = INCOME_COLOR if savings_rate >= 20 else ("#f59e0b" if savings_rate >= 10 else EXPENSE_COLOR)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=savings_rate,
        title={"text": "Savings Rate %"},
        delta={"reference": 20, "valueformat": ".1f"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 10], "color": "#fee2e2"},
                {"range": [10, 20], "color": "#fef3c7"},
                {"range": [20, 100], "color": "#dcfce7"},
            ],
            "threshold": {"line": {"color": "red", "width": 3}, "value": 20},
        },
        number={"suffix": "%", "valueformat": ".1f"},
    ))
    fig.update_layout(height=250, margin=dict(t=30, b=10, l=20, r=20))
    return fig


def budget_vs_actual_chart(budget_df: pd.DataFrame, actual_df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart: budget vs actual per category."""
    if budget_df.empty or actual_df.empty:
        return go.Figure()
    merged = pd.merge(budget_df, actual_df, on="category", how="outer").fillna(0)
    merged.columns = ["category", "budget", "actual"]
    merged = merged.sort_values("actual", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(y=merged["category"], x=merged["budget"],
                         name="Budget", orientation="h", marker_color="#93c5fd", opacity=0.7))
    fig.add_trace(go.Bar(y=merged["category"], x=merged["actual"],
                         name="Actual", orientation="h", marker_color=EXPENSE_COLOR, opacity=0.85))
    fig.update_layout(
        barmode="overlay", title="Budget vs Actual Spending",
        xaxis_title="Amount (₹)", height=max(300, len(merged) * 40),
        legend=dict(orientation="h", y=1.05),
        plot_bgcolor="#f8fafc", paper_bgcolor="white",
        margin=dict(l=150, r=30, t=50, b=40),
    )
    return fig


def prediction_bar_chart(pred_df: pd.DataFrame) -> go.Figure:
    """Bar chart for predicted category expenses."""
    if pred_df.empty:
        return go.Figure()
    fig = px.bar(
        pred_df.head(10), x="predicted_amount", y="category",
        orientation="h", title="Predicted Next Month Expenses by Category",
        color="predicted_amount", color_continuous_scale="Reds",
        labels={"predicted_amount": "Predicted Amount (₹)", "category": "Category"},
    )
    fig.update_layout(height=400, showlegend=False, plot_bgcolor="#f8fafc", paper_bgcolor="white")
    return fig


def heatmap_monthly_expense(df: pd.DataFrame) -> go.Figure:
    """Heatmap: category × month expense."""
    if df.empty:
        return go.Figure()
    pivot = df[df["type"] == "Expense"].pivot_table(
        index="category", columns="month", values="amount", aggfunc="sum", fill_value=0
    )
    month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    pivot.columns = [month_names.get(c, c) for c in pivot.columns]

    fig = px.imshow(
        pivot, title="Expense Heatmap (Category × Month)",
        color_continuous_scale="Reds", aspect="auto",
        labels=dict(color="Amount (₹)"),
    )
    fig.update_layout(height=400, paper_bgcolor="white")
    return fig