# models.py
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    employee_code = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)

class Policy(Base):
    """
    Single table for all insurance types.
    insurance_type: Car / Health / Term / General
    """
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True)
    policy_number = Column(String, unique=True, nullable=True, index=True)

    # Core
    insurance_type = Column(String, nullable=False)  # Car / Health / Term / General
    customer_name = Column(String, nullable=False)
    company = Column(String, nullable=True)          # insurer
    product = Column(String, nullable=True)          # product plan name (health/term)
    fresh_renewal = Column(String, nullable=True)    # Fresh / Renewal

    policy_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    

    # Finance
    premium_with_gst = Column(Float, nullable=True)
    premium_without_gst = Column(Float, nullable=True)
    premium = Column(Float, nullable=True)           # Keep for backward compatibility (optional)
    commission = Column(Float, nullable=True)
    payout = Column(Float, nullable=True)            # return to customer
    net_profit = Column(Float, nullable=True)
    claim_status = Column(String, nullable=True)     # Yes/No/Approved/Rejected etc

    # Car-specific
    vehicle_type = Column(String, nullable=True)     # Car/Bike etc
    vehicle_model = Column(String, nullable=True)
    vehicle_variant = Column(String, nullable=True)  # Swift etc
    vehicle_number = Column(String, nullable=True)   # HR 36 ...

    # Health/Term-specific
    sum_assured = Column(Float, nullable=True)

    # General insurance
    general_category = Column(String, nullable=True)  # Marine, WC, etc.

    # Ownership
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    employee_code = Column(String, unique=True, nullable=True)
    employee = relationship("User")

    # Import helpers (prevents duplicates on repeated import)
    source_file = Column(String, nullable=True)
    source_row_hash = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("source_row_hash", name="uq_policy_source_row_hash"),
    )


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String)

    sign_in = Column(String, nullable=True)
    sign_out = Column(String, nullable=True)

    status = Column(String)  # Early / On Time / Late / Absent
    minutes_late = Column(Integer, nullable=True, default=0)

    worked_minutes = Column(Integer, nullable=True, default=0)
    left_early_minutes = Column(Integer, nullable=True, default=0)
    overtime_minutes = Column(Integer, nullable=True, default=0)

    employee = relationship("User")