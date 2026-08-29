# Dataset format

Place a real CSV dataset in this directory and pass its path to `train_model.py`.

The CSV must contain one URL column (`url`, `link`, or `domain`) and one label column (`label`, `class`, `type`, or `status`). Labels may be `0/1`, `legitimate/phishing`, `benign/malicious`, or common equivalents. `0` means legitimate and `1` means phishing.

Example:

```csv
url,label
https://example.com,0
http://example-phishing.test/login,1
```

No dataset is bundled and the application never invents training data.
