#!/usr/bin/env bash
cd "$(dirname "$0")"

echo "=========================================="
echo "  Dhanyalakshmi Insurancewala - Data Import"
echo "=========================================="
echo

python3 import_csv.py

echo
echo "=========================================="
echo "  Finished."
echo "=========================================="
