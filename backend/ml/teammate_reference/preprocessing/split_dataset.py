
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

# 1. Locate the cleaned dataset
BASE_DIR = Path(__file__).resolve().parent.parent
input_path = BASE_DIR / "dataset" / "cleaned_dataset.csv"

# 2. Create an output folder
output_dir = BASE_DIR / "dataset" / "splits"
output_dir.mkdir(parents=True, exist_ok=True)

# 3. Load the cleaned dataset
df = pd.read_csv(input_path)

print("Total tickets:", len(df))

# 4. Prepare separate splits for each prediction task
tasks = {
    "type": ["ticket_text", "type", "language"],
    "priority": ["ticket_text", "priority", "language"]
}

for target, columns in tasks.items():
    task_df = df[columns].copy()

    # Split into 80% training and 20% testing
    train_df, test_df = train_test_split(
        task_df,
        test_size=0.20,
        random_state=42,
        stratify=task_df[target]
    )

    # Save the datasets
    train_path = output_dir / f"{target}_train.csv"
    test_path = output_dir / f"{target}_test.csv"

    train_df.to_csv(train_path, index=False, encoding="utf-8")
    test_df.to_csv(test_path, index=False, encoding="utf-8")

    # Display results
    print(f"\n--- {target.upper()} CLASSIFICATION ---")
    print("Training rows:", len(train_df))
    print("Testing rows:", len(test_df))

    print("\nTraining label distribution:")
    print(train_df[target].value_counts())

    print("\nTesting label distribution:")
    print(test_df[target].value_counts())

print("\nTrain-test splitting completed!")
print("Output folder:", output_dir)