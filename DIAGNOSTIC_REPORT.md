# PhishGuard ML Classification Bug - DIAGNOSTIC REPORT

**Date**: August 29, 2026  
**Status**: Root cause identified ✅  
**Severity**: CRITICAL 🚨

---

## EXECUTIVE SUMMARY

A critical label inversion bug was discovered in the ML training pipeline. The model was trained with **inverted labels**, causing it to predict the opposite of what was intended.

**Result**: Phishing URLs are classified as Legitimate (WRONG)

---

## ROOT CAUSE

### The Bug

| Component | Actual Mapping | Code Mapping | Mismatch |
|-----------|---|---|---|
| **Dataset** | 0 = Phishing, 1 = Legitimate | — | — |
| **normalize_label()** | — | 1 = Phishing, 0 = Legitimate | ✗ INVERTED |
| **Model Training** | Used inverted labels | Treats as normal | ✗ FAILURE |
| **Predictions** | Backwards | Backwards | ✗ FAILURE |

### Evidence

**Diagnostic 1 - Label Verification**:
- Dataset has 100,945 URLs with label=0 (these are Phishing)
- Dataset has 134,850 URLs with label=1 (these are Legitimate)
- IP address analysis confirms: label=0 tends to have more suspicious patterns (phishing indicator)

**Diagnostic 2 - Model Testing**:
```
Test URL: https://google.com
  Raw model prediction: 0
  Current display: "Legitimate" ❌
  Should display: "Phishing" (because prediction=0=phishing)

Test URL: https://example.com  
  Raw model prediction: 0
  Current display: "Legitimate" ❌
  Should display: "Phishing"
```

**Diagnostic 3 - Training Data Consistency**:
```
Dataset URL: http://www.teramill.com
  Dataset label: 0 (Phishing in the file)
  Model prediction: 0 (matches dataset value)
  Current display: "Legitimate" ❌
  Should display: "Phishing"

Dataset URL: https://www.southbankmosaics.com
  Dataset label: 1 (Legitimate in the file)
  Model prediction: 1 (matches dataset value)
  Current display: "Phishing" ❌
  Should display: "Legitimate"
```

---

## WHY MODEL IS STILL 99.5% ACCURATE

The model **is** 99.5% accurate. But at the WRONG task:

```
Training Process:
  CSV label=0 → normalize_label(0) → 0 (no change)
  CSV label=1 → normalize_label(1) → 1 (no change)
  
  Model trains: "When you see this feature pattern, output 0"
  Test verification: URL from CSV with label=0 → Model predicts 0 ✓
  Accuracy: 99.5% correct!
  
But:
  CSV label=0 MEANS "Phishing" (in the file)
  Our code treats 0 as "Legitimate" (in the function)
  Result: Model is 99.5% accurate at INVERTING the labels
```

---

## PIPELINE ANALYSIS

### ✓ Verified Correct

1. **Feature Extraction**
   - Order: Identical between training and prediction
   - Semantics: All features mean the same thing
   - Determinism: Same URL always produces same features
   - No data leakage: Labels not used as features

2. **Risk Engine**
   - Correctly checks `model_result["label"] == 1` for phishing
   - Issue detection works properly
   - Problem: Input predictions are backwards

3. **Database & Flask Integration**
   - No bugs in how predictions are stored
   - No bugs in how results are displayed
   - Problem: Data being stored is backwards

### ✗ Root Cause Identified

**File**: `train_model.py`  
**Function**: `normalize_label()`

```python
def normalize_label(value: object) -> int | None:
    text = str(value).strip().lower()
    if text in {"1", "phishing", "phish", ...}:
        return 1  # ❌ Should return 0 (inverted)
    if text in {"0", "legitimate", "benign", ...}:
        return 0  # ❌ Should return 1 (inverted)
    return None
```

**The Problem**:
- The function assumes: 1 = Phishing, 0 = Legitimate
- But the dataset has: 0 = Phishing, 1 = Legitimate
- Result: Labels get inverted and never corrected

---

## VERIFICATION TESTS

### Diagnostic 2: Model Predictions

**Before Fix** (All suspicious URLs predicted as class 0):
- https://google.com → Prediction: 0, Display: "Legitimate" ❌
- https://example.com → Prediction: 0, Display: "Legitimate" ❌  
- http://192.168.1.1/login → Prediction: 0, Display: "Legitimate" ❌
- https://secure-bank-login.xyz → Prediction: 0, Display: "Legitimate" ❌

**All get prediction=0, which we display as "Legitimate"**
**Should all display as "Phishing"**

### Diagnostic 1: Dataset Analysis

**Phishing URL from dataset** (label=0):
- http://www.teramill.com
- Model predicts: 0 ✓ (matches training)
- We display: "Legitimate" ✗ (WRONG)

