from fastapi import FastAPI, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import Form, UploadFile, File
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from fastapi.responses import StreamingResponse
import io
import csv
from openpyxl import Workbook
from fastapi.staticfiles import StaticFiles
import models
import plotly.express as px
from fastapi import HTTPException
from starlette.responses import RedirectResponse
from starlette.requests import Request
import pandas as pd
from database import engine, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Dhanyalakshmi Insurancewala")

import os, sys

def resource_path(rel_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)

TEMPLATES_DIR = resource_path("templates")
STATIC_DIR = resource_path("static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

ALLOWED_LOGIN_ROLES = {"Owner", "Co-Owner"}

# Session secret
SECRET_KEY = "CHANGE_THIS_TO_A_RANDOM_LONG_SECRET_1234567890"
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# app.mount("/static", StaticFiles(directory="static"), name="static")

@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    # Redirect unauthenticated users to login for browser pages
    if exc.status_code == 401:
        return RedirectResponse(url="/login", status_code=302)
    raise exc

# templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def export_csv(filename: str, headers: list[str], rows: list[list]):
    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(r)
        yield buffer.getvalue().encode("utf-8")

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'}
    )


def export_excel(filename: str, headers: list[str], rows: list[list]):
    wb = Workbook()
    ws = wb.active
    ws.title = "Export"

    ws.append(headers)
    for r in rows:
        ws.append(r)

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}.xlsx"'}
    )

# ---------- Helpers ----------
def _policy_stats(db: Session, insurance_type: str):
    q = db.query(models.Policy).filter(models.Policy.insurance_type == insurance_type)
    total_premium = q.with_entities(func.sum(models.Policy.premium_with_gst)).scalar() or 0
    total_commission = q.with_entities(func.sum(models.Policy.commission)).scalar() or 0
    total_profit = q.with_entities(func.sum(models.Policy.net_profit)).scalar() or 0
    count = q.count()
    policies = q.order_by(models.Policy.id.desc()).limit(50).all()
    return total_premium, total_commission, total_profit, count, policies

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def get_current_user(request: Request):
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "id": uid,
        "role": request.session.get("role"),
        "name": request.session.get("name"),
    }

def require_user(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "id": request.session.get("user_id"),
        "role": request.session.get("role"),
        "name": request.session.get("name"),
    }

# # ---------- Pages ----------
# @app.get("/", response_class=HTMLResponse)
# def dashboard(request: Request, db: Session = Depends(get_db)):
#     user = get_current_user(request)
#     total_premium = db.query(
#     func.sum(func.coalesce(models.Policy.premium_with_gst, models.Policy.premium, 0))
#     ).scalar() or 0
#     total_commission = db.query(func.sum(models.Policy.commission)).scalar() or 0
#     total_profit = db.query(func.sum(models.Policy.net_profit)).scalar() or 0
#     active_policies = db.query(models.Policy).count()

#     policies = db.query(models.Policy).order_by(models.Policy.id.desc()).limit(10).all()

#     total_employees = db.query(models.User).count()
#     present_today = db.query(models.Attendance).filter(models.Attendance.status == "Present").count()
#     leave_today = db.query(models.Attendance).filter(models.Attendance.status == "Leave").count()
#     late_today = db.query(models.Attendance).filter(models.Attendance.status == "Late").count()

#     return templates.TemplateResponse("dashboard.html", {
#         "request": request,
#         "active": "dashboard",
#         "user_name": user["name"],
#         "total_premium": total_premium,
#         "total_commission": total_commission,
#         "total_profit": total_profit,
#         "active_policies": active_policies,
#         "policies": policies,
#         "total_employees": total_employees,
#         "present_today": present_today,
#         "leave_today": leave_today,
#         "late_today": late_today,
#         # charts placeholders (safe)
#         "monthly_chart": "<div class='chart-placeholder'>[Chart Placeholder - Plotly Here]</div>",
#         "pie_chart": "<div class='chart-placeholder'>[Pie Chart Placeholder]</div>",
#     })


