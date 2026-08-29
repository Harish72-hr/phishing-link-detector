from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from scanner.feature_extractor import FEATURE_NAMES, feature_vector

URL_COLUMNS = ("url", "link", "domain", "uri")
LABEL_COLUMNS = ("label", "class", "type", "status", "result")


def find_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {column.strip().lower(): column for column in columns}
    return next((normalized[name] for name in candidates if name in normalized), None)


def normalize_label(value: object) -> int | None:
    text = str(value).strip().lower()
    # Dataset encoding: 0 = Phishing, 1 = Legitimate
    if text in {"0", "phishing", "phish", "malicious", "fraud", "bad", "true"}:
        return 1
    if text in {"1", "legitimate", "benign", "safe", "good", "false"}:
        return 0
    return None


def train(dataset_path: str, output_dir: str = "model") -> None:
    print("\n" + "=" * 80)
    print("PHISHGUARD ML TRAINING PIPELINE")
    print("=" * 80)
    
    # Step 1: Load dataset
    print("\n[1/7] Loading dataset...")
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}. Place a real CSV in dataset/ and pass its path to this command.")
    
    frame = pd.read_csv(path)
    print(f"      ✓ Dataset loaded: {frame.shape[0]} rows × {frame.shape[1]} columns")
    
    # Step 2: Identify columns
    print("\n[2/7] Identifying columns...")
    url_column = find_column(list(frame.columns), URL_COLUMNS)
    label_column = find_column(list(frame.columns), LABEL_COLUMNS)
    if not url_column or not label_column:
        raise ValueError("CSV must include a URL column (url/link/domain) and a label column (label/class/type/status). See dataset/README.md.")
    print(f"      ✓ URL column: {url_column}")
    print(f"      ✓ Label column: {label_column}")
    
    # Step 3: Clean data
    print("\n[3/7] Cleaning data...")
    initial_count = len(frame)
    clean = frame[[url_column, label_column]].dropna().copy()
    print(f"      • Removed rows with missing values: {initial_count - len(clean)}")
    
    clean["target"] = clean[label_column].map(normalize_label)
    before_norm = len(clean)
    clean = clean[clean["target"].notna()]
    invalid_labels = before_norm - len(clean)
    if invalid_labels > 0:
        print(f"      • Removed rows with invalid labels: {invalid_labels}")
    
    if len(clean) < 10 or clean["target"].nunique() < 2:
        raise ValueError("Dataset needs at least 10 valid rows and both legitimate and phishing labels.")
    
    # Check for empty URLs
    empty_urls = clean[url_column].isna().sum() + (clean[url_column] == "").sum()
    print(f"      • Empty URLs: {empty_urls}")
    
    # Check for duplicate URLs
    dup_urls = clean[url_column].duplicated().sum()
    print(f"      • Duplicate URLs: {dup_urls}")
    
    print(f"      ✓ Final clean dataset: {len(clean)} rows")
    
    # Step 4: Class distribution
    print("\n[4/7] Analyzing class distribution...")
    class_counts = clean["target"].value_counts().sort_index()
    for label_val, count in class_counts.items():
        label_name = "Legitimate" if label_val == 0 else "Phishing"
        pct = (count / len(clean)) * 100
        print(f"      • {label_name} (label={label_val}): {count:8d} ({pct:6.2f}%)")
    
    # Step 5: Extract features
    print("\n[5/7] Extracting URL features...")
    print(f"      • Extracting {len(FEATURE_NAMES)} features from {len(clean)} URLs...")
    
    # Extract features with progress
    features_list = []
    for idx, url in enumerate(clean[url_column], 1):
        if idx % 50000 == 0:
            print(f"      • Progress: {idx}/{len(clean)} URLs processed...")
        try:
            feat_vec = feature_vector(str(url))
            features_list.append(feat_vec)
        except Exception as e:
            print(f"      ⚠ Warning: Failed to extract features for URL at index {idx}: {e}")
            features_list.append([0] * len(FEATURE_NAMES))
    
    features = pd.DataFrame(features_list, columns=FEATURE_NAMES)
    print(f"      ✓ Features extracted: {features.shape[0]} rows × {features.shape[1]} columns")
    
    # Check for invalid feature values
    nan_count = features.isnull().sum().sum()
    inf_count = features.isin([float('inf'), float('-inf')]).sum().sum()
    if nan_count > 0 or inf_count > 0:
        print(f"      ⚠ Warning: Found {nan_count} NaN and {inf_count} infinite values - replacing with 0")
        features = features.fillna(0).replace([float('inf'), float('-inf')], 0)
    
    # Step 6: Split dataset
    print("\n[6/7] Splitting dataset...")
    y = clean["target"].astype(int).values
    x_train, x_test, y_train, y_test = train_test_split(
        features, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"      ✓ Training set: {len(x_train)} samples (80%)")
    print(f"      ✓ Testing set: {len(x_test)} samples (20%)")
    print(f"      • Training - Legitimate: {(y_train == 0).sum()}, Phishing: {(y_train == 1).sum()}")
    print(f"      • Testing  - Legitimate: {(y_test == 0).sum()}, Phishing: {(y_test == 1).sum()}")
    
    # Step 7: Train model
    print("\n[7/7] Training Random Forest classifier...")
    print(f"      • n_estimators=250")
    print(f"      • random_state=42")
    print(f"      • class_weight='balanced'")
    print(f"      • n_jobs=-1 (using all CPU cores)")
    
    model = RandomForestClassifier(
        n_estimators=250,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1
    )
    model.fit(x_train, y_train)
    print(f"      ✓ Model trained successfully")
    
    # Evaluate model
    print("\n" + "=" * 80)
    print("MODEL EVALUATION (TEST SET)")
    print("=" * 80)
    
    predicted = model.predict(x_test)
    predicted_proba = model.predict_proba(x_test)
    
    accuracy = accuracy_score(y_test, predicted)
    precision = precision_score(y_test, predicted, zero_division=0)
    recall = recall_score(y_test, predicted, zero_division=0)
    f1 = f1_score(y_test, predicted, zero_division=0)
    roc_auc = roc_auc_score(y_test, predicted_proba[:, 1])
    
    print(f"\nAccuracy:  {accuracy * 100:6.2f}%  - Proportion of correct predictions")
    print(f"Precision: {precision * 100:6.2f}%  - Of predicted phishing, how many are correct")
    print(f"Recall:    {recall * 100:6.2f}%  - Of actual phishing, how many are detected")
    print(f"F1-Score:  {f1 * 100:6.2f}%  - Harmonic mean of precision and recall")
    print(f"ROC-AUC:   {roc_auc * 100:6.2f}%  - Area under ROC curve (0.5=random, 1.0=perfect)")
    
    print(f"\nClassification Report:")
    print(classification_report(y_test, predicted, target_names=["Legitimate", "Phishing"], zero_division=0))
    
    print(f"\nConfusion Matrix:")
    cm = confusion_matrix(y_test, predicted)
    print(f"                 Predicted")
    print(f"                 Legit  Phish")
    print(f"Actual Legit  [{cm[0, 0]:6d} {cm[0, 1]:6d}]")
    print(f"       Phish  [{cm[1, 0]:6d} {cm[1, 1]:6d}]")
    
    # Save model
    print("\n" + "=" * 80)
    print("SAVING MODEL")
    print("=" * 80)
    
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    
    model_path = destination / "phishing_model.pkl"
    features_path = destination / "feature_names.json"
    
    joblib.dump(model, model_path)
    print(f"\n✓ Model saved to: {model_path}")
    
    (destination / "feature_names.json").write_text(json.dumps(FEATURE_NAMES, indent=2), encoding="utf-8")
    print(f"✓ Features saved to: {features_path}")
    
    # Save metadata
    metadata = {
        "training_date": datetime.now().isoformat(),
        "dataset_path": str(path),
        "dataset_name": path.name,
        "total_samples": len(clean),
        "training_samples": len(x_train),
        "testing_samples": len(x_test),
        "num_features": len(FEATURE_NAMES),
        "feature_names": FEATURE_NAMES,
        "class_mapping": {
            "0": "Legitimate",
            "1": "Phishing"
        },
        "class_distribution": {
            "legitimate_count": int(class_counts.get(0, 0)),
            "phishing_count": int(class_counts.get(1, 0))
        },
        "model_parameters": {
            "n_estimators": 250,
            "random_state": 42,
            "class_weight": "balanced",
            "n_jobs": -1
        },
        "metrics": {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "roc_auc": float(roc_auc)
        },
        "confusion_matrix": {
            "true_negatives": int(cm[0, 0]),
            "false_positives": int(cm[0, 1]),
            "false_negatives": int(cm[1, 0]),
            "true_positives": int(cm[1, 1])
        }
    }
    
    metadata_path = destination / "model_metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata saved to: {metadata_path}")
    
    print("\n" + "=" * 80)
    print("✅ TRAINING COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print(f"\nModel is ready for deployment.")
    print(f"To use the model, ensure these files exist:")
    print(f"  • {model_path}")
    print(f"  • {features_path}")
    print(f"\nThe Flask app will automatically load and use the model.")
    print(f"Run: python app.py")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train PhishGuard on a real URL CSV dataset.")
    parser.add_argument("dataset", help="Path to a real CSV dataset")
    parser.add_argument("--output-dir", default="model")
    args = parser.parse_args()
    train(args.dataset, args.output_dir)
