from pathlib import Path

import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report
)


# Project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Dataset paths
TRAIN_PATH = BASE_DIR / "dataset" / "splits" / "priority_train.csv"
TEST_PATH = BASE_DIR / "dataset" / "splits" / "priority_test.csv"


# Load datasets
train_df = pd.read_csv(TRAIN_PATH)
test_df = pd.read_csv(TEST_PATH)

print("Training rows:", len(train_df))
print("Testing rows:", len(test_df))


# Input and target
X_train = train_df["ticket_text"].fillna("")
y_train = train_df["priority"]

X_test = test_df["ticket_text"].fillna("")
y_test = test_df["priority"]


# Display priority distribution
print("\nPriority categories:")
print(y_train.value_counts())


# TF-IDF + Logistic Regression
model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2)
        )
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=1000
        )
    )
])


# Train model
print("\nTraining priority classification model...")

model.fit(X_train, y_train)


# Predictions
y_pred = model.predict(X_test)


# Evaluation
accuracy = accuracy_score(y_test, y_pred)

precision = precision_score(
    y_test,
    y_pred,
    average="weighted",
    zero_division=0
)

recall = recall_score(
    y_test,
    y_pred,
    average="weighted",
    zero_division=0
)

f1 = f1_score(
    y_test,
    y_pred,
    average="weighted",
    zero_division=0
)


print("\n========== MODEL EVALUATION ==========")

print("Accuracy :", round(accuracy, 4))
print("Precision:", round(precision, 4))
print("Recall   :", round(recall, 4))
print("F1-score :", round(f1, 4))


# Classification report
print("\nClassification Report:")

print(
    classification_report(
        y_test,
        y_pred,
        zero_division=0
    )
)


# Create models folder
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


# Save priority model
MODEL_PATH = MODEL_DIR / "priority_classifier.pkl"

joblib.dump(model, MODEL_PATH)

print("\nPriority model saved successfully!")
print("Model path:", MODEL_PATH)
