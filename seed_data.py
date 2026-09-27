# seed_data.py
from datetime import date
from database import SessionLocal, engine
import models
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Users
# admin = models.User(name="Abhishek Maheswari", email="admin@test.com", password=pwd_context.hash("1234"), role="admin")
# amit  = models.User(name="Amit", email="amit@test.com", password=pwd_context.hash("1234"), role="agent")
# rohit = models.User(name="Rohit", email="rohit@test.com", password=pwd_context.hash("1234"), role="agent")

# db.add_all([admin, amit, rohit])
db.commit()

# Policies (Car)
p1 = models.Policy(
    insurance_type="Car",
    customer_name="Rahul Sharma",
    company="HDFC ERGO",
    vehicle_type="Car",
    vehicle_model="Maruti Swift",
    vehicle_variant="VXI",
    vehicle_number="HR36AB4425",
    policy_date=date(2026, 2, 1),
    expiry_date=date(2027, 1, 31),
    premium_with_gst=18000,
    premium_without_gst=15254,
    commission=2000,
    payout=500,
    net_profit=1500,
    claim_status="No",
    # employee_id=amit.id
)

# Policies (Health)
p2 = models.Policy(
    insurance_type="Health",
    customer_name="Neha Gupta",
    product="Family Floater",
    company="Star Health",
    fresh_renewal="Renewal",
    sum_assured=500000,
    policy_date=date(2026, 2, 5),
    expiry_date=date(2027, 2, 4),
    premium_with_gst=25000,
    premium_without_gst=21186,
    commission=3500,
    payout=1000,
    net_profit=2500,
    claim_status="No",
    # employee_id=rohit.id
)

# Policies (Term)
p3 = models.Policy(
    insurance_type="Term",
    customer_name="Vikas Arora",
    product="Life Shield",
    company="SBI Life",
    fresh_renewal="Fresh",
    sum_assured=5000000,
    policy_date=date(2026, 2, 10),
    expiry_date=date(2027, 2, 9),
    premium_with_gst=12000,
    premium_without_gst=10169,
    commission=1800,
    payout=300,
    net_profit=1500,
    claim_status="Yes",
    # employee_id=amit.id
)

# Policies (General)
p4 = models.Policy(
    insurance_type="General",
    customer_name="M/s ABC Logistics",
    company="ICICI Lombard",
    general_category="Marine",
    policy_date=date(2026, 2, 12),
    expiry_date=date(2027, 2, 11),
    premium_with_gst=45000,
    premium_without_gst=38136,
    commission=6000,
    payout=1500,
    net_profit=4500,
    claim_status="No",
    # employee_id=rohit.id
)

db.add_all([p1, p2, p3, p4])
db.commit()

# Attendance dummy
# a1 = models.Attendance(employee_id=amit.id, date="2026-02-25", status="Present")
# a2 = models.Attendance(employee_id=rohit.id, date="2026-02-25", status="Late")
# db.add_all([a1, a2])
db.commit()

db.close()
print("Seed data inserted successfully.")