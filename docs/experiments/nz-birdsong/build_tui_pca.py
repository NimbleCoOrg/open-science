#!/usr/bin/env python3
"""
Build tui_pca_data.json for the interactive PCA clustering tool (cluster.html).

Mirrors bellbird_template_optimization.py's build_pca_data output format so the
same front-end works for tui. Source = the 200 pre-extracted tui candidate clips
in annotation/tui/ (each ~800ms, syllable-centred, with Hill rule-based
auto_category in manifest.json).

Feature vector (30-dim, identical layout to bellbird):
  13 MFCC means + 13 MFCC stds + [centroid, bandwidth, rolloff, zcr]
PCA -> 8 components. Points coloured by Hill auto_category (initial seed only —
these are rule-based approximations Azure will re-cluster by ear/eye).

Fisher-style score per point: distance to own-category centroid vs nearest
other-category centroid (higher = more prototypical of its class), plus the
nearest competing category, for the tool's confidence colour mode.
"""
import json, os, glob
import numpy as np
import librosa
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

TUI_DIR = '/opt/data/open-science/docs/experiments/nz-birdsong/annotation/tui'
OUT = os.path.join(TUI_DIR, '..', 'tui_pca_data.json')
SR = 22050
N_MFCC = 13
HOP = 512

manifest = json.load(open(os.path.join(TUI_DIR, 'manifest.json')))
print(f"manifest entries: {len(manifest)}")

feats, meta = [], []
for m in manifest:
    wav = os.path.join(TUI_DIR, f"{m['id']}.wav")
    if not os.path.exists(wav):
        continue
    try:
        y, _ = librosa.load(wav, sr=SR)
    except Exception as e:
        print(f"  load fail {m['id']}: {e}")
        continue
    if len(y) < int(0.03 * SR):
        continue
    mfcc = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=N_MFCC, hop_length=HOP)
    mfcc_mean = np.mean(mfcc, axis=1)
    mfcc_std = np.std(mfcc, axis=1)
    centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=SR)))
    bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=SR)))
    rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=SR)))
    zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
    feat = np.concatenate([mfcc_mean, mfcc_std, [centroid, bandwidth, rolloff, zcr]])
    feats.append(feat)
    meta.append({
        'id': m['id'],
        'family': m.get('auto_category', 'unknown'),
        'wav': f"{m['id']}.wav",
        'recording': m.get('recording', ''),
        'start_ms': int(m.get('syl_start_ms', 0)),
        'end_ms': int(m.get('syl_end_ms', 0)),
        'duration_ms': int(m.get('duration_ms', 0)),
        'spectral': {'centroid': round(centroid, 2), 'bandwidth': round(bandwidth, 2),
                     'rolloff': round(rolloff, 2), 'zcr': round(zcr, 4)},
    })

print(f"features extracted: {len(feats)}")
X = np.array(feats)
Xs = StandardScaler().fit_transform(X)
n_comp = min(8, Xs.shape[1], Xs.shape[0])
pca = PCA(n_components=n_comp)
Xp = pca.fit_transform(Xs)
print(f"PCA {n_comp} comps, explained var: {[f'{v:.1%}' for v in pca.explained_variance_ratio_[:6]]}")

# Fisher-style prototypicality: own-centroid vs nearest-other-centroid (in PCA space)
fams = sorted({m['family'] for m in meta})
cents = {}
for fam in fams:
    idx = [i for i, m in enumerate(meta) if m['family'] == fam]
    cents[fam] = Xp[idx].mean(axis=0)

points = []
for i, m in enumerate(meta):
    own = m['family']
    d_own = np.linalg.norm(Xp[i] - cents[own])
    others = [(fam, np.linalg.norm(Xp[i] - c)) for fam, c in cents.items() if fam != own]
    others.sort(key=lambda t: t[1])
    nearest_other, d_other = (others[0] if others else ('', d_own))
    # ratio > 1 => closer to own class than to nearest other (more prototypical)
    fisher = round(float(d_other / (d_own + 1e-9)), 4)
    points.append({
        'id': m['id'], 'family': own, 'wav': m['wav'],
        'recording': m['recording'], 'start_ms': m['start_ms'], 'end_ms': m['end_ms'],
        'duration_ms': m['duration_ms'],
        'pc': [round(float(Xp[i, j]), 4) for j in range(n_comp)],
        'fisher_score': fisher, 'nearest_other': nearest_other,
        'spectral': m['spectral'],
    })

out = {
    'species': 'tui',
    'n_components': n_comp,
    'explained_variance': [round(float(v), 4) for v in pca.explained_variance_ratio_],
    'n_points': len(points),
    'families': fams,
    'family_counts': {f: sum(1 for p in points if p['family'] == f) for f in fams},
    'category_source': 'Hill & Ji (2014) rule-based auto-classification (seed for manual re-clustering)',
    'points': points,
}
json.dump(out, open(os.path.abspath(OUT), 'w'))
print(f"wrote {os.path.abspath(OUT)} : {len(points)} points, families={out['family_counts']}")
