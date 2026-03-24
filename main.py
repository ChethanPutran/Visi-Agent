import os

# Prevent Python from writing __pycache__ folders 
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

if __name__ == "__main__":
    from src.main import run_api

    run_api()