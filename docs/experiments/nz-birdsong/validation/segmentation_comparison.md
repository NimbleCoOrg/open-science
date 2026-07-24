# Segmentation Validation: Energy-Threshold vs AviaNZ Wavelet Denoising

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

   **Results: Energy-Threshold vs AviaNZ Trained Wavelet Recogniser (48 Koe bellbird test files, 583 GT VUs)**

   | Metric | Energy-Threshold | AviaNZ Trained (N=5) | AviaNZ Trained (N=10) |
   |---|---|---|---|
   | Precision | 0.476 | **0.532** | 0.532 |
   | Recall | 0.408 | **0.501** | 0.501 |
   | F1 | 0.440 | **0.516** | 0.516 |
   | TP | 238 | 292 | 292 |
   | FP | 262 | 257 | 257 |
   | FN | 345 | 291 | 291 |

   **Key finding:** The trained AviaNZ wavelet recogniser outperforms our energy-threshold method on all three metrics (F1: 0.516 vs 0.440). The wavelet packet reconstruction from learned discriminative nodes captures bellbird vocalisation structure better than simple energy thresholding. 5 training examples is sufficient for node selection.

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
