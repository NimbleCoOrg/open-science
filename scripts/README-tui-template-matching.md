# Tūī template-matching workflow

The tūī classification uses the same human-in-the-loop pipeline that produced the
korimako (bellbird) categories. Three stages; stage 1 is done, stage 2 is Azure's
manual pass, stage 3 is the DTW script.

## Stage 1 — PCA embedding (DONE)
`scripts/build_tui_pca.py` computed a 30-dim feature vector (13 MFCC means + 13 stds
+ centroid/bandwidth/rolloff/zcr) over the 200 tūī candidate clips in
`docs/experiments/nz-birdsong/annotation/tui/`, ran PCA→8 components, and wrote
`annotation/tui_pca_data.json`. Points are seeded with Hill & Ji (2014) rule-based
categories (rmnr/harmonic/trill/high_frequency/low_frequency/harsh) — a starting
colour only, not ground truth.

## Stage 2 — Manual clustering (AZURE)
Open the tūī clustering tool:
  https://nimblecoorg.github.io/open-science/experiments/nz-birdsong/cluster.html?species=tui

- Lasso groups of similar syllables across the linked PC panels (spike-sorting style),
  OR click individual points and use the Quick-assign buttons (Hill categories).
- Play audio + inspect spectrograms to confirm.
- Aim for a clean set of prototypes per category — even ~5–10 solid, unambiguous
  members per category is enough to seed a good DTW template (bellbird used ~12–79).
- Click **Export Clusters** → downloads `tui_clusters.json`
  (format: `{clusters:{category:[ids]}, excluded:[ids]}`).
- Send that file to Matilde.

## Stage 3 — DTW template build + classify (MATILDE runs)
```
python3 scripts/dtw_classify.py tui /path/to/tui_clusters.json
```
This builds a DTW-barycenter template (tslearn DBA) per manual category, classifies
the remaining candidates by normalised DTW distance, and writes to
`/opt/data/template_matching/tui_v2/`:
- `classification_results.json` — per-point best match, per-template scores, margin,
  confidence (high margin>0.03 / medium>0.01 / low)
- `combined_labels.json` — {id: {category, source, confidence}} for manual + matched

Low-confidence points are printed for a second review pass (re-cluster them in the
tool and re-run). The script is species-general: `dtw_classify.py kaka <export>` works
the same way once kākā has a manual pass.

## Notes
- Seed-label "agreement" printed by the script is a sanity number vs the noisy Hill
  seeds, NOT an accuracy figure. Accuracy comes from Azure's manual clusters being
  the ground truth, exactly as with bellbird.
- Point IDs are strings for tūī (`tui_0000`); the tool and script handle this.