**Legitimate URL from dataset** (label=1):
- https://www.southbankmosaics.com  
- Model predicts: 1 ✓ (matches training)
- We display: "Phishing" ✗ (WRONG)

---

## IMPACT ASSESSMENT

### Current Behavior (BUGGY)

```
ML Prediction                    Display Result
           ↓                            ↓
Phishing URL → Model outputs 0 → "Legitimate" ❌
Legit URL    → Model outputs 1 → "Phishing" ❌
```

### Affected Components

1. **Flask Results Page** - Shows wrong ML predictions
2. **Database Records** - Stores wrong predictions
3. **Risk Assessment** - Combines wrong ML + right rules
4. **PDF Reports** - Includes wrong predictions
5. **Dashboard Stats** - Counts wrong predictions

### Not Affected

- Feature extraction ✓
- Rule-based detection ✓
- Risk scoring logic ✓
- Database schema ✓

---

## SOLUTION

### Step 1: Fix the Label Mapping

**File**: `train_model.py`  
**Function**: `normalize_label()`

Change from:
```python
def normalize_label(value: object) -> int | None:
    text = str(value).strip().lower()
    if text in {"1", "phishing", "phish", "malicious", "fraud", "bad", "true"}:
        return 1
    if text in {"0", "legitimate", "benign", "safe", "good", "false"}:
        return 0
    return None
```

To:
```python
def normalize_label(value: object) -> int | None:
    text = str(value).strip().lower()
    # Dataset encoding: 0 = Phishing, 1 = Legitimate
    if text in {"0", "phishing", "phish", "malicious", "fraud", "bad", "true"}:
        return 1  # Output 1 for phishing
    if text in {"1", "legitimate", "benign", "safe", "good", "false"}:
        return 0  # Output 0 for legitimate
    return None
```

**Key Change**:
- Input value "0" from CSV → Output 1 (Phishing)
- Input value "1" from CSV → Output 0 (Legitimate)
- Input string "phishing" → Output 1 (Phishing)
- Input string "legitimate" → Output 0 (Legitimate)

### Step 2: Retrain the Model

```bash
python train_model.py dataset/PhiUSIIL_Phishing_URL_Dataset.csv
```

This will:
- Load the dataset with correct label interpretation
- Extract features
- Train Random Forest with CORRECT labels
- Save corrected model files

### Step 3: Verification

After retraining, run diagnostics again to verify:
- Phishing URLs now predict as class 1 (or close to 1)
- Legitimate URLs now predict as class 0 (or close to 0)
- Suspicious test URLs display as "Phishing"
- Safe URLs display as "Legitimate"

---

## FILES AFFECTED

### Files to Modify
- ✏️ `train_model.py` - Fix normalize_label() function (1 change)

### Files to Regenerate (via retraining)
- 🔄 `model/phishing_model.pkl` - Will be overwritten with correct model
- 🔄 `model/model_metadata.json` - Will be overwritten with correct metadata

### Files Unchanged
- ✓ `scanner/feature_extractor.py` - No changes needed
- ✓ `scanner/ml_detector.py` - No changes needed
- ✓ `scanner/risk_engine.py` - No changes needed
- ✓ `app.py` - No changes needed
- ✓ `scanner/rule_engine.py` - No changes needed
- ✓ `database/database.py` - No changes needed

---

## EXPECTED RESULTS AFTER FIX

### Phishing/Suspicious URLs
```
URL: https://secure-bank-login.xyz
  Before: Risk=22 (Low), Prediction="Legitimate" ❌
  After:  Risk=22+ (Medium/High), Prediction="Phishing" ✓
  
URL: http://192.168.1.1/login/verify
  Before: Risk=41 (Medium), Prediction="Legitimate" ❌
  After:  Risk=41+ (Medium/High), Prediction="Phishing" ✓
```

### Legitimate URLs
```
URL: https://google.com
  Before: Risk=0 (Low), Prediction="Legitimate" (Lucky!) ✓
  After:  Risk=0 (Low), Prediction="Legitimate" ✓ (Correct!)
```

### Consistency
- ML predictions and risk scores will now align properly
- Suspicious-looking URLs will show as "Phishing"
- Safe URLs will show as "Legitimate"
- Rule-based and ML-based detection will work together

---

## CONCLUSION

**Root Cause**: Label inversion in normalize_label()  
**Impact**: Model trained backwards, predicts opposite  
**Fix**: Invert the mapping in one function, retrain model  
**Effort**: Minimal (1 file, 2 lines changed)  
**Risk**: Low (only changes data labels, not logic)  
**Verification**: Run diagnostic scripts to confirm  

---

**Diagnostic Status**: ✅ COMPLETE  
**Ready for Fix**: ✅ YES  
**Ready for Retraining**: ✅ YES  

Next: Apply the fix and retrain the model.
