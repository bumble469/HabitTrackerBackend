"""Optional experiment: does a voting ensemble of logistic regression + gradient boosting help?

Run from the repo root (slow: it trains gradient boosting on the full training set):
    python -m ml.voting_test

Uses the same data file and the same 80/20 split by habit as ml/train.py.
It does not save or change the deployed model.
"""
import argparse

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.train import build_dataset, find_data_file, load_habits


def row(name, y, pred, proba=None):
    auc = f"{roc_auc_score(y, proba):.4f}" if proba is not None else "n/a"
    print(
        f"{name:34s}{accuracy_score(y, pred):>9.4f}{precision_score(y, pred, zero_division=0):>11.4f}"
        f"{recall_score(y, pred, zero_division=0):>9.4f}{f1_score(y, pred, zero_division=0):>9.4f}{auc:>10s}"
    )


def main(data_arg) -> None:
    habits = load_habits(find_data_file(data_arg))
    X, y, groups, _ = build_dataset(habits)
    train_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(X, y, groups))
    Xtr, ytr, Xte, yte = X[train_idx], y[train_idx], X[test_idx], y[test_idx]

    print(f"Training on {len(ytr):,} rows, testing on {len(yte):,} rows. Gradient boosting is slow, please wait...\n")
    lr = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(class_weight="balanced", max_iter=1000))])
    gb = GradientBoostingClassifier(random_state=42)
    lr.fit(Xtr, ytr)
    gb.fit(Xtr, ytr)

    p_lr, p_gb = lr.predict_proba(Xte)[:, 1], gb.predict_proba(Xte)[:, 1]
    pred_lr, pred_gb = (p_lr >= 0.5).astype(int), (p_gb >= 0.5).astype(int)

    p_soft = (p_lr + p_gb) / 2                         # soft voting: average the probabilities
    pred_soft = (p_soft >= 0.5).astype(int)
    pred_hard = ((pred_lr + pred_gb) >= 2).astype(int)  # hard voting, 2 voters: a tie counts as "fine"

    print(f"{'Model':34s}{'Accuracy':>9s}{'Precision':>11s}{'Recall':>9s}{'F1':>9s}{'ROC-AUC':>10s}")
    row("Baseline (never flags)", yte, np.zeros_like(yte))
    row("Logistic regression (deployed)", yte, pred_lr, p_lr)
    row("Gradient boosting", yte, pred_gb, p_gb)
    row("Soft voting (average probability)", yte, pred_soft, p_soft)
    row("Hard voting (both must agree)", yte, pred_hard)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", help="path to the same CSV/Excel file used for training")
    main(parser.parse_args().data)
