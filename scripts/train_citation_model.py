"""
Train and evaluate the citation-vs-warning model on the cleaned Parquet file.

    python scripts/train_citation_model.py --data data/cleaned_traffic_violations.parquet

Writes reports/citation_model.md and reports/citation_model.json.
"""

import argparse
import json
import os
import sys
import time
from dataclasses import asdict

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.citation_model import (CATEGORICAL, EXCLUDED, FLAGS, NUMERIC, RAW_COLUMNS,  # noqa: E402
                                Recalibrator, best_f1_threshold, build_frame, fold_rare, make_logreg, score,
                                time_split, top_coefficients)

TRAIN_UNTIL, VALID_YEAR, TEST_FROM = 2022, 2023, 2024


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/cleaned_traffic_violations.parquet")
    ap.add_argument("--train-sample", type=int, default=600_000,
                    help="rows sampled from the training years (0 = all)")
    ap.add_argument("--out", default="reports")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    t0 = time.time()

    df = build_frame(pd.read_parquet(args.data, columns=RAW_COLUMNS))
    train, valid, test = time_split(df, TRAIN_UNTIL, VALID_YEAR, TEST_FROM)
    if args.train_sample and len(train) > args.train_sample:
        train = train.sample(args.train_sample, random_state=args.seed)
    train, valid, test = fold_rare(train, [train, valid, test], "Charge", min_count=200)
    train, valid, test = fold_rare(train, [train, valid, test], "VehicleType", min_count=200)
    print(f"rows  train={len(train):,}  valid={len(valid):,}  test={len(test):,}")

    X = lambda d: d[CATEGORICAL + NUMERIC + FLAGS]  # noqa: E731
    results, meta = [], {}

    # 1. Baseline: predict the training citation rate for everyone.
    base_p = np.full(len(test), float(train["y"].mean()))
    results.append(score("Baseline (training citation rate)", test["y"], base_p, 0.5))

    # 2. Logistic regression: tune C and class weighting on the validation year.
    best = None
    for C in (0.1, 1.0, 10.0):
        for cw in (None, "balanced"):
            m = make_logreg(C=C, class_weight=cw).fit(X(train), train["y"])
            pv = m.predict_proba(X(valid))[:, 1]
            th = best_f1_threshold(valid["y"], pv)
            s = score("lr", valid["y"], pv, th)
            print(f"  LR C={C:<5} class_weight={cw!s:<9} valid ROC-AUC={s.roc_auc:.4f} F1={s.f1:.4f}")
            if best is None or s.roc_auc > best[0].roc_auc:
                best = (s, m, C, cw, th)
    _, lr, C, cw, th = best
    meta["logreg"] = {"C": C, "class_weight": cw, "threshold_from_valid": th}
    results.append(score(f"Logistic regression (C={C}, class_weight={cw})",
                         test["y"], lr.predict_proba(X(test))[:, 1], th))

    # 2b. Same model, probabilities recalibrated on the validation year (fixes drift in level).
    pv = lr.predict_proba(X(valid))[:, 1]
    cal = Recalibrator().fit(valid["y"], pv)
    th_cal = best_f1_threshold(valid["y"], cal.transform(pv))
    results.append(score("Logistic regression, recalibrated on 2023", test["y"],
                         cal.transform(lr.predict_proba(X(test))[:, 1]), th_cal))

    # 3. Gradient-boosted trees for comparison (same features, ordinal-coded categoricals).
    # Trees allow at most 255 categories per feature: keep the 250 most common, the rest share a code.
    cat_codes = {c: {v: i for i, v in enumerate(train[c].value_counts().index[:250])} for c in CATEGORICAL}
    def X_tree(d):  # noqa: E306
        out = d[NUMERIC + FLAGS].copy()
        for c in CATEGORICAL:
            out[c] = d[c].map(cat_codes[c]).fillna(-1).astype(int)
        return out
    gb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.1,
                                        categorical_features=[X_tree(train).columns.get_loc(c)
                                                              for c in CATEGORICAL],
                                        random_state=args.seed)
    # unseen categories (-1) are not allowed as categorical codes; map them to a spare code
    def safe(d):  # noqa: E306
        x = X_tree(d)
        for c in CATEGORICAL:
            x[c] = x[c].where(x[c] >= 0, len(cat_codes[c]))
        return x
    gb.fit(safe(train), train["y"])
    th_gb = best_f1_threshold(valid["y"], gb.predict_proba(safe(valid))[:, 1])
    results.append(score("Gradient-boosted trees", test["y"], gb.predict_proba(safe(test))[:, 1], th_gb))

    # Drift: ROC-AUC of the LR model per test year, and the citation rate each year.
    by_year = []
    for yr, part in test.groupby("Stop_Year"):
        p = lr.predict_proba(X(part))[:, 1]
        s = score("lr", part["y"], p, th)
        by_year.append({"year": int(yr), "rows": int(len(part)), "citation_rate": float(part["y"].mean()),
                        "mean_predicted": float(p.mean()),
                        "mean_predicted_recalibrated": float(cal.transform(p).mean()),
                        "roc_auc": s.roc_auc, "f1": s.f1})
    pos, neg = top_coefficients(lr, 10)

    os.makedirs(args.out, exist_ok=True)
    report = {"split": {"train": f"<= {TRAIN_UNTIL}", "valid": VALID_YEAR, "test": f">= {TEST_FROM}",
                        "rows": {"train": len(train), "valid": len(valid), "test": len(test)},
                        "test_citation_rate": float(test["y"].mean())},
              "excluded_features": EXCLUDED, "models": [asdict(r) for r in results],
              "meta": meta, "test_by_year": by_year,
              "top_citation_weights": pos, "top_warning_weights": neg,
              "seconds": round(time.time() - t0, 1)}
    with open(os.path.join(args.out, "citation_model.json"), "w") as f:
        json.dump(report, f, indent=2)
    with open(os.path.join(args.out, "citation_model.md"), "w", encoding="utf-8") as f:
        f.write(to_markdown(report))
    print(to_markdown(report))