@app.get("/car", response_class=HTMLResponse)
def car_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    total_premium, total_commission, total_profit, count, policies = _policy_stats(db, "Car")
    return templates.TemplateResponse("car.html", {
        "request": request,
        "active": "car",
        "user_name": user["name"],
        "type_name": "Car Insurance",
        "total_premium": total_premium,
        "total_commission": total_commission,
        "total_profit": total_profit,
        "total_policies": count,
        "policies": policies,
    })


@app.get("/health", response_class=HTMLResponse)
def health_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    total_premium, total_commission, total_profit, count, policies = _policy_stats(db, "Health")
    return templates.TemplateResponse("health.html", {
        "request": request,
        "active": "health",
        "user_name": user["name"],
        "type_name": "Health Insurance",
        "total_premium": total_premium,
        "total_commission": total_commission,
        "total_profit": total_profit,
        "total_policies": count,
        "policies": policies,
    })


@app.get("/term", response_class=HTMLResponse)
def term_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    total_premium, total_commission, total_profit, count, policies = _policy_stats(db, "Term")
    return templates.TemplateResponse("term.html", {
        "request": request,
        "active": "term",
        "user_name": user["name"],
        "type_name": "Term Insurance",
        "total_premium": total_premium,
        "total_commission": total_commission,
        "total_profit": total_profit,
        "total_policies": count,
        "policies": policies,
    })


@app.get("/general", response_class=HTMLResponse)
def general_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    total_premium, total_commission, total_profit, count, policies = _policy_stats(db, "General")
    return templates.TemplateResponse("general.html", {
        "request": request,
        "active": "general",
        "user_name": user["name"],
        "type_name": "General Insurance",
        "total_premium": total_premium,
        "total_commission": total_commission,
        "total_profit": total_profit,
        "total_policies": count,
        "policies": policies,
    })


@app.get("/employees", response_class=HTMLResponse)
def employees_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    employees = db.query(models.User).order_by(models.User.id.desc()).all()
    return templates.TemplateResponse("employees.html", {
        "request": request,
        "active": "employees",
        "employees": employees
    })


@app.get("/attendance-page", response_class=HTMLResponse)
def attendance_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)

    latest = db.query(func.max(models.Attendance.date)).scalar()

    q = db.query(models.Attendance)
    if latest:
        q = q.filter(models.Attendance.date == latest)

    attendance = q.all()

    total = len(attendance)
    present = sum(1 for a in attendance if a.status in ("On Time", "Late", "Early"))
    late = sum(1 for a in attendance if a.status == "Late")
    on_time = sum(1 for a in attendance if a.status == "On Time")
    early = sum(1 for a in attendance if a.status == "Early")
    absent = sum(1 for a in attendance if a.status == "Absent")

    left_early_count = sum(1 for a in attendance if (a.left_early_minutes or 0) > 0)
    overtime_count = sum(1 for a in attendance if (a.overtime_minutes or 0) > 0)

    late_list = sorted(
        [a for a in attendance if a.status == "Late"],
        key=lambda x: (x.minutes_late or 0),
        reverse=True
    )[:10]

    late_minutes = [a.minutes_late for a in attendance if a.status == "Late" and a.minutes_late is not None]
    avg_late = round(sum(late_minutes) / len(late_minutes), 1) if late_minutes else 0

    worked_list = [a.worked_minutes for a in attendance if a.worked_minutes]
    total_worked = sum(worked_list) if worked_list else 0
    avg_worked = round(total_worked / len(worked_list), 1) if worked_list else 0

    return templates.TemplateResponse("attendance.html", {
        "request": request,
        "active": "attendance",
        "user_name": user.get("name"),
        "latest_date": latest or "-",
        "attendance": attendance,

        "kpi_total": total,
        "kpi_present": present,
        "kpi_late": late,
        "kpi_on_time": on_time,
        "kpi_early": early,
        "kpi_absent": absent,
        "kpi_left_early": left_early_count,
        "kpi_overtime": overtime_count,
        "avg_late": avg_late,
        "avg_worked": avg_worked,
        "late_list": late_list,
    })

