#!/bin/bash
source .venv/bin/activate

for i in $(seq 1 20); do
    echo ""
    echo "=========================================="
    echo "  Run $i of 20"
    echo "=========================================="
    python generate_v5.py
done

echo ""
echo "All 20 runs complete!"
