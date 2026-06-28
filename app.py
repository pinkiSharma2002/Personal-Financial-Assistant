"""
Finance Manager Pro — Main Streamlit App
CA-grade Personal Finance Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
import calendar
import sys
from pathlib import Path

# ── Path Setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from utils.db import init_db, register_user, login_user, get_user_by_id
from utils.data_manager import (
    load_transactions, add_transaction, delete_transaction,
    get_monthly_summary, get_yearly_summary,
    get_category_breakdown, get_monthly_trend,
    save_budget, get_budgets,
    INCOME_CATEGORIES, EXPENSE_CATEGORIES,
)
from utils.charts import (
    monthly_trend_chart, expense_pie_chart, income_expense_area_chart,
    savings_gauge, budget_vs_actual_chart, prediction_bar_chart, heatmap_monthly_expense,
)
from utils.report_gen import (
    generate_monthly_pdf, generate_yearly_pdf, transactions_to_csv,
)
from models.predictor import (
    predict_next_month_expense, predict_next_month_income,
    savings_goal_calculator, get_category_predictions, anomaly_detection,
)

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finance Manager Pro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .metric-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    border-radius: 12px;
    padding: 18px 22px;
    color: white;
    margin-bottom: 12px;
    box-shadow: 0 4px 12px rgba(37,99,235,0.25);
  }
  .metric-card.green { background: linear-gradient(135deg, #064e3b, #16a34a); }
  .metric-card.red   { background: linear-gradient(135deg, #7f1d1d, #dc2626); }
  .metric-card .label { font-size: 0.85rem; opacity: 0.85; font-weight: 500; }
  .metric-card .value { font-size: 1.9rem; font-weight: 700; margin-top: 4px; }
  .metric-card .sub   { font-size: 0.8rem; opacity: 0.7; margin-top: 2px; }
  .section-header {
    font-size: 1.2rem; font-weight: 700;
    color: #1e3a5f; border-left: 4px solid #2563eb;
    padding-left: 10px; margin: 18px 0 10px;
  }
  .stTabs [data-baseweb="tab"] { font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ── Session State ─────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None


def metric_card(label, value, sub="", color="blue"):
    cls = "green" if color == "green" else ("red" if color == "red" else "")
    return f"""
    <div class="metric-card {cls}">
      <div class="label">{label}</div>
      <div class="value">{value}</div>
      <div class="sub">{sub}</div>
    </div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH PAGES
# ═══════════════════════════════════════════════════════════════════════════════

