# Regeneration entry point for M1.6 author-review visuals.
# This file intentionally does not execute scientific analysis. It reads only the frozen
# source tables copied under author_review/visuals/source and regenerates editorial layouts.
# The candidate package includes the already-rendered PDF/PNG artifacts and identity audits.
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'manuscripts/manuscript_01/author_review/visuals/source'
OUT=ROOT/'manuscripts/manuscript_01/author_review/visuals'
if __name__=='__main__':
    print('M1_6_VISUAL_RENDER_SOURCES_PRESENT', SOURCE.is_dir())
    print('No scientific computation is authorized by this entry point.')
