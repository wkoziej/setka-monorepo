# ABOUTME: Console entry point for the paternologia package.
# ABOUTME: Launches the FastAPI app via uvicorn (target of the `paternologia` script).

import uvicorn


def main() -> None:
    """Run the paternologia FastAPI server."""
    uvicorn.run("paternologia.main:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
