
from pathlib import Path
import pandas as pd

# Get the main project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Dataset file path
file_path = BASE_DIR / "dataset" / "general_dataset.csv"

# Check whether the file exists
print("Dataset exists:", file_path.exists())
print("Dataset path:", file_path)

# Load and inspect the dataset
df = pd.read_csv(file_path)

print("\nFirst 5 rows:")
print(df.head())

print("\nDataset shape:")
print(df.shape)

print("\nColumn names:")
print(df.columns.tolist())

print("\nMissing values:")
print(df.isnull().sum())


# Check ticket categories
print("\nTicket Category Distribution:")
print(df["type"].value_counts())

# Check ticket priority distribution
print("\nTicket Priority Distribution:")
print(df["priority"].value_counts())

# Check unique values in important columns
print("\nUnique Categories:", df["type"].nunique())
print("Unique Priorities:", df["priority"].nunique())

# Check whether both subject and body are missing
print("\nRows with both subject and body missing:")
print(df[["subject", "body"]].isna().all(axis=1).sum())

# Check duplicate tickets
print("\nExact duplicate rows:", df.duplicated().sum())