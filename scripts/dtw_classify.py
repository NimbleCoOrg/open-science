#!/usr/bin/env python3
"""
Species-general DTW template-matching classifier.

Reads a cluster export from cluster.html (format: {clusters:{cat:[ids]}, excluded:[ids]}),
builds DTW-barycenter templates (tslearn DBA) from the manually-clustered clips, then
classifies the remaining (unclustered, non-excluded) candidate clips against those
templates. Mirrors the bellbird v2 pipeline (dtw_classify_v2.py) but parametrised by
species so it works for tui / kaka / bellbird.

USAGE:
  python3 dtw_classify.py <species> <clusters_export.json>
  e.g. python3 dtw_classify.py tui /opt/data/tui_clusters_azure.json

Assets are read from the deployed annotation dir for that species:
  docs/experiments/nz-birdsong/annotation/<species>/<id>.wav
PCA data (for original-category comparison + full candidate list) from:
  docs/experiments/nz-birdsong/annotation/<species>_pca_data.json
Outputs to /opt/data/template_matching/<species>_v2/:
  classification_results.json  — per-point matches, scores, confidence
  combined_labels.json         — {id: {category, source, confidence, ...}} for all points
"""
import json, os, sys
import numpy as np
import librosa
from tslearn.metrics import dtw as tslearn_dtw
from tslearn.barycenters import dtw_barycenter_averaging
from tslearn.utils import to_time_series, to_time_series_dataset
from collections import Counter

if len(sys.argv) < 3:
    print(__doc__); sys.exit(1)

SPECIES = sys.argv[1].lower()
CLUSTERS_FILE = sys.argv[2]

# Use repo-relative paths so the script works both locally and in GitHub Actions
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
BASE = os.path.join(REPO_ROOT, 'docs', 'experiments', 'nz-birdsong', 'annotation')
PCA_DATA = os.path.join(BASE, f'{SPECIES}_pca_data.json') if SPECIES != 'bellbird' else os.path.join(BASE, 'bellbird_pca_data.json')
CLIPS_DIR = os.path.join(BASE, SPECIES)
OUTPUT_DIR = os.path.join(REPO_ROOT, 'template_matching', f'{SPECIES}_v2')
os.makedirs(OUTPUT_DIR, exist_ok=True)

SR = 22050
N_MFCC = 13
MIN_MEMBERS = 2          # need >=2 clips to average a template
# Fewer templates than this and a margin-based confidence tier is
# meaningless (see the guard below).
MIN_TEMPLATES_FOR_CONFIDENCE = 2
# Reported instead of a high/medium/low tier when the tier cannot mean
# anything. 'high' on a one-class classifier is not a weaker claim, it is
# a false one.
SINGLE_TEMPLATE_CONFIDENCE = "unranked"
# Pins DBA's random initialisation so published labels are regenerable.
DBA_RANDOM_STATE = 42
HIGH_MARGIN = 0.03       # confidence thresholds (same calibration as bellbird v2)
MED_MARGIN = 0.01

# ------------------------------------------------------------
print(f"Species: {SPECIES}")
print(f"Loading PCA data: {PCA_DATA}")
with open(PCA_DATA) as f:
    pca_data = json.load(f)
with open(CLUSTERS_FILE) as f:
    cluster_data = json.load(f)

point_map = {p['id']: p for p in pca_data['points']}
clusters = cluster_data['clusters']
excluded = set(cluster_data.get('excluded', []))
clustered_ids = set()
for ids in clusters.values():
    clustered_ids.update(ids)
unclustered_ids = [p['id'] for p in pca_data['points']
                   if p['id'] not in clustered_ids and p['id'] not in excluded]

print(f"  Categories: {list(clusters.keys())}")
print(f"  Clustered (ground truth): {len(clustered_ids)}, Excluded: {len(excluded)}, "
      f"To classify: {len(unclustered_ids)}")

if not clustered_ids:
    print("\nNo manual clusters in the export — nothing to build templates from. "
          "Do a clustering pass in cluster.html?species=%s and Export first." % SPECIES)
    sys.exit(1)