@app.get("/commissions", response_class=HTMLResponse)
def commissions_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    total_commission = db.query(func.sum(models.Policy.commission)).scalar() or 0
    total_payout = db.query(func.sum(models.Policy.payout)).scalar() or 0
    total_profit = db.query(func.sum(models.Policy.net_profit)).scalar() or 0

    rows = (
        db.query(
            models.User.name.label("employee"),
            func.sum(models.Policy.commission).label("commission"),
            func.sum(models.Policy.payout).label("payout"),
            func.sum(models.Policy.net_profit).label("profit"),
            func.count(models.Policy.id).label("policies"),
        )
        .join(models.Policy, models.Policy.employee_id == models.User.id, isouter=True)
        .group_by(models.User.name)
        .order_by(func.sum(models.Policy.commission).desc().nullslast())
        .all()
    )

    return templates.TemplateResponse("commissions.html", {
        "request": request,
        "active": "commissions",
        "user_name": user["name"],
        "total_commission": total_commission,
        "total_payout": total_payout,
        "total_profit": total_profit,
        "rows": rows,
    })


@app.get("/expenses", response_class=HTMLResponse)
def expenses_page(request: Request):
    return templates.TemplateResponse("expenses.html", {
        "request": request,
        "active": "expenses",
    })


@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "active": "reports",
    })

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)

    total_premium = db.query(
        func.sum(func.coalesce(models.Policy.premium_with_gst, models.Policy.premium, 0))
    ).scalar() or 0

    total_commission = db.query(func.sum(func.coalesce(models.Policy.commission, 0))).scalar() or 0
    total_profit = db.query(func.sum(func.coalesce(models.Policy.net_profit, 0))).scalar() or 0
    active_policies = db.query(models.Policy).count()

    # Recent policies
    policies = db.query(models.Policy).order_by(models.Policy.id.desc()).limit(10).all()

    # -------- Chart 1: Monthly Premium vs Profit ----------
    policy_rows = db.query(
        models.Policy.policy_date,
        models.Policy.premium_with_gst,
        models.Policy.premium,
        models.Policy.net_profit
    ).filter(models.Policy.policy_date.isnot(None)).all()

    df = pd.DataFrame(policy_rows, columns=["policy_date", "premium_with_gst", "premium", "net_profit"])

    if not df.empty:
        df["policy_date"] = pd.to_datetime(df["policy_date"])
        df["month"] = df["policy_date"].dt.to_period("M").astype(str)

        df["Total Premium"] = df["premium_with_gst"].fillna(df["premium"]).fillna(0)
        df["Total Profit"] = df["net_profit"].fillna(0)

        monthly = df.groupby("month", as_index=False)[["Total Premium", "Total Profit"]].sum()

        fig1 = px.bar(
            monthly,
            x="month",
            y=["Total Premium", "Total Profit"],
            barmode="group",
            title="Monthly Premium vs Profit"
        )
        fig1.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=280)

        monthly_chart = fig1.to_html(full_html=False, include_plotlyjs="cdn")
    else:
        monthly_chart = "<div class='chart-placeholder'>No data with Policy Date to plot</div>"

    # -------- Chart 2: Insurance Type Distribution ----------
    type_rows = db.query(
        models.Policy.insurance_type,
        func.sum(func.coalesce(models.Policy.premium_with_gst, models.Policy.premium, 0)).label("premium_sum")
    ).group_by(models.Policy.insurance_type).all()

    df2 = pd.DataFrame(type_rows, columns=["insurance_type", "premium_sum"])

    if not df2.empty and float(df2["premium_sum"].sum()) > 0:
        fig2 = px.pie(
            df2,
            names="insurance_type",
            values="premium_sum",
            title="Insurance Type Distribution"
        )
        fig2.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=280)

        # Don't include plotly JS twice
        pie_chart = fig2.to_html(full_html=False, include_plotlyjs=False)
    else:
        pie_chart = "<div class='chart-placeholder'>No premium data to plot</div>"

    # Attendance summary (use latest date so it matches Attendance page)
    latest_att_date = db.query(func.max(models.Attendance.date)).scalar()

    if latest_att_date:
        att_q = db.query(models.Attendance).filter(models.Attendance.date == latest_att_date)
    else:
        att_q = db.query(models.Attendance).filter(False)  # empty

    total_employees = db.query(models.User).count()
    present_today = att_q.filter(models.Attendance.status.in_(["On Time", "Late", "Early"])).count()
    leave_today = att_q.filter(models.Attendance.status == "Leave").count()  # if you still use Leave later
    late_today = att_q.filter(models.Attendance.status == "Late").count()

    # Attendance summary (optional, keep if you have it on dashboard)
    # total_employees = db.query(models.User).count()
    # present_today = db.query(models.Attendance).filter(models.Attendance.status == "Present").count()
    # leave_today = db.query(models.Attendance).filter(models.Attendance.status == "Leave").count()
    # late_today = db.query(models.Attendance).filter(models.Attendance.status == "Late").count()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active": "dashboard",
        "user_name": user.get("name"),

        "total_premium": total_premium,
        "total_commission": total_commission,
        "total_profit": total_profit,
        "active_policies": active_policies,

        "monthly_chart": monthly_chart,
        "pie_chart": pie_chart,

        "policies": policies,

        "total_employees": total_employees,
        "present_today": present_today,
        "leave_today": leave_today,
        "late_today": late_today,
    })

