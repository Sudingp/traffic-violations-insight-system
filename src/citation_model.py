"""
Will a traffic stop charge end in a citation or a warning?

A classical-ML baseline on the cleaned county data: logistic regression on one-hot
categorical features plus a few scaled numeric ones, compared with a majority-class
baseline and a gradient-boosted tree model.

Design choices, each for a reason:
- Time-based split (train on older years, tune on the next year, test on the latest
  years). A random split would leak future enforcement patterns into training, and
  the citation rate falls from 57% in 2012 to 28% in 2025, so drift is the real risk.
- Race, gender and anything recorded after the decision (searches, search outcomes)
  are excluded from the features.
- The decision threshold is chosen on the validation year (best F1), never on test.
- Rare categories are folded into "OTHER" using training-set counts only.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET_POSITIVE = "Citation"
TARGET_NEGATIVE = "Warning"

CATEGORICAL = ["Charge", "Violation_Category", "SubAgency", "VehicleType", "Arrest_Type",
               "Day_Of_Week", "Time_Of_Day"]
FLAGS = ["Accident", "Belts", "Personal_Injury", "Property_Damage", "Fatal", "Commercial_License",
         "HAZMAT", "Commercial_Vehicle", "Alcohol", "Work_Zone", "Contributed_To_Accident",
         "Is_Multi_Charge"]
NUMERIC = ["Stop_Hour", "Vehicle_Age"]
EXCLUDED = ["Race", "Gender", "Search_Conducted", "Search_Disposition", "Search_Outcome",
            "Search_Reason", "Search_Reason_For_Stop", "Search_Type", "Search_Arrest_Reason"]

RAW_COLUMNS = (["Violation_Type", "Stop_Year", "Year"] + CATEGORICAL + FLAGS + ["Stop_Hour"])


def build_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Keep citation/warning rows and derive the model's columns."""
    out = df[df["Violation_Type"].isin([TARGET_POSITIVE, TARGET_NEGATIVE])].copy()
    out["y"] = (out["Violation_Type"] == TARGET_POSITIVE).astype(np.int8)
    age = out["Stop_Year"] - out["Year"]
    out["Vehicle_Age"] = age.where((age >= 0) & (age <= 50))   # bad model years become missing
    out["Vehicle_Age"] = out["Vehicle_Age"].fillna(out["Vehicle_Age"].median())
    for c in CATEGORICAL:
        out[c] = out[c].astype("string").fillna("UNKNOWN").str.strip().replace("", "UNKNOWN")
    for c in FLAGS:
        out[c] = out[c].fillna(False).astype(np.int8)
    out["Stop_Hour"] = out["Stop_Hour"].astype(float)
    return out


def time_split(df: pd.DataFrame, train_until: int, valid_year: int, test_from: int):
    train = df[df["Stop_Year"] <= train_until]
    valid = df[df["Stop_Year"] == valid_year]
    test = df[df["Stop_Year"] >= test_from]
    return train, valid, test


def fold_rare(train: pd.DataFrame, frames, column: str, min_count: int):
    """Replace categories seen fewer than min_count times in TRAIN with 'OTHER'."""
    keep = set(train[column].value_counts().loc[lambda s: s >= min_count].index)
    return [f.assign(**{column: f[column].where(f[column].isin(keep), "OTHER")}) for f in frames]


def make_logreg(C: float = 1.0, class_weight=None) -> Pipeline:
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=None), CATEGORICAL),
        ("num", StandardScaler(), NUMERIC),
        ("flag", "passthrough", FLAGS),
    ])
    return Pipeline([("pre", pre),
                     ("clf", LogisticRegression(C=C, class_weight=class_weight, max_iter=300,
                                                solver="lbfgs"))])


def best_f1_threshold(y_true, proba) -> float:
    """Threshold with the highest F1 (searched on validation data only)."""
    grid = np.linspace(0.05, 0.95, 91)
    scores = [f1_score(y_true, proba >= t, zero_division=0) for t in grid]
    return float(grid[int(np.argmax(scores))])


@dataclass
class Scores:
    name: str
    roc_auc: float
    pr_auc: float
    f1: float
    precision: float
    recall: float
    brier: float
    threshold: float
    confusion: list = field(default_factory=list)   # [[tn, fp], [fn, tp]]


def score(name: str, y_true, proba, threshold: float) -> Scores:
    pred = proba >= threshold
    return Scores(name=name,
                  roc_auc=float(roc_auc_score(y_true, proba)) if len(set(y_true)) > 1 else float("nan"),
                  pr_auc=float(average_precision_score(y_true, proba)),
                  f1=float(f1_score(y_true, pred, zero_division=0)),
                  precision=float(precision_score(y_true, pred, zero_division=0)),
                  recall=float(recall_score(y_true, pred, zero_division=0)),
                  brier=float(brier_score_loss(y_true, proba)),
                  threshold=threshold,
                  confusion=confusion_matrix(y_true, pred, labels=[0, 1]).tolist())


class Recalibrator:
    """
    Platt-style recalibration fitted on the validation year: a 1-D logistic regression on
    the model's log-odds. The citation rate keeps falling, so a model trained on older
    years over-predicts citations; this shifts its probabilities to the recent base rate
    without changing the ranking (ROC-AUC stays the same).
    """

    def fit(self, y_valid, p_valid):
        z = np.log(np.clip(p_valid, 1e-6, 1 - 1e-6) / np.clip(1 - p_valid, 1e-6, 1)).reshape(-1, 1)
        self.lr = LogisticRegression(C=1e6, max_iter=200).fit(z, y_valid)
        return self

    def transform(self, p):
        z = np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1)).reshape(-1, 1)
        return self.lr.predict_proba(z)[:, 1]


def top_coefficients(model: Pipeline, n: int = 10):
    """Largest positive (towards citation) and negative (towards warning) LR weights."""
    names = model.named_steps["pre"].get_feature_names_out()
    coefs = model.named_steps["clf"].coef_[0]
    order = np.argsort(coefs)
    pos = [(names[i], float(coefs[i])) for i in order[::-1][:n]]
    neg = [(names[i], float(coefs[i])) for i in order[:n]]
    return pos, neg
