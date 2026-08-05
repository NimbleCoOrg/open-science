# Segmentation Validation: Energy-Threshold vs AviaNZ Wavelet Denoising

---

> ## ⚠ Correction (5 August 2026) — both "winner" claims in this document are withdrawn
>
> **This file is served publicly and was never corrected when the claims it contains were
> superseded. It is being corrected now rather than edited quietly. The original text below is
> left exactly as published; nothing has been deleted.**
>
> Two comparative-superiority claims in this document are wrong. Both are withdrawn.
>
> ### 1. "Our energy-threshold method currently outperforms AviaNZ wavelet denoising" (Key Findings §1, F1=0.81 vs 0.36) — **withdrawn**
>
> That claim rests on **5 files**, of which only 4 carried ≥5 segments. It is contradicted by the
> larger sweep **already present further down this same document** (Next Steps §1, 48 test files,
> 583 ground-truth VUs), which scores:
>
> | Method | F1 (48 files) |
> |---|---|
> | AviaNZ Trained Wavelet (N=5) | **0.516** |
> | Energy-Threshold | **0.440** |
> | AviaNZ Wavelet Denoise | 0.381 |
>
> On the larger sample the energy-threshold method **loses** to AviaNZ's trained wavelet
> recogniser. The 0.81-vs-0.36 comparison also pitted our tuned pipeline against only AviaNZ's
> *denoising step*, not its detection pipeline — a limitation this document states plainly in
> Limitations §1 and which the headline claim then ignored. **We should not have published a
> superiority claim over a method we had explicitly not evaluated at full strength.**
>
> ### 2. "Winner: FIR Envelope at threshold 0.05 … dramatically outperforms all other methods" (F1=0.732) — **withdrawn**
>
> Three separate defects:
>
> - **"All other methods" meant only the classical methods in that table.** No learned segmenter
>   was in the comparison. On a held-out split scored under a single matcher, a TweetyNet-style
>   CNN reaches **F1 = 0.8577** against **FIR 0.7212** (see below). The FIR envelope is not the
>   best method available; it is the best of six classical methods on one tuning run.
> - **The reported optimum sits at the floor of the swept grid.** The FIR threshold was swept
>   `0.05–0.9` and the winner is `0.05` — the lowest value tested. An optimum at the edge of a
>   sweep means the sweep did not contain the optimum, so 0.732 is a boundary artefact, not a
>   located maximum.
> - **The threshold was chosen on the same 48 files the score is reported on.** There was no
>   validation split. 0.732 is an optimistic upper bound on that configuration, not a held-out
>   estimate — the same defect already disclosed for the CNN's 0.784 on the main dashboard page.
>
> ### What the current best-provenanced comparison actually says
>
> On split `88513a3aaa91` — **15 held-out test files, 246 ground-truth segments** — with **one
> matching criterion applied to both arms** (`IoU ≥ 0.3 OR overlap ≥ 0.5`, greedy by detected
> length) and **both operating thresholds chosen by argmax F1 on a separate validation split**:
>
> | Method | Threshold | Precision | Recall | **F1** |
> |---|---|---|---|---|
> | CNN (TweetyNet-style) | 0.45 | 0.846 | 0.870 | **0.8577** |
> | FIR envelope | 0.70 | 0.882 | 0.610 | **0.7212** |
>
> Δ F1 = **+0.137** in favour of the CNN. Paired sign test across the 15 test files: **12 favour
> the CNN, 2 favour FIR, 1 tie**; **p = 0.035 two-sided** (the value recorded in the source
> artifact, 0.0176, is one-sided).
> Source: `rescore_final_results.json`, 29 July 2026.
>
> **Read that with its caveats, which are not small:** n = 15 files, all from **one site (CUV)**
> in **one week of November 2016**; **4 of the 12 test bird IDs also appear in training** and
> **6 of 12 also appear in validation** — and because the operating threshold is an argmax on
> validation, the operating point was selected on birds that are in the test set. This is
> **within-individual, within-site, within-week** segmentation performance. **It is not evidence
> that any of these methods generalise.**
>
> ### Still true in this document
>
> The *mechanism* findings survive: wavelet denoising fragments contiguous vocalisations into many
> short segments (431 FP vs 90); sparse ground truth depresses precision for every method; and
> default AviaNZ parameters transfer badly to bellbird. Those were the useful results here. The
> rankings built on top of them were not.