@app.get("/export/policies/Car/csv")
def export_car_csv(db: Session = Depends(get_db)):
    policies = db.query(models.Policy).filter(models.Policy.insurance_type == "Car").all()

    headers = [
        "Customer name", "Car type/Model", "Variant", "Car number",
        "Policy Date", "Expiry Date",
        "Premium with GST", "Premium without GST",
        "Employee Name", "Commission", "Payout", "Net Profit", "Claim", "Company"
    ]

    rows = []
    for p in policies:
        rows.append([
            p.customer_name,
            p.vehicle_model or "",
            p.vehicle_variant or "",
            p.vehicle_number or "",
            str(p.policy_date or ""),
            str(p.expiry_date or ""),
            p.premium_with_gst or 0,
            p.premium_without_gst or 0,
            (p.employee.name if p.employee else ""),
            p.commission or 0,
            p.payout or 0,
            p.net_profit or 0,
            p.claim_status or "",
            p.company or "",
        ])

    return export_csv("car_policies", headers, rows)

@app.get("/export/policies/Car/excel")
def export_car_excel(db: Session = Depends(get_db)):
    policies = db.query(models.Policy).filter(models.Policy.insurance_type == "Car").all()

    headers = [
        "Customer name", "Car type/Model", "Variant", "Car number",
        "Policy Date", "Expiry Date",
        "Premium with GST", "Premium without GST",
        "Employee Name", "Commission", "Payout", "Net Profit", "Claim", "Company"
    ]

    rows = []
    for p in policies:
        rows.append([
            p.customer_name,
            p.vehicle_model or "",
            p.vehicle_variant or "",
            p.vehicle_number or "",
            str(p.policy_date or ""),
            str(p.expiry_date or ""),
            p.premium_with_gst or 0,
            p.premium_without_gst or 0,
            (p.employee.name if p.employee else ""),
            p.commission or 0,
            p.payout or 0,
            p.net_profit or 0,
            p.claim_status or "",
            p.company or "",
        ])

    return export_excel("car_policies", headers, rows)

