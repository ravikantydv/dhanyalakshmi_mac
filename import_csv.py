import csv
import os
import hashlib
from datetime import datetime
from datetime import date as dt_date, time as dt_time
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from openpyxl import load_workbook
from app_paths import get_data_dir

from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)

DATA_DIR = get_data_dir()
INBOX_DIR = os.path.join(DATA_DIR, "import_inbox")
os.makedirs(INBOX_DIR, exist_ok=True)

ATTENDANCE_FILE = "attendance.csv"

POLICY_FILES = {
    "car_insurance.csv": "Car",
    "health_insurance.csv": "Health",
    "term_insurance.csv": "Term",
    "general_insurance.csv": "General",
}

EMPLOYEE_FILE = "employees.csv"

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def parse_date(val: str):
    if not val:
        return None
    val = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            pass
    return None


def parse_time(val: str):
    if not val:
        return None
    s = str(val).strip()
    if s == "":
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            pass
    return None


def to_float(val):
    if val is None:
        return None
    s = str(val).strip().replace(",", "")
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def normalize(s: str):
    return (s or "").strip().lower()


def iter_rows_from_csv(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        yield from csv.DictReader(f)


def iter_rows_from_xlsx(path):
    """Read an .xlsx sheet and normalize every cell to a string, matching
    csv.DictReader's contract, so downstream parsing (parse_date, to_float,
    plain .strip() calls) doesn't need to know which format the file came in."""
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip() if h is not None else "" for h in next(rows_iter, [])]
    for raw_row in rows_iter:
        row = {}
        for h, v in zip(headers, raw_row):
            if not h:
                continue
            if v is None:
                row[h] = ""
            elif isinstance(v, float) and v.is_integer():
                row[h] = str(int(v))
            elif isinstance(v, (datetime, dt_date)):
                row[h] = v.strftime("%Y-%m-%d")
            elif isinstance(v, dt_time):
                row[h] = v.strftime("%H:%M")
            else:
                row[h] = str(v)
        yield row
    wb.close()


