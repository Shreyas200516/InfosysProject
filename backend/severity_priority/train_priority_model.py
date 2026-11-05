"""
Trains a TF-IDF + Logistic Regression priority classifier, evaluates performance
(Accuracy, Precision, Recall, F1-Score, Confusion Matrix), and persists the model.
"""

import os
import argparse
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix,
)

DEFAULT_CANDIDATE_DATASETS = ["cleaned_dataset.csv"]
MODEL_PATH = "priority_model.joblib"


def find_dataset(custom_path=None):
    if custom_path and os.path.exists(custom_path):
        return custom_path
    for path in DEFAULT_CANDIDATE_DATASETS:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        f"Could not find any support ticket dataset. Please provide one or specify via --dataset."
    )


def train_and_evaluate_priority_model(dataset_path=None, model_save_path=MODEL_PATH):
    print("=" * 60)
    print("SupportPilot - Training Priority Prediction Model ")
    print("=" * 60)

    dataset_path = find_dataset(dataset_path)
    print(f"Using dataset: {dataset_path}")

    df = pd.read_csv(dataset_path)
    print(f"Loaded {len(df)} records from {dataset_path}")

    text_col = None
    for candidate in ["ticket_text", "text", "ticket", "description", "subject"]:
        if candidate in df.columns:
            text_col = candidate
            break

    # Support priority column names
    prio_col = None
    for candidate in ["priority", "Priority", "priority_label", "severity"]:
        if candidate in df.columns:
            prio_col = candidate
            break

    if not text_col or not prio_col:
        raise ValueError(
            f"Dataset must contain ticket text and priority columns. Found: {list(df.columns)}"
        )

    print(f"Using text column: '{text_col}', priority column: '{prio_col}'")
    print("Label distribution:\n", df[prio_col].value_counts())

    X = df[text_col].astype(str)
    y = df[prio_col].astype(str)

    # Stratified train/test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"\nTrain set: {len(X_train)} samples | Test set: {len(X_test)} samples")

    # Pipeline: TF-IDF with unigrams & bigrams + Multinomial Logistic Regression
    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    stop_words="english",
                    sublinear_tf=True,
                    max_features=5000,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=1.0, max_iter=1000, class_weight="balanced", random_state=42
                ),
            ),
        ]
    )

    # Train model
    pipeline.fit(X_train, y_train)
    print("\nModel training completed successfully.")

    # Predictions & Evaluation on test set
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)

    acc = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="weighted", zero_division=0
    )

    print("\n" + "=" * 60)
    print("EVALUATION METRICS (TEST SET):")
    print("=" * 60)
    print(f"Accuracy:  {acc * 100:.2f}%")
    print(f"Precision: {precision * 100:.2f}%")
    print(f"Recall:    {recall * 100:.2f}%")
    print(f"F1-Score:  {f1 * 100:.2f}%")

    labels = sorted(list(y.unique()))
    print("\nClassification Report:")
    report = classification_report(
        y_test, y_pred, target_names=labels, digits=4, zero_division=0
    )
    print(report)

    cm = confusion_matrix(y_test, y_pred, labels=labels)
    cm_df = pd.DataFrame(
        cm, index=[f"Actual {l}" for l in labels], columns=[f"Pred {l}" for l in labels]
    )
    print("Confusion Matrix:")
    print(cm_df)

    # Persist model artifact with metadata
    artifact = {
        "model": pipeline,
        "classes": pipeline.named_steps["clf"].classes_.tolist(),
        "metrics": {
            "accuracy": float(acc),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
        },
        "report": classification_report(
            y_test, y_pred, target_names=labels, output_dict=True, zero_division=0
        ),
        "confusion_matrix": cm.tolist(),
    }

    joblib.dump(artifact, model_save_path)
    print(f"\nModel artifact successfully saved to: {model_save_path}")
    return artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SupportPilot Priority Model Trainer")
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to cleaned dataset CSV",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=MODEL_PATH,
        help="Output path for joblib model artifact",
    )
    args = parser.parse_args()
    train_and_evaluate_priority_model(
        dataset_path=args.dataset, model_save_path=args.output
    )