# ------------------------------------------------------------
def load_mfcc(pid):
    wav_path = os.path.join(CLIPS_DIR, f"{pid}.wav")
    if not os.path.exists(wav_path):
        return None
    try:
        y, _ = librosa.load(wav_path, sr=SR)
        if len(y) < 200:
            return None
        hop = min(256, max(64, len(y) // 8))
        mfcc = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=N_MFCC, hop_length=hop, fmax=10000)
        return mfcc.T  # (T, 13)
    except Exception:
        return None

# ------------------------------------------------------------
print("\n" + "=" * 60)
print("BUILDING DTW BARYCENTER TEMPLATES (tslearn DBA)")
print("=" * 60)

templates = {}
for cat_name, cat_ids in clusters.items():
    mfccs, valid_ids = [], []
    for pid in cat_ids:
        m = load_mfcc(pid)
        if m is not None and m.shape[0] >= 2:
            mfccs.append(m); valid_ids.append(pid)
    if len(mfccs) < MIN_MEMBERS:
        print(f"  {cat_name}: only {len(mfccs)} valid clip(s) — skipping (need >={MIN_MEMBERS})")
        continue
    dataset = to_time_series_dataset(mfccs)
    # random_state pins DBA's random init: without it the published labels
    # cannot be regenerated (two runs over the same clusters gave different
    # score distributions). max_iter was 5 against tslearn's default of 30,
    # so the barycenters were very likely not converged.
    barycenter = dtw_barycenter_averaging(dataset, n_init=1, max_iter=30,
                                          random_state=DBA_RANDOM_STATE,
                                          verbose=False)
    templates[cat_name] = {'barycenter': barycenter, 'members': valid_ids, 'n_members': len(valid_ids)}
    print(f"  {cat_name}: {len(valid_ids)} clips → template {barycenter.shape}")

if not templates:
    print("\nNo category had >=2 valid clips — cannot build templates. "
          "Cluster a few more points per category and re-export.")
    sys.exit(1)

# A margin-based confidence tier needs a runner-up to take a margin against.
# With a single template `second` is 0.0, so margin == score and every clip
# reads as confident — which is exactly how 1796/1797 kaka clips were published
# in one category with 1265 of them labelled "High confidence". Refuse rather
# than emit a tier that measures nothing.
if len(templates) < MIN_TEMPLATES_FOR_CONFIDENCE:
    print(f"\nERROR: only {len(templates)} template(s) built "
          f"({', '.join(sorted(templates))}).")
    print("  Confidence tiers are a margin against the runner-up, so with fewer "
          f"than {MIN_TEMPLATES_FOR_CONFIDENCE} templates every clip would be "
          "reported as high-confidence regardless of fit.")
    print("  Cluster at least one more category by hand and re-export, or run "
          "with --allow-unranked to emit assignments with "
          f"confidence='{SINGLE_TEMPLATE_CONFIDENCE}'.")
    if "--allow-unranked" not in sys.argv:
        sys.exit(2)
    print("  --allow-unranked given: continuing with unranked confidence.")
print(f"\n  Built {len(templates)} templates")

# ------------------------------------------------------------
print("\n" + "=" * 60)
print(f"CLASSIFYING {len(unclustered_ids)} UNCLUSTERED CANDIDATES")
print("=" * 60)

def _confidence_tier(margin, n_templates):
    """Margin-based tier, or "unranked" when a margin cannot mean anything.

    With a single template the runner-up score is 0.0, so margin == score and
    every clip would be graded "high" no matter how poorly it fits. Reporting
    "unranked" is the honest output; it is not a weaker claim than "high", it is
    the absence of a claim we are not entitled to make.
    """
    if n_templates < MIN_TEMPLATES_FOR_CONFIDENCE:
        return SINGLE_TEMPLATE_CONFIDENCE
    if margin > HIGH_MARGIN:
        return 'high'
    return 'medium' if margin > MED_MARGIN else 'low'


results, skipped = [], 0
for i, pid in enumerate(unclustered_ids):
    mfcc = load_mfcc(pid)
    if mfcc is None or mfcc.shape[0] < 2:
        skipped += 1; continue
    cand_ts = to_time_series(mfcc)
    scores = {}
    for cat_name, tmpl in templates.items():
        dist = tslearn_dtw(cand_ts, tmpl['barycenter'])
        norm = np.sqrt(cand_ts.shape[0] * tmpl['barycenter'].shape[0])
        similarity = float(np.exp(-(dist / norm) / 15.0))
        scores[cat_name] = round(similarity, 4)
    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_cat, best_score = sorted_cats[0]
    second = sorted_cats[1][1] if len(sorted_cats) > 1 else 0.0
    margin = best_score - second
    results.append({
        'id': pid,
        'original_family': point_map.get(pid, {}).get('family', 'unknown'),
        'best_match': best_cat,
        'best_score': round(float(best_score), 4),
        'margin': round(float(margin), 4),
        'scores': scores,
        'confidence': _confidence_tier(margin, len(templates)),
    })
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(unclustered_ids)} ({skipped} skipped)...")