@app.get("/export/policies/Health/csv")
def export_health_csv(db: Session = Depends(get_db)):
    policies = db.query(models.Policy).filter(models.Policy.insurance_type == "Health").all()

    headers = [
        "Name", "Product (Health)", "Company", "Fresh/Renewal",
        "Sum assured", "Premium", "Commission", "Payout", "Net Profit", "Claim",
        "Employee Name", "Policy Date", "Expiry Date"
    ]

    rows = []
    for p in policies:
        rows.append([
            p.customer_name,
            p.product or "",
            p.company or "",
            p.fresh_renewal or "",
            p.sum_assured or 0,
            (p.premium_with_gst or p.premium or 0),
            p.commission or 0,
            p.payout or 0,
            p.net_profit or 0,
            p.claim_status or "",
            (p.employee.name if p.employee else ""),
            str(p.policy_date or ""),
            str(p.expiry_date or ""),
        ])

    return export_csv("health_policies", headers, rows)


@app.get("/export/policies/Health/excel")
def export_health_excel(db: Session = Depends(get_db)):
    policies = db.query(models.Policy).filter(models.Policy.insurance_type == "Health").all()
    headers = [
        "Name", "Product (Health)", "Company", "Fresh/Renewal",
        "Sum assured", "Premium", "Commission", "Payout", "Net Profit", "Claim",
        "Employee Name", "Policy Date", "Expiry Date"
    ]
    rows = []
    for p in policies:
        rows.append([
            p.customer_name,
            p.product or "",
            p.company or "",
            p.fresh_renewal or "",
            p.sum_assured or 0,
            (p.premium_with_gst or p.premium or 0),
            p.commission or 0,
            p.payout or 0,
            p.net_profit or 0,
            p.claim_status or "",
            (p.employee.name if p.employee else ""),
            str(p.policy_date or ""),
            str(p.expiry_date or ""),
        ])
    return export_excel("health_policies", headers, rows)

@app.get("/export/policies/Term/csv")
def export_term_csv(db: Session = Depends(get_db)):
    policies = db.query(models.Policy).filter(models.Policy.insurance_type == "Term").all()

    headers = [
        "Name", "Product (Life Insurance)", "Company", "Fresh/Renewal",
        "Sum assured", "Premium", "Commission", "Payout", "Net Profit", "Claim",
        "Employee Name", "Policy Date", "Expiry Date"
    ]

    rows = []
    for p in policies:
        rows.append([
            p.customer_name,
            p.product or "",
            p.company or "",
            p.fresh_renewal or "",
            p.sum_assured or 0,
            (p.premium_with_gst or p.premium or 0),
            p.commission or 0,
            p.payout or 0,
            p.net_profit or 0,
            p.claim_status or "",
            (p.employee.name if p.employee else ""),
            str(p.policy_date or ""),
            str(p.expiry_date or ""),
        ])

    return export_csv("term_policies", headers, rows)


@app.get("/export/policies/Term/excel")
def export_term_excel(db: Session = Depends(get_db)):
    policies = db.query(models.Policy).filter(models.Policy.insurance_type == "Term").all()
    headers = [
        "Name", "Product (Life Insurance)", "Company", "Fresh/Renewal",
        "Sum assured", "Premium", "Commission", "Payout", "Net Profit", "Claim",
        "Employee Name", "Policy Date", "Expiry Date"
    ]
    rows = []
    for p in policies:
        rows.append([
            p.customer_name,
            p.product or "",
            p.company or "",
            p.fresh_renewal or "",
            p.sum_assured or 0,
            (p.premium_with_gst or p.premium or 0),
            p.commission or 0,
            p.payout or 0,
            p.net_profit or 0,
            p.claim_status or "",
            (p.employee.name if p.employee else ""),
            str(p.policy_date or ""),
            str(p.expiry_date or ""),
        ])
    return export_excel("term_policies", headers, rows)