def show_auth_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center; padding: 30px 0 10px;'>
          <h1 style='color:#2563eb; font-size:2.5rem;'>Finance Manager Pro</h1>
          <p style='color:#64748b; font-size:1.05rem;'>
            Your Personal CA Dashboard — Track · Analyze · Predict
          </p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])

        with tab_login:
            st.markdown("### Welcome Back!")
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
                if submitted:
                    if not username or not password:
                        st.error("Please fill all fields.")
                    else:
                        result = login_user(username, password)
                        if result["success"]:
                            st.session_state.logged_in = True
                            st.session_state.user = result["user"]
                            st.success("✅ Login successful!")
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")

        with tab_register:
            st.markdown("### Create Account")
            with st.form("register_form"):
                full_name = st.text_input("Full Name")
                email = st.text_input("Email")
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Register", use_container_width=True, type="primary")
                if submitted:
                    if not all([full_name, email, new_username, new_password]):
                        st.error("Please fill all fields.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        result = register_user(new_username, email, new_password, full_name)
                        if result["success"]:
                            st.success("✅ Registered! Please login.")
                        else:
                            st.error(f"❌ {result['message']}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def show_dashboard():
    user = st.session_state.user
    user_id = user["id"]
    full_name = user.get("full_name") or user["username"]

    now = datetime.now()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### 👤 {full_name}")
        st.caption(f"@{user['username']}")
        st.divider()

        page = st.radio(
            "Navigation",
            ["📊 Dashboard", "➕ Add Transaction", "📋 Transactions",
             "📈 Analysis", "🎯 Budget & Goals", "🔮 AI Predictions",
             "📄 Reports"],
            label_visibility="collapsed",
        )

        st.divider()
        sel_year = st.selectbox("📅 Year", list(range(now.year, now.year - 5, -1)))
        sel_month = st.selectbox("📅 Month", list(range(1, 13)),
                                 index=now.month - 1,
                                 format_func=lambda m: calendar.month_name[m])
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()

    # ── Load Data ─────────────────────────────────────────────────────────────
    df = load_transactions(user_id)
    monthly = get_monthly_summary(user_id, sel_year, sel_month)
    trend_df = get_monthly_trend(user_id, sel_year)

    # ═══ PAGE: DASHBOARD ════════════════════════════════════════════════════
    if page == "📊 Dashboard":
        st.markdown(f"## 📊 Dashboard — {calendar.month_name[sel_month]} {sel_year}")

        # KPI Cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(metric_card("💰 Total Income",
                f"₹{monthly['income']:,.0f}", "This month", "green"),
                unsafe_allow_html=True)
        with c2:
            st.markdown(metric_card("💸 Total Expenses",
                f"₹{monthly['expense']:,.0f}", "This month", "red"),
                unsafe_allow_html=True)
        with c3:
            bal_color = "green" if monthly["balance"] >= 0 else "red"
            st.markdown(metric_card("📈 Net Balance",
                f"₹{monthly['balance']:,.0f}", "Savings this month", bal_color),
                unsafe_allow_html=True)
        with c4:
            st.markdown(metric_card("🎯 Savings Rate",
                f"{monthly['savings_rate']:.1f}%", "Target: ≥ 20%", "blue"),
                unsafe_allow_html=True)

        st.divider()

        # Charts row
        col_left, col_right = st.columns([3, 2])
        with col_left:
            st.markdown('<div class="section-header">Monthly Trend</div>', unsafe_allow_html=True)
            st.plotly_chart(monthly_trend_chart(trend_df), use_container_width=True)

        with col_right:
            st.markdown('<div class="section-header">Savings Rate</div>', unsafe_allow_html=True)
            st.plotly_chart(savings_gauge(monthly["savings_rate"]), use_container_width=True)

            # Quick yearly stats
            ys = get_yearly_summary(user_id, sel_year)
            st.metric("Annual Income", f"₹{ys['income']:,.0f}")
            st.metric("Annual Expense", f"₹{ys['expense']:,.0f}")
            st.metric("Annual Balance", f"₹{ys['balance']:,.0f}",
                      delta=f"₹{ys['balance']:,.0f}")

        # Expense Breakdown
        st.markdown('<div class="section-header">Expense Breakdown (This Month)</div>', unsafe_allow_html=True)
        exp_bkdn = get_category_breakdown(user_id, sel_year, sel_month, "Expense")
        inc_bkdn = get_category_breakdown(user_id, sel_year, sel_month, "Income")
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(expense_pie_chart(exp_bkdn, "Expenses by Category"), use_container_width=True)
        with c2:
            st.plotly_chart(expense_pie_chart(inc_bkdn, "Income by Source"), use_container_width=True)

        # Recent transactions
        if not df.empty:
            st.markdown('<div class="section-header">Recent Transactions</div>', unsafe_allow_html=True)
            recent = df.sort_values("date", ascending=False).head(8)[
                ["date", "type", "category", "description", "amount"]
            ].copy()
            recent["date"] = recent["date"].dt.strftime("%d %b %Y")
            recent["amount"] = recent["amount"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(recent, use_container_width=True, hide_index=True)

    # ═══ PAGE: ADD TRANSACTION ═══════════════════════════════════════════════
    elif page == "➕ Add Transaction":
        st.markdown("## ➕ Add Transaction")
        col1, col2 = st.columns([2, 1])
        with col1:
            txn_type = st.selectbox("Type", ["Income", "Expense"])
            with st.form("add_txn_form", clear_on_submit=True):
                
                categories = INCOME_CATEGORIES if txn_type == "Income" else EXPENSE_CATEGORIES
                
                category = st.selectbox("Category", categories)
                amount = st.number_input("Amount (₹)", min_value=0.01, step=100.0, format="%.2f")
                txn_date = st.date_input("Date", value=date.today())
                description = st.text_input("Description (optional)")
                submitted = st.form_submit_button("✅ Add Transaction", type="primary", use_container_width=True)

                if submitted:
                    if amount <= 0:
                        st.error("Amount must be greater than 0.")
                    else:
                        if add_transaction(user_id, txn_date, txn_type, category, amount, description):
                            st.success(f"✅ {txn_type} of ₹{amount:,.2f} added!")
                            st.rerun()

        with col2:
            st.markdown("### 💡 Quick Tips")
            st.info("• Add transactions regularly for accurate predictions.\n\n"
                    "• Use consistent categories for better analysis.\n\n"
                    "• Track even small expenses for complete picture.")

    # ═══ PAGE: TRANSACTIONS ══════════════════════════════════════════════════
    elif page == "📋 Transactions":
        st.markdown("## 📋 All Transactions")
        if df.empty:
            st.info("No transactions yet. Add some from '➕ Add Transaction'.")
        else:
            # Filters
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                f_type = st.selectbox("Filter Type", ["All", "Income", "Expense"])
            with fc2:
                f_year = st.selectbox("Filter Year", ["All"] + sorted(df["year"].unique().tolist(), reverse=True))
            with fc3:
                f_month = st.selectbox("Filter Month", ["All"] + list(range(1, 13)),
                                       format_func=lambda m: "All" if m == "All" else calendar.month_name[m])

            filtered = df.copy()
            if f_type != "All":
                filtered = filtered[filtered["type"] == f_type]
            if f_year != "All":
                filtered = filtered[filtered["year"] == int(f_year)]
            if f_month != "All":
                filtered = filtered[filtered["month"] == int(f_month)]

            filtered = filtered.sort_values("date", ascending=False)

            st.markdown(f"**{len(filtered)} transactions** | "
                        f"Income: ₹{filtered[filtered['type']=='Income']['amount'].sum():,.2f} | "
                        f"Expense: ₹{filtered[filtered['type']=='Expense']['amount'].sum():,.2f}")

            disp = filtered[["id","date","type","category","description","amount"]].copy()
            disp["date"] = disp["date"].dt.strftime("%d %b %Y")
            disp["amount"] = disp["amount"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(disp, use_container_width=True, hide_index=True)

            # Delete transaction
            st.markdown("### 🗑️ Delete Transaction")
            del_id = st.number_input("Enter Transaction ID to delete", min_value=1, step=1)
            if st.button("Delete", type="secondary"):
                if delete_transaction(user_id, int(del_id)):
                    st.success(f"Transaction #{del_id} deleted.")
                    st.rerun()
                else:
                    st.error("Transaction not found.")

    # ═══ PAGE: ANALYSIS ══════════════════════════════════════════════════════
    elif page == "📈 Analysis":
        st.markdown(f"## 📈 Financial Analysis — {sel_year}")

        if df.empty:
            st.info("Add transactions to see analysis.")
        else:
            t1, t2, t3 = st.tabs(["📊 Trends", "🗂️ Category", "🌡️ Heatmap"])

            with t1:
                st.plotly_chart(income_expense_area_chart(trend_df), use_container_width=True)
                st.plotly_chart(monthly_trend_chart(trend_df), use_container_width=True)

            with t2:
                col1, col2 = st.columns(2)
                with col1:
                    exp_bkdn = get_category_breakdown(user_id, sel_year, None, "Expense")
                    st.plotly_chart(expense_pie_chart(exp_bkdn, f"Yearly Expense Breakdown {sel_year}"),
                                    use_container_width=True)
                with col2:
                    inc_bkdn = get_category_breakdown(user_id, sel_year, None, "Income")
                    st.plotly_chart(expense_pie_chart(inc_bkdn, f"Yearly Income Breakdown {sel_year}"),
                                    use_container_width=True)

            with t3:
                st.plotly_chart(heatmap_monthly_expense(df[df["year"] == sel_year]), use_container_width=True)

    # ═══ PAGE: BUDGET & GOALS ════════════════════════════════════════════════
    elif page == "🎯 Budget & Goals":
        st.markdown(f"## 🎯 Budget — {calendar.month_name[sel_month]} {sel_year}")

        t_budget, t_goals = st.tabs(["📋 Set Budget", "🏠 Savings Goals"])

        with t_budget:
            st.markdown("### Set Monthly Budget by Category")
            budgets = get_budgets(user_id, sel_month, sel_year)
            budget_dict = {}
            if not budgets.empty:
                budget_dict = dict(zip(budgets["category"], budgets["budget_amount"]))

            with st.form("budget_form"):
                cols = st.columns(2)
                new_budgets = {}
                for i, cat in enumerate(EXPENSE_CATEGORIES):
                    with cols[i % 2]:
                        val = budget_dict.get(cat, 0.0)
                        new_budgets[cat] = st.number_input(
                            cat, min_value=0.0, value=float(val), step=500.0,
                            format="%.0f", key=f"bgt_{cat}"
                        )
                if st.form_submit_button("💾 Save Budgets", type="primary", use_container_width=True):
                    for cat, amt in new_budgets.items():
                        save_budget(user_id, cat, sel_month, sel_year, amt)
                    st.success("✅ Budgets saved!")
                    st.rerun()

            # Budget vs Actual
            if not budgets.empty:
                st.markdown("### Budget vs Actual Spending")
                actual = get_category_breakdown(user_id, sel_year, sel_month, "Expense")
                b_df = pd.DataFrame(list(budget_dict.items()), columns=["category", "amount"])
                st.plotly_chart(budget_vs_actual_chart(b_df, actual), use_container_width=True)

        with t_goals:
            st.markdown("### 🏠 Savings Goal Calculator")
            monthly_data = get_monthly_summary(user_id, now.year, now.month)
            avg_income = monthly_data["income"]
            avg_expense = monthly_data["expense"]

            st.info(f"📊 Current Month — Income: ₹{avg_income:,.0f} | Expense: ₹{avg_expense:,.0f} | "
                    f"Savings: ₹{max(0, avg_income - avg_expense):,.0f}")

            st.markdown("#### Add Your Goals")
            num_goals = st.number_input("Number of Goals", min_value=1, max_value=5, value=2)
            goals = []
            for i in range(int(num_goals)):
                st.markdown(f"**Goal {i+1}**")
                gc1, gc2, gc3 = st.columns(3)
                with gc1:
                    gname = st.text_input("Goal Name", key=f"gn_{i}",
                                          placeholder=["Home", "Car", "Education", "Travel", "Emergency"][i % 5])
                with gc2:
                    gamt = st.number_input("Target Amount (₹)", min_value=1000.0, step=10000.0,
                                           value=500000.0, key=f"ga_{i}")
                with gc3:
                    gmonths = st.number_input("In how many months?", min_value=1, max_value=360,
                                              value=24, key=f"gm_{i}")
                if gname:
                    goals.append({"name": gname, "amount": gamt, "months": gmonths})

            if st.button("🔮 Calculate", type="primary") and goals:
                result = savings_goal_calculator(avg_income, avg_expense, goals)
                st.divider()
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Monthly Savings Needed", f"₹{result['total_monthly_savings_needed']:,.0f}")
                with c2:
                    st.metric("Recommended Max Expense", f"₹{result['recommended_max_expense']:,.0f}")
                with c3:
                    st.metric("Current Savings", f"₹{result['current_savings']:,.0f}")

                for g in result["goals"]:
                    with st.expander(f"🎯 {g['name']} — ₹{g['target']:,.0f}"):
                        if g["achievable"]:
                            st.success(f"✅ Achievable! Save ₹{g['monthly_needed']:,.0f}/month")
                        else:
                            st.warning(f"⚠️ Need ₹{g['monthly_needed']:,.0f}/month. "
                                       f"Cut expenses by ₹{g['shortfall']:,.0f}")

    # ═══ PAGE: AI PREDICTIONS ════════════════════════════════════════════════
    elif page == "🔮 AI Predictions":
        st.markdown("## 🔮 AI-Powered Predictions")

        if df.empty:
            st.info("Add at least 2 months of data for predictions.")
        else:
            t1, t2, t3 = st.tabs(["📅 Next Month", "📊 Category Forecast", "🚨 Anomalies"])

            with t1:
                pred_exp = predict_next_month_expense(df)
                pred_inc = predict_next_month_income(df)
                next_m = now.month % 12 + 1
                next_y = now.year + (1 if next_m == 1 else 0)
                next_month_name = calendar.month_name[next_m]

                st.markdown(f"### Predictions for {next_month_name} {next_y}")

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(metric_card("📈 Predicted Income",
                        f"₹{pred_inc['predicted']:,.0f}", "Based on history", "green"),
                        unsafe_allow_html=True)
                with c2:
                    st.markdown(metric_card("📉 Predicted Expense",
                        f"₹{pred_exp['predicted']:,.0f}",
                        f"Range: ₹{pred_exp.get('lower_bound',0):,.0f}–₹{pred_exp.get('upper_bound',0):,.0f}",
                        "red"), unsafe_allow_html=True)
                with c3:
                    pred_bal = pred_inc["predicted"] - pred_exp["predicted"]
                    bal_color = "green" if pred_bal >= 0 else "red"
                    st.markdown(metric_card("💰 Predicted Balance",
                        f"₹{pred_bal:,.0f}", "Net savings forecast", bal_color),
                        unsafe_allow_html=True)

                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Trend:** {pred_exp['trend'].title()}")
                    st.info(f"**Confidence:** {pred_exp['confidence'].title()}")
                with col2:
                    st.info(pred_exp.get("message", ""))
                    if pred_exp["trend"] == "increasing":
                        st.warning("⚠️ Expenses are trending up! Consider reviewing your spending.")
                    elif pred_exp["trend"] == "decreasing":
                        st.success("✅ Great! Your expenses are trending down.")

            with t2:
                cat_pred = get_category_predictions(df)
                if not cat_pred.empty:
                    st.plotly_chart(prediction_bar_chart(cat_pred), use_container_width=True)
                    st.dataframe(
                        cat_pred.assign(predicted_amount=cat_pred["predicted_amount"].apply(
                            lambda x: f"₹{x:,.2f}")),
                        use_container_width=True, hide_index=True,
                    )

            with t3:
                anomalies = anomaly_detection(df)
                if anomalies.empty:
                    st.success("✅ No unusual spending patterns detected!")
                else:
                    st.warning(f"⚠️ {len(anomalies)} unusual transactions found")
                    disp = anomalies[["date","category","description","amount"]].copy()
                    disp["date"] = disp["date"].dt.strftime("%d %b %Y")
                    disp["amount"] = disp["amount"].apply(lambda x: f"₹{x:,.2f}")
                    st.dataframe(disp, use_container_width=True, hide_index=True)

    # ═══ PAGE: REPORTS ═══════════════════════════════════════════════════════
    elif page == "📄 Reports":
        st.markdown("## 📄 Reports & Export")

        t_monthly, t_yearly, t_csv = st.tabs(["📅 Monthly Report", "📆 Yearly Report", "📊 Export CSV"])

        with t_monthly:
            st.markdown(f"### Monthly Balance Sheet — {calendar.month_name[sel_month]} {sel_year}")
            if df.empty:
                st.info("No data to generate report.")
            else:
                monthly_s = get_monthly_summary(user_id, sel_year, sel_month)
                inc_bkdn = get_category_breakdown(user_id, sel_year, sel_month, "Income")
                exp_bkdn = get_category_breakdown(user_id, sel_year, sel_month, "Expense")

                # Preview
                c1, c2, c3 = st.columns(3)
                c1.metric("Income", f"₹{monthly_s['income']:,.2f}")
                c2.metric("Expense", f"₹{monthly_s['expense']:,.2f}")
                c3.metric("Balance", f"₹{monthly_s['balance']:,.2f}")

                pdf_bytes = generate_monthly_pdf(
                    full_name, sel_year, sel_month, monthly_s, inc_bkdn, exp_bkdn, df
                )
                st.download_button(
                    "⬇️ Download Monthly PDF Report",
                    data=pdf_bytes,
                    file_name=f"monthly_report_{sel_year}_{sel_month:02d}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )

        with t_yearly:
            st.markdown(f"### Annual Financial Report — {sel_year}")
            if df.empty:
                st.info("No data to generate report.")
            else:
                yearly_s = get_yearly_summary(user_id, sel_year)
                c1, c2, c3 = st.columns(3)
                c1.metric("Annual Income", f"₹{yearly_s['income']:,.2f}")
                c2.metric("Annual Expense", f"₹{yearly_s['expense']:,.2f}")
                c3.metric("Annual Balance", f"₹{yearly_s['balance']:,.2f}")

                pdf_bytes = generate_yearly_pdf(full_name, sel_year, yearly_s, trend_df)
                st.download_button(
                    "⬇️ Download Annual PDF Report",
                    data=pdf_bytes,
                    file_name=f"annual_report_{sel_year}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )

        with t_csv:
            st.markdown("### Export Transactions to CSV")
            if df.empty:
                st.info("No transactions to export.")
            else:
                csv_bytes = transactions_to_csv(df)
                st.download_button(
                    "⬇️ Download My Transactions (CSV)",
                    data=csv_bytes,
                    file_name=f"transactions_{user['username']}_{now.strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    type="primary",
                )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    init_db()
    if st.session_state.logged_in and st.session_state.user:
        show_dashboard()
    else:
        show_auth_page()


if __name__ == "__main__":
    main()