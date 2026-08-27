from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[3]
M=ROOT/'manuscripts/manuscript_01/author_review/manuscript'
for cmd in [['pdflatex','-interaction=nonstopmode','-halt-on-error','manuscript_author_review.tex'],['biber','manuscript_author_review'],['pdflatex','-interaction=nonstopmode','-halt-on-error','manuscript_author_review.tex'],['pdflatex','-interaction=nonstopmode','-halt-on-error','manuscript_author_review.tex']]:
    subprocess.run(cmd,cwd=M,check=True)
print('MANUSCRIPT1_AUTHOR_REVIEW_BUILD_PASS')
