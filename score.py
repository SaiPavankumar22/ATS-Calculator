"""Backward-compatible CLI shim. Prefer: python -m services.score <pdf_path>"""
from services.score import main

if __name__ == "__main__":
    import os
    import sys

    if len(sys.argv) < 2:
        print("Usage: python score.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' does not exist.")
        sys.exit(1)

    main(pdf_path)
