import traceback

try:
    import app.main  # noqa: F401
    print("IMPORT_OK")
except Exception:
    traceback.print_exc()
    raise
