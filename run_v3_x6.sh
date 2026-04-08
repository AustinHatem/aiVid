#!/bin/bash
source .venv/bin/activate

for i in $(seq 1 10); do
    echo ""
    echo "=========================================="
    echo "  Run $i of 10"
    echo "=========================================="
    python generate_v3.py
done

echo ""
echo "All 10 runs complete!"
