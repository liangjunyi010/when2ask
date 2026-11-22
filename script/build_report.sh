#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../report"
latexmk -pdf -interaction=nonstopmode -halt-on-error When2Ask_Final_Report_Illustrated.tex
