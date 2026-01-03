import os

from backend.main import app


def main():
    print("Starting LLM Council API...")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