def to_markdown(r) -> str:
    L = ["# Citation vs warning: model report", "",
         f"Train {r['split']['train']} ({r['split']['rows']['train']:,} rows), "
         f"validate {r['split']['valid']} ({r['split']['rows']['valid']:,}), "
         f"test {r['split']['test']} ({r['split']['rows']['test']:,}); "
         f"test citation rate {r['split']['test_citation_rate']:.1%}.", "",
         "| Model | ROC-AUC | PR-AUC | F1 | Precision | Recall | Brier | Threshold |",
         "|---|---|---|---|---|---|---|---|"]
    for m in r["models"]:
        L.append(f"| {m['name']} | {m['roc_auc']:.3f} | {m['pr_auc']:.3f} | {m['f1']:.3f} | "
                 f"{m['precision']:.3f} | {m['recall']:.3f} | {m['brier']:.3f} | {m['threshold']:.2f} |")
    lr = next(m for m in r["models"] if m["name"].startswith("Logistic regression (C"))
    (tn, fp), (fn, tp) = lr["confusion"]
    L += ["", f"Logistic regression confusion matrix on test: TN {tn:,}  FP {fp:,}  FN {fn:,}  TP {tp:,}", "",
          "## Drift by test year (logistic regression)", "",
          "| Year | Rows | Actual citation rate | Mean predicted | Mean predicted (recalibrated) | ROC-AUC | F1 |",
          "|---|---|---|---|---|---|---|"]
    for y in r["test_by_year"]:
        L.append(f"| {y['year']} | {y['rows']:,} | {y['citation_rate']:.1%} | {y['mean_predicted']:.1%} | "
                 f"{y['mean_predicted_recalibrated']:.1%} | {y['roc_auc']:.3f} | {y['f1']:.3f} |")
    L += ["", "## Strongest logistic-regression weights", "", "Towards citation:", ""]
    L += [f"- `{n}`: {w:+.2f}" for n, w in r["top_citation_weights"]]
    L += ["", "Towards warning:", ""] + [f"- `{n}`: {w:+.2f}" for n, w in r["top_warning_weights"]]
    L += ["", "Excluded from features: " + ", ".join(r["excluded_features"]) + "."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
