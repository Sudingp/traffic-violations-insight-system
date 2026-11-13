import numpy as np
import pandas as pd
import pytest

from src.citation_model import (CATEGORICAL, EXCLUDED, FLAGS, NUMERIC, Recalibrator,
                                best_f1_threshold, build_frame, fold_rare, make_logreg, score,
                                time_split, top_coefficients)


def raw_rows(n=2000, seed=0, citation_rate_by_year=None):
    """Small frame in the cleaned-Parquet shape. DUI charges are mostly citations,
    equipment charges mostly warnings, so a working model must find that signal."""
    rng = np.random.default_rng(seed)
    years = rng.choice([2019, 2020, 2021, 2022, 2023, 2024], n)
    charge = rng.choice(["21-902(A)", "22-204(F)", "21-801.1"], n)
    p = np.where(charge == "21-902(A)", 0.9, np.where(charge == "22-204(F)", 0.1, 0.5))
    vt = rng.random(n) < p
    df = pd.DataFrame({
        "Violation_Type": np.where(vt, "Citation", "Warning"),
        "Stop_Year": years, "Year": years - rng.integers(0, 15, n),
        "Charge": charge,
        "Violation_Category": np.where(charge == "21-902(A)", "DUI / Alcohol / Substance",
                                       np.where(charge == "22-204(F)", "Vehicle Equipment & Maintenance",
                                                "Speeding")),
        "SubAgency": rng.choice(["1st District", "2nd District"], n),
        "VehicleType": rng.choice(["02 - Automobile", "28 - Other"], n),
        "Arrest_Type": rng.choice(["A - Marked Patrol", "Q - Marked Laser"], n),
        "Day_Of_Week": rng.choice(["Monday", "Friday"], n),
        "Time_Of_Day": rng.choice(["Morning", "Night"], n),
        "Stop_Hour": rng.integers(0, 24, n).astype("int8"),
    })
    for c in FLAGS:
        df[c] = rng.random(n) < 0.05
    return df


def test_build_frame_keeps_only_citations_and_warnings():
    df = raw_rows(50)
    df.loc[:4, "Violation_Type"] = "Esero"
    out = build_frame(df)
    assert set(out["Violation_Type"]) <= {"Citation", "Warning"} and len(out) == 45
    assert set(out["y"]) <= {0, 1}


def test_impossible_vehicle_ages_become_the_median_not_negative():
    df = raw_rows(20)
    df.loc[0, "Year"] = df.loc[0, "Stop_Year"] + 3      # model year in the future
    df.loc[1, "Year"] = 1900                            # typo
    out = build_frame(df)
    assert out["Vehicle_Age"].between(0, 50).all()


def test_protected_and_post_decision_columns_are_not_features():
    features = set(CATEGORICAL + NUMERIC + FLAGS)
    assert not features & set(EXCLUDED)
    assert {"Race", "Gender", "Search_Outcome"} <= set(EXCLUDED)


def test_time_split_has_no_overlap_and_respects_years():
    df = build_frame(raw_rows(500))
    train, valid, test = time_split(df, 2022, 2023, 2024)
    assert train["Stop_Year"].max() <= 2022 and set(valid["Stop_Year"]) == {2023}
    assert test["Stop_Year"].min() >= 2024
    assert not set(train.index) & set(test.index)


def test_rare_categories_are_folded_using_training_counts_only():
    train = pd.DataFrame({"Charge": ["A"] * 5 + ["B"]})
    test = pd.DataFrame({"Charge": ["B"] * 50 + ["C"]})     # common in test, rare in train
    tr, te = fold_rare(train, [train, test], "Charge", min_count=3)
    assert set(tr["Charge"]) == {"A", "OTHER"}
    assert set(te["Charge"]) == {"OTHER"}


def test_logistic_regression_learns_the_planted_signal():
    df = build_frame(raw_rows(3000))
    train, valid, test = time_split(df, 2022, 2023, 2024)
    X = lambda d: d[CATEGORICAL + NUMERIC + FLAGS]  # noqa: E731
    m = make_logreg().fit(X(train), train["y"])
    s = score("lr", test["y"], m.predict_proba(X(test))[:, 1], 0.5)
    assert s.roc_auc > 0.8
    pos, neg = top_coefficients(m, 3)
    assert any("21-902(A)" in n or "DUI" in n for n, _ in pos)
    assert any("22-204(F)" in n or "Equipment" in n for n, _ in neg)


def test_threshold_search_returns_a_probability():
    y = np.array([0, 0, 1, 1])
    assert 0.05 <= best_f1_threshold(y, np.array([0.1, 0.2, 0.8, 0.9])) <= 0.95


def test_recalibration_moves_predictions_to_the_new_base_rate_without_reordering():
    rng = np.random.default_rng(1)
    p_model = rng.uniform(0.2, 0.9, 5000)            # model trained when citations were common
    y_new = (rng.random(5000) < p_model * 0.5).astype(int)   # citations now half as likely
    cal = Recalibrator().fit(y_new, p_model)
    p_cal = cal.transform(p_model)
    assert abs(p_cal.mean() - y_new.mean()) < 0.02
    assert abs(p_model.mean() - y_new.mean()) > 0.2
    assert np.all(np.diff(p_cal[np.argsort(p_model)]) >= -1e-12)   # ranking unchanged


def test_score_reports_confusion_matrix_in_tn_fp_fn_tp_order():
    s = score("x", np.array([0, 0, 1, 1]), np.array([0.1, 0.9, 0.2, 0.8]), 0.5)
    assert s.confusion == [[1, 1], [1, 1]]
    assert s.precision == pytest.approx(0.5) and s.recall == pytest.approx(0.5)
