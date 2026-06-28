"""
Report Generator
- Monthly/Yearly Balance Sheet (PDF + CSV export)
- CA-style formatted reports
"""
import io
import pandas as pd
from datetime import datetime
from fpdf import FPDF


class FinanceReport(FPDF):
    """Custom PDF class for finance reports."""

    def __init__(self, title="Finance Report"):
        super().__init__()
        self.report_title = title

    def _safe(self, text: str) -> str:
        """Replace characters unsupported by Helvetica."""
        return (
            str(text)
            .replace("₹", "Rs.")
            .replace("\u20b9", "Rs.")
            .replace("\u2013", "-")
            .replace("\u2014", "-")
            .replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
        )

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_fill_color(26, 86, 219)
        self.set_text_color(255, 255, 255)
        self.cell(0, 12, self._safe(self.report_title), ln=True, align="C", fill=True)
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 9)
        self.cell(
            0, 6,
            f"Generated on: {datetime.now().strftime('%d %B %Y, %I:%M %p')}",
            ln=True, align="R"
        )
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()} | Finance Manager Pro", align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(240, 244, 255)
        self.set_text_color(26, 86, 219)
        self.cell(0, 9, self._safe(f"  {title}"), ln=True, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def kv_row(self, key: str, value: str, bold_value=False, color=None):
        self.set_font("Helvetica", "", 10)
        self.cell(90, 7, self._safe(f"  {key}"), border="B")
        if bold_value:
            self.set_font("Helvetica", "B", 10)
        if color:
            self.set_text_color(*color)
        self.cell(0, 7, self._safe(f"  Rs. {value}"), border="B", ln=True)
        self.set_text_color(0, 0, 0)

    def table(self, headers: list, rows: list, col_widths: list = None):
        if col_widths is None:
            col_widths = [190 // len(headers)] * len(headers)
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(26, 86, 219)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 8, self._safe(str(h)), border=1, fill=True, align="C")
        self.ln()
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 9)
        for idx, row in enumerate(rows):
            if idx % 2 == 0:
                self.set_fill_color(248, 250, 255)
            else:
                self.set_fill_color(255, 255, 255)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 7, self._safe(str(cell)), border=1, fill=True)
            self.ln()
        self.ln(3)


def generate_monthly_pdf(
    user_name: str,
    year: int,
    month: int,
    summary: dict,
    income_breakdown: pd.DataFrame,
    expense_breakdown: pd.DataFrame,
    transactions: pd.DataFrame,
) -> bytes:
    month_name = datetime(year, month, 1).strftime("%B %Y")
    pdf = FinanceReport(f"Monthly Financial Report of {month_name}")
    pdf.add_page()

    # Summary Section
    pdf.section_title("Account Summary")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, pdf._safe(f"  Account Holder: {user_name}"), ln=True)
    pdf.cell(0, 6, pdf._safe(f"  Period: {month_name}"), ln=True)
    pdf.ln(3)

    pdf.kv_row("Total Income", f"{summary['income']:,.2f}", bold_value=True, color=(22, 163, 74))
    pdf.kv_row("Total Expenses", f"{summary['expense']:,.2f}", bold_value=True, color=(220, 38, 38))
    pdf.kv_row(
        "Net Balance (Savings)", f"{summary['balance']:,.2f}", bold_value=True,
        color=(22, 163, 74) if summary["balance"] >= 0 else (220, 38, 38),
    )
    pdf.kv_row("Savings Rate", f"{summary['savings_rate']:.1f}%")
    pdf.ln(6)

    # Income Breakdown
    if not income_breakdown.empty:
        pdf.section_title("Income Breakdown")
        rows = [
            [row["category"], f"Rs.{row['amount']:,.2f}"]
            for _, row in income_breakdown.iterrows()
        ]
        pdf.table(["Category", "Amount"], rows, [120, 70])

    # Expense Breakdown
    if not expense_breakdown.empty:
        pdf.section_title("Expense Breakdown")
        rows = [
            [row["category"], f"Rs.{row['amount']:,.2f}"]
            for _, row in expense_breakdown.iterrows()
        ]
        pdf.table(["Category", "Amount"], rows, [120, 70])

    # Transactions
    if not transactions.empty:
        pdf.section_title("All Transactions")
        m_txns = transactions[
            (transactions["month"] == month) & (transactions["year"] == year)
        ].sort_values("date", ascending=False)
        rows = []
        for _, row in m_txns.iterrows():
            desc = str(row["description"])[:20] if pd.notna(row["description"]) else ""
            rows.append([
                str(row["date"])[:10],
                row["type"],
                row["category"],
                desc,
                f"Rs.{row['amount']:,.2f}",
            ])
        pdf.table(
            ["Date", "Type", "Category", "Description", "Amount"],
            rows,
            [35, 22, 38, 60, 35],
        )

    pdf_bytes = pdf.output(dest="S")
    return bytes(pdf_bytes)


def generate_yearly_pdf(
    user_name: str,
    year: int,
    yearly_summary: dict,
    monthly_trend: pd.DataFrame,
) -> bytes:
    pdf = FinanceReport(f"Annual Financial Report of {year}")
    pdf.add_page()

    pdf.section_title("Annual Summary")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, pdf._safe(f"  Account Holder: {user_name}"), ln=True)
    pdf.cell(0, 6, pdf._safe(f"  Financial Year: {year}"), ln=True)
    pdf.ln(3)

    pdf.kv_row("Total Annual Income", f"{yearly_summary['income']:,.2f}", bold_value=True, color=(22, 163, 74))
    pdf.kv_row("Total Annual Expenses", f"{yearly_summary['expense']:,.2f}", bold_value=True, color=(220, 38, 38))
    pdf.kv_row(
        "Net Annual Balance", f"{yearly_summary['balance']:,.2f}", bold_value=True,
        color=(22, 163, 74) if yearly_summary["balance"] >= 0 else (220, 38, 38),
    )
    pdf.ln(6)

    if not monthly_trend.empty:
        pdf.section_title("Month-wise Breakdown")
        rows = []
        for _, row in monthly_trend.iterrows():
            balance = row["income"] - row["expense"]
            rows.append([
                row["month_name"],
                f"Rs.{row['income']:,.2f}",
                f"Rs.{row['expense']:,.2f}",
                f"Rs.{balance:,.2f}",
            ])
        pdf.table(
            ["Month", "Income", "Expense", "Net Balance"],
            rows,
            [40, 52, 52, 52],
        )

    buf = io.BytesIO()
    buf.write(pdf.output())
    buf.seek(0)
    return buf.read()


def transactions_to_csv(transactions: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    transactions.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")