import os
from platformdirs import user_data_dir

APP_NAME = "Dhanyalakshmi Insurancewala"
APP_AUTHOR = "Dhanyalakshmi Insurancewala"

# Old names used by earlier versions of database.py / import_csv.py - kept
# only so we can migrate any existing install's data into the unified path.
OLD_APP_NAME = "InsuranceERP"
OLD_APP_AUTHOR = "DhanyalakshmiInsurancewala"


def get_data_dir() -> str:
    d = user_data_dir(APP_NAME, APP_AUTHOR)
    os.makedirs(d, exist_ok=True)
    return d


def get_old_data_dir() -> str:
    return user_data_dir(OLD_APP_NAME, OLD_APP_AUTHOR)