print(f"\n  Classified: {len(results)}, Skipped (missing/too short): {skipped}")

# ------------------------------------------------------------
high = [r for r in results if r['confidence'] == 'high']
medium = [r for r in results if r['confidence'] == 'medium']
low = [r for r in results if r['confidence'] == 'low']
n = max(len(results), 1)
print("\n  Confidence:")
print(f"    High:   {len(high)} ({100*len(high)/n:.1f}%)")
print(f"    Medium: {len(medium)} ({100*len(medium)/n:.1f}%)")
print(f"    Low:    {len(low)} ({100*len(low)/n:.1f}%)")
print("\n  Distribution (all):")
for cat, cnt in Counter(r['best_match'] for r in results).most_common():
    print(f"    {cat}: {cnt}")
if results:
    agree = sum(1 for r in results if r['best_match'] == r['original_family'])
    print(f"\n  Seed-label agreement (sanity, not accuracy): {agree}/{len(results)} ({100*agree/len(results):.1f}%)")

# ------------------------------------------------------------
output = {
    'pipeline': 'dtw_barycenter_tslearn',
    'species': SPECIES,
    'n_templates': len(templates),
    'n_classified': len(results),
    'confidence_counts': {'high': len(high), 'medium': len(medium),
                          'low': len(low),
                          SINGLE_TEMPLATE_CONFIDENCE: len(
                              [r for r in results if r['confidence']
                               == SINGLE_TEMPLATE_CONFIDENCE])},
    'template_members': {k: v['n_members'] for k, v in templates.items()},
    'results': results,
    'manual_clusters': clusters,
    'excluded': list(excluded),
}
with open(os.path.join(OUTPUT_DIR, 'classification_results.json'), 'w') as f:
    json.dump(output, f, indent=2)

combined = {}
for cat, ids in clusters.items():
    for pid in ids:
        combined[str(pid)] = {'category': cat, 'source': 'manual', 'confidence': 'ground_truth'}
for r in results:
    combined[str(r['id'])] = {'category': r['best_match'], 'source': 'template_match',
                              'confidence': r['confidence'], 'score': r['best_score'], 'margin': r['margin']}
with open(os.path.join(OUTPUT_DIR, 'combined_labels.json'), 'w') as f:
    json.dump(combined, f, indent=2)
print(f"\n  Saved → {OUTPUT_DIR}/{{classification_results,combined_labels}}.json")

print(f"\n{'='*60}\nFOR REVIEW: {len(low)} low-confidence points (smallest margins first)\n{'='*60}")
for r in sorted(low, key=lambda x: x['margin'])[:15]:
    top3 = sorted(r['scores'].items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"  {r['id']} (seed: {r['original_family']}) → {r['best_match']} "
          f"(score={r['best_score']:.3f}, margin={r['margin']:.4f}) | "
          f"{', '.join(f'{c}={s:.3f}' for c,s in top3)}")
print("\nDone!")
