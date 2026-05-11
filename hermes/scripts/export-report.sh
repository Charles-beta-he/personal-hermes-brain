#!/bin/bash
# Export evolution report to PDF via pandoc
INPUT="${1:-~/.hermes/notes/engineering-cybernetics/evolution-dashboard.md}"
OUTPUT="${2:-~/.hermes/notes/reports/evolution-report.pdf}"
if command -v pandoc &> /dev/null; then
    pandoc "$INPUT" -o "$OUTPUT" --pdf-engine=xelatex 2>/dev/null || pandoc "$INPUT" -o "$OUTPUT"
    echo "PDF exported: $OUTPUT"
else
    echo "pandoc not installed, using HTML fallback"
    cp ~/.hermes/notes/reports/evolution-dashboard-v2.html "${OUTPUT%.pdf}.html"
    echo "HTML exported: ${OUTPUT%.pdf}.html"
fi
