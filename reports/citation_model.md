# Citation vs warning: model report

Train <= 2022 (1,740,977 rows), validate 2023 (66,876), test >= 2024 (167,260); test citation rate 30.7%.

| Model | ROC-AUC | PR-AUC | F1 | Precision | Recall | Brier | Threshold |
|---|---|---|---|---|---|---|---|
| Baseline (training citation rate) | 0.500 | 0.307 | 0.000 | 0.000 | 0.000 | 0.238 | 0.50 |
| Logistic regression (C=0.1, class_weight=None) | 0.790 | 0.698 | 0.605 | 0.620 | 0.591 | 0.171 | 0.50 |
| Logistic regression, recalibrated on 2023 | 0.790 | 0.698 | 0.604 | 0.613 | 0.596 | 0.154 | 0.35 |
| Gradient-boosted trees | 0.797 | 0.709 | 0.610 | 0.558 | 0.672 | 0.164 | 0.43 |

Logistic regression confusion matrix on test: TN 97,352  FP 18,565  FN 21,017  TP 30,326

## Drift by test year (logistic regression)

| Year | Rows | Actual citation rate | Mean predicted | Mean predicted (recalibrated) | ROC-AUC | F1 |
|---|---|---|---|---|---|---|
| 2024 | 77,581 | 33.4% | 44.6% | 34.1% | 0.790 | 0.618 |
| 2025 | 89,679 | 28.3% | 42.1% | 31.6% | 0.789 | 0.592 |

## Strongest logistic-regression weights

Towards citation:

- `cat__Charge_16-113(K)`: +3.69
- `cat__Charge_16-303(H)`: +3.41
- `cat__Violation_Category_DUI / Alcohol / Substance`: +3.38
- `cat__Charge_16-303(D)`: +3.31
- `cat__Charge_16-303(C)`: +2.98
- `cat__Charge_16-303(G)`: +2.96
- `cat__Charge_20-103(B)`: +2.76
- `cat__Charge_16-303(F)`: +2.64
- `cat__Charge_16-112(E)`: +2.55
- `cat__Charge_16-101(A)`: +2.41

Towards warning:

- `cat__Charge_21-802.1`: -2.70
- `cat__Charge_11-393.95(F)`: -2.61
- `cat__Charge_22-204(F)`: -2.39
- `cat__Charge_11-393.78`: -2.17
- `cat__Charge_17-104.2(B1)`: -2.17
- `cat__Charge_21-1120(C)`: -2.16
- `cat__Charge_11-390.21`: -2.06
- `cat__Charge_13-410(E2)`: -1.97
- `cat__Charge_16-114(B)`: -1.90
- `cat__Charge_11-393.9`: -1.85

Excluded from features: Race, Gender, Search_Conducted, Search_Disposition, Search_Outcome, Search_Reason, Search_Reason_For_Stop, Search_Type, Search_Arrest_Reason.
