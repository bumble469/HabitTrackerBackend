"""Print the confusion matrix and precision/recall of the saved model on the held-out habits.

Run AFTER training, from the repo root:
    python -m ml.evaluate

It rebuilds the same 80/20 split by habit that ml/train.py uses (same data file, same seed),
so the test set is exactly the one behind the numbers in ml/metrics.json.
It only reads the saved model. It does not train anything or change any file.
"""
import argparse

import joblib
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit

from ml.train import OUT_DIR, build_dataset, find_data_file, load_habits


def main(data_arg) -> None:
    habits = load_habits(find_data_file(data_arg))
    X, y, groups, _ = build_dataset(habits)
    _, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(X, y, groups))

    model = joblib.load(OUT_DIR / "model.joblib")
    y_true = y[test_idx]
    y_pred = model.predict(X[test_idx])  # same 0.5 cut-off as the reported metrics

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    total = int(tn + fp + fn + tp)

    print(f"Confusion matrix (logistic regression, {total:,} held-out rows)\n")
    print(f"{'':22s}{'Predicted: fine':>18s}{'Predicted: at risk':>22s}")
    print(f"{'Actual: fine':22s}{tn:>18,d}{fp:>22,d}")
    print(f"{'Actual: dropped':22s}{fn:>18,d}{tp:>22,d}")
    print()
    print(f"TN {tn:,} correct 'fine'   | FP {fp:,} false alarms")
    print(f"FN {fn:,} missed dropouts  | TP {tp:,} dropouts caught\n")
    print(f"Accuracy   {accuracy_score(y_true, y_pred):.4f}")
    print(f"Precision  {precision_score(y_true, y_pred, zero_division=0):.4f}   (of the warnings, how many were right)")
    print(f"Recall     {recall_score(y_true, y_pred, zero_division=0):.4f}   (of the real dropouts, how many were caught)")
    print(f"F1         {f1_score(y_true, y_pred, zero_division=0):.4f}")
    print(f"False alarm rate  {fp / max(fp + tn, 1):.4f}   (fine habits wrongly flagged)")
    print(f"Miss rate         {fn / max(fn + tp, 1):.4f}   (real dropouts not flagged)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", help="path to the same CSV/Excel file used for training")
    main(parser.parse_args().data)
