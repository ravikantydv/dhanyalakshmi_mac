import os
import sys
import time
import threading
import webbrowser
import traceback
import uvicorn
from app_paths import get_data_dir

PORT = 8010

def get_log_path():
    return os.path.join(get_data_dir(), "desktop_app.log")

def log(msg: str):
    with open(get_log_path(), "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def ensure_std_streams():
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

def run_import():
    try:
        import import_csv
        log("Starting CSV import...")
        import_csv.main()
        log("CSV import finished.")
    except Exception:
        log("CSV import failed:")
        log(traceback.format_exc())

def open_browser():
    time.sleep(2)
    url = f"http://127.0.0.1:{PORT}"
    log(f"Opening browser: {url}")
    webbrowser.open(url)

def main():
    try:
        ensure_std_streams()
        log("App starting...")
        run_import()

        from main import app

        threading.Thread(target=open_browser, daemon=True).start()

        log(f"Starting uvicorn on port {PORT}...")
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=PORT,
            reload=False,
            log_config=None,
            access_log=False,
            log_level="info",
        )
    except Exception:
        log("App crashed:")
        log(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()