@app.get("/export/policies/General/csv")
def export_general_csv(db: Session = Depends(get_db)):
    policies = db.query(models.Policy).filter(models.Policy.insurance_type == "General").all()

    headers = [
        "General Insurance Category (Marine/WC etc)",
        "Customer Name", "Company",
        "Policy Date", "Expiry Date",
        "Premium", "Commission", "Payout", "Net Profit", "Claim", "Employee Name"
    ]

    rows = []
    for p in policies:
        rows.append([
            p.general_category or "",
            p.customer_name,
            p.company or "",
            str(p.policy_date or ""),
            str(p.expiry_date or ""),
            (p.premium_with_gst or p.premium or 0),
            p.commission or 0,
            p.payout or 0,
            p.net_profit or 0,
            p.claim_status or "",
            (p.employee.name if p.employee else ""),
        ])

    return export_csv("general_policies", headers, rows)


@app.get("/export/policies/General/excel")
def export_general_excel(db: Session = Depends(get_db)):
    policies = db.query(models.Policy).filter(models.Policy.insurance_type == "General").all()
    headers = [
        "General Insurance Category (Marine/WC etc)",
        "Customer Name", "Company",
        "Policy Date", "Expiry Date",
        "Premium", "Commission", "Payout", "Net Profit", "Claim", "Employee Name"
    ]
    rows = []
    for p in policies:
        rows.append([
            p.general_category or "",
            p.customer_name,
            p.company or "",
            str(p.policy_date or ""),
            str(p.expiry_date or ""),
            (p.premium_with_gst or p.premium or 0),
            p.commission or 0,
            p.payout or 0,
            p.net_profit or 0,
            p.claim_status or "",
            (p.employee.name if p.employee else ""),
        ])
    return export_excel("general_policies", headers, rows)

@app.get("/export/employees/csv")
def export_employees_csv(db: Session = Depends(get_db)):
    employees = db.query(models.User).all()
    headers = ["Name", "Email", "Role"]
    rows = [[e.name, e.email, e.role] for e in employees]
    return export_csv("employees", headers, rows)


@app.get("/export/employees/excel")
def export_employees_excel(db: Session = Depends(get_db)):
    employees = db.query(models.User).all()
    headers = ["Name", "Email", "Role"]
    rows = [[e.name, e.email, e.role] for e in employees]
    return export_excel("employees", headers, rows)

@app.get("/export/attendance/csv")
def export_attendance_csv(db: Session = Depends(get_db)):
    attendance = db.query(models.Attendance).all()
    headers = [
        "Date", "Employee", "Sign In", "Sign Out", "Status",
        "Minutes Late", "Worked Minutes", "Left Early Minutes", "Overtime Minutes"
    ]
    rows = [[
        a.date,
        (a.employee.name if a.employee else ""),
        a.sign_in or "",
        a.sign_out or "",
        a.status or "",
        a.minutes_late or 0,
        a.worked_minutes or 0,
        a.left_early_minutes or 0,
        a.overtime_minutes or 0
    ] for a in attendance]
    return export_csv("attendance", headers, rows)


@app.get("/export/attendance/excel")
def export_attendance_excel(db: Session = Depends(get_db)):
    attendance = db.query(models.Attendance).all()
    headers = [
        "Date", "Employee", "Sign In", "Sign Out", "Status",
        "Minutes Late", "Worked Minutes", "Left Early Minutes", "Overtime Minutes"
    ]
    rows = [[
        a.date,
        (a.employee.name if a.employee else ""),
        a.sign_in or "",
        a.sign_out or "",
        a.status or "",
        a.minutes_late or 0,
        a.worked_minutes or 0,
        a.left_early_minutes or 0,
        a.overtime_minutes or 0
    ] for a in attendance]
    return export_excel("attendance", headers, rows)