def iter_rows(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xlsx":
        yield from iter_rows_from_xlsx(path)
    else:
        yield from iter_rows_from_csv(path)


def resolve_import_path(base_filename: str):
    """base_filename is one of the canonical *.csv names below; accept a
    same-named .xlsx too so users can drop/upload either format."""
    stem = os.path.splitext(base_filename)[0]
    for ext in (".csv", ".xlsx"):
        candidate = os.path.join(INBOX_DIR, stem + ext)
        if os.path.exists(candidate):
            return candidate
    return None


def get_employee_id(db, employee_name: str):
    if not employee_name:
        return None

    name_norm = normalize(employee_name)
    users = db.query(models.User).all()
    for u in users:
        if normalize(u.name) == name_norm:
            return u.id
    return None


def compute_gst_fields(p_with, p_without, gst_rate=0.18):
    if p_with is not None and (p_without is None or p_without == 0):
        return p_with, round(p_with / (1 + gst_rate), 2)
    if p_without is not None and (p_with is None or p_with == 0):
        return round(p_without * (1 + gst_rate), 2), p_without
    return p_with, p_without


def compute_net_profit(commission, payout, net_profit):
    if net_profit is None:
        c = commission or 0
        p = payout or 0
        return round(c - p, 2)
    return net_profit


def row_hash(policy_type: str, row: dict):
    key = [
        policy_type,
        row.get("Customer name", "") or row.get("Customer Name", "") or row.get("Name", ""),
        row.get("Policy Date", ""),
        row.get("Expiry Date", ""),
        row.get("Premium with GST", "") or row.get("Premium", ""),
        row.get("Car number (HR 36 etc)", ""),
        row.get("Company", ""),
    ]
    raw = "||".join([str(x).strip().lower() for x in key])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def compute_attendance_status(sign_in: dt_time | None, office_start="10:00", late_grace_min=10):
    """
    office_start=10:00, grace=10 minutes
    - Absent: no sign_in
    - Early: before 10:00
    - On Time: 10:00 to 10:10
    - Late: after 10:10
    """
    start_t = parse_time(office_start)
    if sign_in is None:
        return "Absent", None

    sign_in_dt = datetime.combine(dt_date.today(), sign_in)
    start_dt = datetime.combine(dt_date.today(), start_t)

    minutes_late = int((sign_in_dt - start_dt).total_seconds() // 60)

    if minutes_late < 0:
        return "Early", 0
    if minutes_late <= late_grace_min:
        return "On Time", 0
    return "Late", minutes_late


def compute_work_minutes(sign_in: dt_time | None, sign_out: dt_time | None):
    if not sign_in or not sign_out:
        return 0
    a = datetime.combine(dt_date.today(), sign_in)
    b = datetime.combine(dt_date.today(), sign_out)
    mins = int((b - a).total_seconds() // 60)
    if mins < 0:
        return 0
    return mins


def compute_out_time_metrics(sign_out: dt_time | None, office_end="19:00"):
    end_t = parse_time(office_end)
    if sign_out is None:
        return 0, 0  # left_early, overtime

    out_dt = datetime.combine(dt_date.today(), sign_out)
    end_dt = datetime.combine(dt_date.today(), end_t)

    diff = int((out_dt - end_dt).total_seconds() // 60)

    if diff < 0:
        return abs(diff), 0
    elif diff > 0:
        return 0, diff
    return 0, 0


def import_employees(db, filename: str):
    path = resolve_import_path(filename)
    if not path:
        return 0, 0

    inserted, skipped = 0, 0

    for row in iter_rows(path):
        name = (row.get("Name") or "").strip()
        role = (row.get("Role") or "agent").strip()
        code = (row.get("Employee code") or "").strip()
        email = (row.get("Email") or f"{name.replace(' ', '').lower()}@company.local").strip()

        if not name:
            skipped += 1
            continue

        exists = db.query(models.User).filter(models.User.email == email).first()
        if exists:
            skipped += 1
            continue

        user = models.User(
            name=name,
            role=role,
            employee_code=code or None,
            email=email,
            password=pwd_context.hash("1234"),
        )
        db.add(user)
        db.commit()
        inserted += 1

    return inserted, skipped


def import_policy_file(db, filename: str, insurance_type: str):
    path = resolve_import_path(filename)
    if not path:
        return 0, 0, 0  # inserted, updated, skipped

    inserted, updated, skipped = 0, 0, 0

    for row in iter_rows(path):
        policy_number = (row.get("Policy Number") or row.get("Policy No") or row.get("Policy_Number") or "").strip()

        customer = (
            (row.get("Customer name") or row.get("Customer Name") or row.get("Name") or "")
            .strip()
        )

        if not customer:
            skipped += 1
            continue

        employee_name = (row.get("Employee Name") or row.get("Employee") or "").strip()
        emp_id = get_employee_id(db, employee_name)

        p_with = to_float(row.get("Premium with GST") or row.get("Premium"))
        p_without = to_float(row.get("Premium without GST"))
        p_with, p_without = compute_gst_fields(p_with, p_without)

        commission = to_float(row.get("Comission") or row.get("Commision") or row.get("Commission"))
        payout = to_float(row.get("Payout (Return to customer)") or row.get("Payout"))
        net_profit = to_float(row.get("Net Profit"))
        net_profit = compute_net_profit(commission, payout, net_profit)

        existing = None
        if policy_number:
            existing = db.query(models.Policy).filter(models.Policy.policy_number == policy_number).first()

        if existing:
            # UPDATE
            existing.insurance_type = insurance_type
            existing.customer_name = customer
            existing.company = (row.get("Company") or "").strip() or None
            existing.product = (row.get("Product (Health)") or row.get("Product (Life Insurance)") or row.get("Product") or "").strip() or None
            existing.fresh_renewal = (row.get("Fresh/Renewal") or "").strip() or None
            existing.sum_assured = to_float(row.get("Sum assured"))

            existing.policy_date = parse_date(row.get("Policy Date"))
            existing.expiry_date = parse_date(row.get("Expiry Date"))

            existing.premium_with_gst = p_with
            existing.premium_without_gst = p_without

            existing.commission = commission
            existing.payout = payout
            existing.net_profit = net_profit
            existing.claim_status = (row.get("Claim") or "").strip() or None

            existing.vehicle_model = (row.get("Car type/Model") or row.get("Car type") or "").strip() or None
            existing.vehicle_variant = (row.get("Variant/Swift etc") or row.get("Variant") or "").strip() or None
            existing.vehicle_number = (row.get("Car number (HR 36 etc)") or row.get("Car number") or "").strip() or None

            existing.general_category = (row.get("General Insurance") or row.get("Marine, WC etc") or row.get("Category") or "").strip() or None

            existing.employee_id = emp_id
            existing.source_file = filename

            db.commit()
            updated += 1
            continue

        # INSERT
        policy = models.Policy(
            policy_number=policy_number or None,
            insurance_type=insurance_type,
            customer_name=customer,
            company=(row.get("Company") or "").strip() or None,
            product=(row.get("Product (Health)") or row.get("Product (Life Insurance)") or row.get("Product") or "").strip() or None,
            fresh_renewal=(row.get("Fresh/Renewal") or "").strip() or None,
            sum_assured=to_float(row.get("Sum assured")),

            policy_date=parse_date(row.get("Policy Date")),
            expiry_date=parse_date(row.get("Expiry Date")),

            premium_with_gst=p_with,
            premium_without_gst=p_without,

            commission=commission,
            payout=payout,
            net_profit=net_profit,
            claim_status=(row.get("Claim") or "").strip() or None,

            vehicle_model=(row.get("Car type/Model") or row.get("Car type") or "").strip() or None,
            vehicle_variant=(row.get("Variant/Swift etc") or row.get("Variant") or "").strip() or None,
            vehicle_number=(row.get("Car number (HR 36 etc)") or row.get("Car number") or "").strip() or None,

            general_category=(row.get("General Insurance") or row.get("Marine, WC etc") or row.get("Category") or "").strip() or None,

            employee_id=emp_id,
            source_file=filename,
            source_row_hash=row_hash(insurance_type, row)
        )

        db.add(policy)
        try:
            db.commit()
            inserted += 1
        except IntegrityError:
            db.rollback()
            skipped += 1

    return inserted, updated, skipped

def import_attendance(db, filename: str):
    path = resolve_import_path(filename)
    if not path:
        return 0, 0

    inserted, skipped = 0, 0
    imported_dates = set()
    present_emp_date = set()  # (employee_id, date_str)

    for row in iter_rows(path):
        name = (row.get("Name") or "").strip()
        d = parse_date(row.get("Date"))

        sign_in_t = parse_time(row.get("Sign in time") or row.get("Sign In Time"))
        sign_out_t = parse_time(row.get("Sign out time") or row.get("Sign Out Time"))

        if not name or not d:
            skipped += 1
            continue

        date_str = str(d)
        imported_dates.add(date_str)

        emp_id = get_employee_id(db, name)
        if not emp_id:
            skipped += 1
            continue

        status, minutes_late = compute_attendance_status(
            sign_in_t, office_start="10:00", late_grace_min=10
        )
        worked = compute_work_minutes(sign_in_t, sign_out_t)
        left_early, overtime = compute_out_time_metrics(sign_out_t, office_end="19:00")

        exists = db.query(models.Attendance).filter(
            models.Attendance.employee_id == emp_id,
            models.Attendance.date == date_str
        ).first()

        if exists:
            # Update existing row (especially useful if it was auto-marked Absent earlier)
            exists.sign_in = (sign_in_t.strftime("%H:%M") if sign_in_t else None)
            exists.sign_out = (sign_out_t.strftime("%H:%M") if sign_out_t else None)
            exists.status = status
            exists.minutes_late = minutes_late or 0
            exists.worked_minutes = worked
            exists.left_early_minutes = left_early
            exists.overtime_minutes = overtime
            db.commit()

            present_emp_date.add((emp_id, date_str))
            inserted += 1
            continue

        att = models.Attendance(
            employee_id=emp_id,
            date=date_str,
            sign_in=(sign_in_t.strftime("%H:%M") if sign_in_t else None),
            sign_out=(sign_out_t.strftime("%H:%M") if sign_out_t else None),
            status=status,
            minutes_late=minutes_late or 0,
            worked_minutes=worked,
            left_early_minutes=left_early,
            overtime_minutes=overtime
        )
        db.add(att)
        db.commit()
        inserted += 1

        present_emp_date.add((emp_id, date_str))

    # AUTO-ABSENT
    if imported_dates:
        all_employees = db.query(models.User).all()

        for date_str in imported_dates:
            for emp in all_employees:
                key = (emp.id, date_str)
                if key in present_emp_date:
                    continue

                exists = db.query(models.Attendance).filter(
                    models.Attendance.employee_id == emp.id,
                    models.Attendance.date == date_str
                ).first()
                if exists:
                    continue

                absent = models.Attendance(
                    employee_id=emp.id,
                    date=date_str,
                    sign_in=None,
                    sign_out=None,
                    status="Absent",
                    minutes_late=0,
                    worked_minutes=0,
                    left_early_minutes=0,
                    overtime_minutes=0
                )
                db.add(absent)
                inserted += 1

        db.commit()

    return inserted, skipped


def main():
    os.makedirs(INBOX_DIR, exist_ok=True)

    db = SessionLocal()

    # 1) Employees first
    emp_ins, emp_skip = import_employees(db, EMPLOYEE_FILE)
    print(f"{EMPLOYEE_FILE}: inserted={emp_ins}, skipped={emp_skip}")

    # 2) Attendance
    att_ins, att_skip = import_attendance(db, ATTENDANCE_FILE)
    print(f"{ATTENDANCE_FILE}: inserted={att_ins}, skipped={att_skip}")

    # 3) Policies
    for file_name, policy_type in POLICY_FILES.items():
        ins, upd, skip = import_policy_file(db, file_name, policy_type)
        print(f"{file_name}: inserted={ins}, updated={upd}, skipped={skip}")

    db.close()
    print(f"\nDONE. Drop files in: {INBOX_DIR}")


if __name__ == "__main__":
    main()