---

**Date:** 2026-07-24
**Ground truth:** Koe bellbird dataset (60 WAVs, human-annotated segment timestamps)
**Circularity check:** ✅ No circularity — Koe annotations were made by humans in the Koe web tool (Fukuzawa et al. 2020), not using AviaNZ's wavelet detection.

## Method

### Ground Truth
- Source: `/opt/data/koe_bellbird/tutorial_data/songinfo.json`
- 60 bellbird song recordings from Tiritiri Matangi, Cuvier, and other NZ islands
- Each segment: (start_ms, end_ms) with syllable type labels
- Annotation tool: Koe (koe.io.ac.nz) — separate from AviaNZ
- **Caveat:** Annotations are sparse — annotators labelled specific call types, not every sound in each recording. This deflates precision for all methods.

### Method 1: Energy-Threshold (our current pipeline)
- Bandpass filter: 500–10000 Hz (Butterworth, 4th order, zero-phase)
- Frame length: 10ms, hop: 5ms
- Threshold: median(energy) × 1.0
- Minimum segment duration: 30ms
- No denoising

### Method 2: AviaNZ Wavelet Denoising + Energy Threshold
- Wavelet: dmey2, maxLevel=5
- Denoising: soft threshold, thrMultiplier=4.5 (AviaNZ defaults)
- Same energy thresholding as Method 1, applied to denoised signal
- **Note:** This is NOT AviaNZ's full detection pipeline — it uses only the denoising step, not trained wavelet filters. A fair comparison requires training a bellbird-specific recogniser.

## Results (5 files, 245 ground-truth segments)

| File | GT segs | Our P | Our R | Our F1 | AviaNZ P | AviaNZ R | AviaNZ F1 |
|---|---|---|---|---|---|---|---|
| CUV_2016_11_04_WHW010_04 | 3 | — | — | — | — | — | — |
| (4 files with ≥5 segs each) | 245 total | 0.72 | 0.93 | 0.81 | 0.26 | 0.61 | 0.36 |

**Totals:**
- Our energy: TP=228, FP=90, FN=17
- AviaNZ wavelet-denoise: TP=149, FP=431, FN=96

## Key Findings

1. **Our energy-threshold method currently outperforms AviaNZ wavelet denoising** (F1=0.81 vs 0.36).
   > **⚠ WITHDRAWN 5 August 2026** — contradicted by the 48-file sweep further down this same
   > document (Energy-Threshold F1=0.440 vs AviaNZ Trained Wavelet 0.516). See the correction at
   > the top of this file. Text retained as published.
2. **AviaNZ's wavelet denoising fragments the signal** — it produces 431 false positives vs our 90, because denoising splits contiguous vocalisations into many small segments.
3. **Both methods have high recall** on well-annotated files, but precision is limited by sparse ground truth (many "false positives" may be unlabelled real vocalisations).
4. **Per-file variation is significant** — our method ranges from F1=0.63 to F1=0.94, suggesting recording-specific effects (noise level, distance, overlap).

## Limitations

1. **AviaNZ was not evaluated at full strength.** Only the denoising step was used — the trained wavelet filter detection (the core of Priyadarshani et al. 2020) requires a species-specific recogniser trained on 5-30 labelled examples. This is the next step.
2. **Ground truth is sparse.** Koe annotators labelled specific call types, not every vocalisation. Precision is artificially low for all methods.
3. **Only 5 files tested.** Statistical significance requires a larger sample.
4. **Only bellbird.** Tūī and kākā ground truth not yet available.
5. **IoU threshold (0.3) is lenient.** Stricter matching would lower both methods' scores but the relative ranking should hold.

## Next Steps

