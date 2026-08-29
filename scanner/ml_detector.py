"""Optional trained-model integration."""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import joblib

from .feature_extractor import FEATURE_NAMES, feature_vector


class ModelUnavailableError(RuntimeError):
    pass


def predict_url(url: str, model_path: str | Path = "model/phishing_model.pkl", features_path: str | Path = "model/feature_names.json") -> dict[str, object]:
    """
    Predict whether a URL is phishing using the trained Random Forest model.
    
    Args:
        url: URL string to analyze
        model_path: Path to trained model (phishing_model.pkl)
        features_path: Path to feature names (feature_names.json)
    
    Returns:
        dict with keys:
            - prediction: "Phishing" or "Legitimate"
            - label: 1 (phishing) or 0 (legitimate)
            - confidence: Prediction confidence as decimal 0.0-1.0
    
    Raises:
        ModelUnavailableError: If model files don't exist
    """
    model_file = Path(model_path)
    names_file = Path(features_path)
    
    if not model_file.exists():
        raise ModelUnavailableError(
            f"ML model not found at {model_file}. "
            "To train the model, run: python train_model.py dataset/PhiUSIIL_Phishing_URL_Dataset.csv"
        )
    
    if not names_file.exists():
        raise ModelUnavailableError(
            f"Feature names file not found at {names_file}. "
            "The model metadata may be corrupted. Retrain with: python train_model.py dataset/PhiUSIIL_Phishing_URL_Dataset.csv"
        )
    
    try:
        # Load model and feature names
        model = joblib.load(model_file)
        feature_names = json.loads(names_file.read_text(encoding="utf-8"))
        
        # Extract features from URL
        vector = feature_vector(url, feature_names)
        
        # Make prediction (suppress sklearn warnings about feature names)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            prediction_label = int(model.predict([vector])[0])
            probabilities = model.predict_proba([vector])[0]
        
        # Get confidence (probability of predicted class, 0.0-1.0)
        confidence = float(max(probabilities))
        
        # Format result
        return {
            "prediction": "Phishing" if prediction_label == 1 else "Legitimate",
            "label": prediction_label,
            "confidence": confidence
        }
    
    except (joblib.JobLibRuntimeError, ValueError, json.JSONDecodeError) as e:
        raise ModelUnavailableError(
            f"Error loading model or feature names: {e}. "
            "The model files may be corrupted. Retrain with: python train_model.py"
        ) from e
