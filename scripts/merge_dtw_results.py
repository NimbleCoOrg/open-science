#!/usr/bin/env python3
"""
Merge DTW classification results (from dtw_classify.py) back into the deployed
PCA JSON that cluster.html reads, so the Confidence tab and Review list populate.

USAGE:
  python3 merge_dtw_results.py <species>

Reads:
  /opt/data/template_matching/<species>_v2/combined_labels.json
    {id: {category, source, confidence, score?, margin?}}
Writes (in place):
  docs/experiments/nz-birdsong/annotation/<species>_pca_data.json
    Adds/updates per point: assigned_category, assignment_source,
    assignment_confidence, assignment_score, assignment_margin
Manual (ground-truth) points are marked source='manual', confidence='ground_truth'
per the existing convention (matches bellbird's schema exactly) and are never
overwritten by a later re-run unless they're re-exported as manual again.
"""
import json, os, sys

if len(sys.argv) < 2:
    print(__doc__); sys.exit(1)

SPECIES = sys.argv[1].lower()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
BASE = os.path.join(REPO_ROOT, 'docs', 'experiments', 'nz-birdsong', 'annotation')
PCA_PATH = os.path.join(BASE, f'{SPECIES}_pca_data.json')
LABELS_PATH = os.path.join(REPO_ROOT, 'template_matching', f'{SPECIES}_v2', 'combined_labels.json')

with open(PCA_PATH) as f:
    pca = json.load(f)
with open(LABELS_PATH) as f:
    labels = json.load(f)

updated = 0
for p in pca['points']:
    lbl = labels.get(str(p['id']))
    if not lbl:
        continue
    p['assigned_category'] = lbl['category']
    p['assignment_source'] = lbl['source']
    p['assignment_confidence'] = lbl['confidence']
    if 'score' in lbl:
        p['assignment_score'] = lbl['score']
    if 'margin' in lbl:
        p['assignment_margin'] = lbl['margin']
    updated += 1

print(f"{SPECIES}: updated {updated}/{len(pca['points'])} points from {LABELS_PATH}")

with open(PCA_PATH, 'w') as f:
    json.dump(pca, f)
print(f"Wrote {PCA_PATH}")