1. ✅ **Train an AviaNZ bellbird wavelet recogniser using Koe ground truth (5-30 examples)** — DONE (2026-07-24)
   - Few-shot sweep: N=5, 10 (pool of 12 training files, 48 test files, file-level split)
   - Trained wavelet packet nodes: [18, 8, 16, 0/3, 1, 17, 7] — stable across N=5 and N=10
   - 5 training examples is sufficient — same nodes selected as N=10
   - Script: `/opt/data/train_avianz_recogniser.py`

   **Full Segmentation Comparison: 6 methods (48 Koe bellbird test files, 583 GT VUs)**

   Parameter sweep run 2026-07-24. FIR threshold swept 0.05–0.9, median clip threshold swept 0.5–7.0. Default AviaNZ parameters (FIR=0.7, median=3.0) were suboptimal for bellbird.

   | Method | P | R | F1 | TP | FP | FN |
   |---|---|---|---|---|---|---|
   | **FIR Envelope (thr=0.05)** | **0.761** | **0.705** | **0.732** | **411** | **129** | **172** |
   | AviaNZ Trained Wavelet (N=5) | 0.532 | 0.501 | 0.516 | 292 | 257 | 291 |
   | Energy-Threshold | 0.476 | 0.408 | 0.440 | 238 | 262 | 345 |
   | Median Clipping (thr=7.0) | 0.409 | 0.350 | 0.377 | 204 | 295 | 379 |
   | AviaNZ Wavelet Denoise | 0.271 | 0.640 | 0.381 | 427 | 1147 | 240 |
   | FIR Envelope (default thr=0.7) | 0.316 | 0.021 | 0.039 | 12 | 26 | 571 |
   | Median Clipping (default thr=3.0) | 0.070 | 0.012 | 0.020 | 7 | 93 | 576 |

   **Winner: FIR Envelope at threshold 0.05** (F1=0.732). With proper parameter tuning, the simple FIR envelope method dramatically outperforms all other methods — including the trained wavelet recogniser. The default AviaNZ threshold of 0.7 was far too high for bellbird; at 0.05 the FIR envelope catches 71% of VUs with 76% precision. This is the best classical method tested and requires no training data.

   > **⚠ WITHDRAWN 5 August 2026** — "all other methods" covered only the six classical methods in
   > this table; a CNN reaches F1=0.8577 vs FIR 0.7212 on a held-out split under one matcher. The
   > winning threshold 0.05 is also the **floor of the swept grid** (0.05–0.9), and it was selected
   > on the same 48 files the score is reported on. See the correction at the top of this file.
   > Text retained as published.

   **FIR threshold sweep highlights:**
   - thr=0.05: F1=0.732 (best — high precision AND recall)
   - thr=0.10: F1=0.561 (recall drops sharply)
   - thr=0.20: F1=0.418
   - thr=0.70: F1=0.039 (AviaNZ default — nearly useless for bellbird)

   **Median clipping sweep highlights:**
   - thr=7.0: F1=0.377 (best, but still well below FIR)
   - thr=5.0: F1=0.251
   - thr=3.0: F1=0.020 (AviaNZ default — too aggressive)

   **Key insight:** Parameter tuning matters more than algorithm choice for classical methods. The FIR envelope with the right threshold is simple, fast, needs no training data, and outperforms the more complex trained wavelet recogniser. Species-specific threshold optimisation is essential — default parameters from one species do not transfer to another.

   > **⚠ QUALIFIED 5 August 2026** — the narrow comparison here (FIR 0.732 > trained wavelet 0.516
   > *within this table*) still stands, and "default parameters do not transfer between species" is
   > a finding we stand by. But the 0.732 is a grid-floor optimum tuned on its own test files, so
   > the *margin* is not trustworthy, and the sentence is scoped to classical methods only. See the
   > correction at the top of this file.

   **Caveats remain:**
   - Sparse ground truth inflates FP counts for both methods (many "false positives" are likely unlabelled real VUs)
   - Only bellbird tested (tūī/kākā ground truth not available)
   - Training pool limited to 12 files (60 total, 48 held out for test) — only N=5 and N=10 could be tested
   - These numbers differ from the earlier comparison because the earlier run used a different file split and energy_factor
2. Add median-clipping and FIR segmentation methods (AviaNZ's other built-in methods)
3. Test TweetyNet and BirdNET as deep learning baselines
4. Acquire/commission dense ground truth (fully annotated recordings)
5. Expand to tūī and kākā once ground truth is available
6. Test on XC mp3 recordings (lower quality than Koe WAVs) to assess robustness

## XC Recording Availability (for sample expansion)

| Species | Currently analysed | XC A+B available | Headroom |
|---|---|---|---|
| Tūī | 116 → 232 (expanded) | 232 | 0 (all used) |
| Bellbird | 47 → 94 (expanded) | 94 | 0 (all used) |
| Kākā | 25 → 47 (expanded) | 47 | 0 (all used) |

All available A+B quality XC recordings have been downloaded and processed. No more headroom from XC without lowering quality threshold below B.