from fastapi import Form
from fastapi.responses import HTMLResponse
from starlette.responses import RedirectResponse

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password"})

    # IMPORTANT: if old DB has plain "1234", bcrypt/pbkdf verify may fail.
    # So handle both cases safely:
    valid = False
    try:
        valid = verify_password(password, user.password)
    except Exception:
        # fallback for old plain text passwords (development only)
        valid = (password == user.password)

    if not valid:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password"})
    
    # Role restriction
    if (user.role or "").strip() not in ALLOWED_LOGIN_ROLES:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Access denied. Only Owner/Co-Owner can login."}
        )

    # set session
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    request.session["name"] = user.name

    return RedirectResponse(url="/", status_code=302)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@app.post("/policies/{policy_id}/claim-toggle")
def toggle_claim(policy_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)

    p = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not p:
        return RedirectResponse(url="/", status_code=302)

    # toggle No <-> Yes
    current = (p.claim_status or "No").strip().lower()
    p.claim_status = "Yes" if current != "yes" else "No"
    db.commit()

    # back to where you came from
    referer = request.headers.get("referer") or "/"
    return RedirectResponse(url=referer, status_code=302)

@app.post("/refresh-import")
def refresh_import(request: Request):
    user = get_current_user(request)

    # only owner / co-owner
    allowed_roles = {"owner", "co-owner"}
    if (user.get("role") or "").strip().lower() not in allowed_roles:
        return RedirectResponse(url="/", status_code=302)

    try:
        import import_csv
        import_csv.main()
    except Exception as e:
        print("Import failed:", e)

    referer = request.headers.get("referer") or "/"
    return RedirectResponse(url=referer, status_code=302)

from fastapi import HTTPException
from fastapi.responses import RedirectResponse

def require_owner_or_coowner(request: Request):
    user = get_current_user(request)
    role = (user.get("role") or "").strip().lower()
    if role not in {"owner", "co-owner"}:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user


IMPORT_TYPE_TO_STEM = {
    "employees": "employees",
    "attendance": "attendance",
    "car": "car_insurance",
    "health": "health_insurance",
    "term": "term_insurance",
    "general": "general_insurance",
}


@app.post("/import-upload")
async def import_upload(
    request: Request,
    data_type: str = Form(...),
    file: UploadFile = File(...),
    user=Depends(require_owner_or_coowner),
):
    stem = IMPORT_TYPE_TO_STEM.get(data_type)
    if not stem:
        raise HTTPException(status_code=400, detail="Unknown data type")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".csv", ".xlsx"):
        raise HTTPException(status_code=400, detail="Only .csv or .xlsx files are accepted")

    import import_csv
    dest_path = os.path.join(import_csv.INBOX_DIR, stem + ext)

    # Remove any stale sibling with the other extension so resolve_import_path()
    # doesn't pick up an old file for the same data type.
    other_ext = ".xlsx" if ext == ".csv" else ".csv"
    stale_path = os.path.join(import_csv.INBOX_DIR, stem + other_ext)
    if os.path.exists(stale_path):
        os.remove(stale_path)

    with open(dest_path, "wb") as f:
        f.write(await file.read())

    try:
        import_csv.main()
    except Exception as e:
        print("Import failed:", e)

    referer = request.headers.get("referer") or "/"
    return RedirectResponse(url=referer, status_code=302)


@app.post("/delete/policy/{policy_id}")
def delete_policy(
    policy_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_owner_or_coowner)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if policy:
        db.delete(policy)
        db.commit()

    referer = request.headers.get("referer") or "/"
    return RedirectResponse(url=referer, status_code=302)


@app.post("/delete/employee/{user_id}")
def delete_employee(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_owner_or_coowner)
):
    emp = db.query(models.User).filter(models.User.id == user_id).first()
    if emp:
        db.delete(emp)
        db.commit()

    referer = request.headers.get("referer") or "/employees"
    return RedirectResponse(url=referer, status_code=302)


@app.post("/delete/attendance/{attendance_id}")
def delete_attendance(
    attendance_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_owner_or_coowner)
):
    att = db.query(models.Attendance).filter(models.Attendance.id == attendance_id).first()
    if att:
        db.delete(att)
        db.commit()

    referer = request.headers.get("referer") or "/attendance-page"
    return RedirectResponse(url=referer, status_code=302)