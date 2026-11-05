
from pathlib import Path
import pandas as pd

# Locate the cleaned dataset
BASE_DIR = Path(__file__).resolve().parent.parent
file_path = BASE_DIR / "dataset" / "cleaned_dataset.csv"

df = pd.read_csv(file_path)

# 1. Check dataset size
print("Dataset shape:", df.shape)

# 2. Check language distribution
print("\nLanguage Distribution:")
print(df["language"].value_counts())

# 3. Check category and priority combinations
print("\nCategory-Priority Combinations:")
print(pd.crosstab(df["type"], df["priority"]))

# 4. Check the percentage of each language
print("\nLanguage Percentages:")
print(
    (df["language"].value_counts(normalize=True) * 100)
    .round(2)
)

# 5. Confirm required fields are present
print("\nMissing Values:")
print(df[["ticket_text", "type", "priority"]].isnull().sum())