import os
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app_paths import get_data_dir, get_old_data_dir

# Folder where DB will be stored (cross platform)
data_dir = get_data_dir()

DB_PATH = os.path.join(data_dir, "insurance.db")

# Migrate a DB created under the old app-data folder name, if this is an
# upgrade from a version that used mismatched APP_NAME/APP_AUTHOR values.
if not os.path.exists(DB_PATH):
    old_db_path = os.path.join(get_old_data_dir(), "insurance.db")
    if os.path.exists(old_db_path):
        shutil.copy2(old_db_path, DB_PATH)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# HIS LINE WAS MISSING
Base = declarative_base()