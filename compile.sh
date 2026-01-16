#!/bin/bash

# LaTeX compilation script for the molecular AutoML paper
# This script compiles the paper.tex document with proper bibliography processing

export PATH=~/texlive/bin/x86_64-linux:$PATH

echo "Compiling LaTeX document..."

# First compilation
pdflatex -interaction=nonstopmode paper.tex

# Bibliography processing
bibtex paper

# Second compilation to resolve references
pdflatex -interaction=nonstopmode paper.tex

# Third compilation to finalize cross-references
pdflatex -interaction=nonstopmode paper.tex

echo "Compilation complete. Output: paper.pdf"
