# Quick Start Guide - Random Forest & Auto-Tuning

## Random Forest Training

### Basic Training
```bash
# Navigate to backend directory
cd Backend/SafeLink_Backend

# Train with default parameters
python train_rf.py

# Or use the module directly
python models/random_forest_trainer.py data/All_Labelled.csv
```

### Custom Training
```python
from models.random_forest_trainer import train_from_csv

trainer, train_metrics, test_metrics = train_from_csv(
    csv_path='data/All_Labelled.csv',
    label_col='Label',
    test_size=0.2,
    n_estimators=200,      # More trees
    max_depth=50,          # Deeper trees
    class_weight='balanced',
    random_state=42
)

print(f"Test Accuracy: {test_metrics['accuracy']:.4f}")
print(f"Test F1: {test_metrics['f1_score']:.4f}")
```

### Using Trained Model
```python
from models.random_forest_trainer import RandomForestTrainer
import pandas as pd

# Load model
trainer = RandomForestTrainer()
trainer.load_model()

# Load new data
new_data = pd.read_csv('new_traffic.csv')
X = new_data.drop(columns=['Label'])  # Remove label if present

# Make predictions
predictions = trainer.predict(X)
probabilities = trainer.predict_proba(X)

print(f"Predictions: {predictions}")
print(f"Confidence: {probabilities}")
```

---

## Hyperparameter Tuning

### Tune Random Forest with Optuna
```python
from models.hyperparameter_tuner import HyperparameterTuner

tuner = HyperparameterTuner()

# Quick tuning (50 trials)
best_params = tuner.tune_random_forest_optuna(
    csv_path='data/All_Labelled.csv',
    label_col='Label',
    n_trials=50,           # Number of optimization trials
    timeout=3600,          # Max 1 hour
    n_jobs=4               # Parallel trials
)

print(f"Best parameters: {best_params}")
```

### Tune with GridSearch
```python
# Exhaustive search (slower but thorough)
param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [20, 30, 40],
    'min_samples_split': [2, 5, 10]
}

best_params = tuner.tune_random_forest_grid(
    csv_path='data/All_Labelled.csv',
    label_col='Label',
    param_grid=param_grid,
    cv=5,                  # 5-fold cross-validation
    n_jobs=-1              # Use all CPUs
)
```

### Compare Tuning Methods
```python
# Compare Optuna vs GridSearch
comparison = tuner.compare_tuning_methods(
    csv_path='data/All_Labelled.csv',
    label_col='Label',
    n_trials=30
)

print(f"Optuna accuracy: {comparison['optuna_best_score']}")
print(f"Grid accuracy: {comparison['grid_best_score']}")
print(f"Winner: {comparison['winner']}")
```

---

## API Usage

### Train RF via API
```bash
# POST request to train Random Forest
curl -X POST "http://localhost:8000/models/train/rf" \
  -H "Content-Type: application/json" \
  -d '{
    "csv_path": "data/All_Labelled.csv",
    "label_col": "Label",
    "n_estimators": 100,
    "max_depth": 30
  }'
```

### Predict with RF
```bash
# POST request for prediction
curl -X POST "http://localhost:8000/models/predict/rf" \
  -H "Content-Type: application/json" \
  -d '{
    "features": [[...feature_values...]]
  }'
```

### Get Model Info
```bash
# GET request for model information
curl http://localhost:8000/models/rf/info
```

### Get Feature Importance
```bash
# GET request for feature importance ranking
curl http://localhost:8000/models/rf/feature_importance?top_n=20
```

### Compare RF vs ANN
```bash
# POST request to compare models
curl -X POST "http://localhost:8000/models/compare/rf_vs_ann" \
  -H "Content-Type: application/json" \
  -d '{
    "test_data_path": "data/All_Labelled.csv"
  }'
```

### Tune Model via API
```bash
# POST request to tune Random Forest
curl -X POST "http://localhost:8000/models/tune/random_forest" \
  -H "Content-Type: application/json" \
  -d '{
    "csv_path": "data/All_Labelled.csv",
    "method": "optuna",
    "n_trials": 50
  }'
```

### Get Best Parameters
```bash
# GET request for saved best parameters
curl http://localhost:8000/models/best_params/random_forest
```

---

## Python API Examples

### Feature Importance Analysis
```python
trainer = RandomForestTrainer()
trainer.load_model()

# Get top 10 most important features
importance = trainer.get_feature_importance(top_n=10)

for feature, score in importance:
    print(f"{feature}: {score:.4f}")
```

### Batch Prediction
```python
import pandas as pd

# Load model
trainer = RandomForestTrainer()
trainer.load_model()

# Load large dataset
df = pd.read_csv('traffic_log.csv')
X = df.drop(columns=['Label'])

# Batch predict
predictions = trainer.predict(X)
probabilities = trainer.predict_proba(X)

# Add predictions to dataframe
df['prediction'] = predictions
df['confidence'] = probabilities.max(axis=1)

# Save results
df.to_csv('predictions.csv', index=False)
```

### Model Comparison
```python
from models.random_forest_trainer import RandomForestTrainer

trainer = RandomForestTrainer()
trainer.load_model()

# Compare with ANN
comparison = trainer.compare_with_ann(
    ann_model_path='models/ann_model.h5',
    X_test=X_test,
    y_test=y_test
)

print(f"RF Accuracy: {comparison['random_forest']['accuracy']}")
print(f"ANN Accuracy: {comparison['ann']['accuracy']}")
print(f"Winner: {comparison['winner']}")
```

---

## Configuration

### Model Parameters

**Random Forest:**
- `n_estimators`: 50-500 (default: 100)
- `max_depth`: 10-100 or None (default: 30)
- `min_samples_split`: 2-20 (default: 2)
- `min_samples_leaf`: 1-10 (default: 1)
- `class_weight`: 'balanced' or None (default: 'balanced')

**Hyperparameter Tuning:**
- `n_trials`: 10-200 (default: 100)
- `timeout`: 600-7200 seconds (default: 3600)
- `n_jobs`: 1 to CPU_count (default: -1 for all CPUs)

### File Locations

- **Model**: `models/random_forest_model.joblib`
- **Best Params**: `models/best_params.json`
- **Classification Report**: `models/classification_report_rf.txt`
- **Training Data**: `data/All_Labelled.csv`

---

## Troubleshooting

### Model Loading Errors
```python
# Check if model exists
import os
model_path = 'models/random_forest_model.joblib'
print(f"Model exists: {os.path.exists(model_path)}")

# If not, train first
from models.random_forest_trainer import train_from_csv
trainer, _, _ = train_from_csv('data/All_Labelled.csv', label_col='Label')
```

### Prediction Errors
```python
# Ensure categorical features are encoded
trainer = RandomForestTrainer()
trainer.load_model()

# If X is DataFrame with categorical columns
if isinstance(X, pd.DataFrame):
    X_encoded = trainer._encode_categorical_features(X, is_training=False)
    predictions = trainer.predict(X_encoded.values)
```

### Memory Issues with Large Datasets
```python
# Use chunking for large files
chunk_size = 10000
predictions = []

for chunk in pd.read_csv('large_file.csv', chunksize=chunk_size):
    X_chunk = chunk.drop(columns=['Label'])
    pred_chunk = trainer.predict(X_chunk)
    predictions.extend(pred_chunk)
```

---

## Performance Tips

1. **Parallel Processing**: Use `n_jobs=-1` to utilize all CPU cores
2. **Feature Selection**: Remove low-importance features to speed up training
3. **Model Caching**: Load model once and reuse for multiple predictions
4. **Batch Processing**: Predict in batches rather than one-by-one
5. **Parameter Tuning**: Start with fewer trials (20-30) for quick iterations

---

## Best Practices

✅ **Always validate** model performance on held-out test set  
✅ **Use cross-validation** when comparing hyperparameters  
✅ **Monitor** feature importance to understand model decisions  
✅ **Retrain periodically** with new data to maintain accuracy  
✅ **Save best parameters** from tuning for reproducibility  
✅ **Log predictions** with confidence scores for analysis  

---

## Additional Resources

- **Full Documentation**: `FINAL_IMPLEMENTATION_SUMMARY.md`
- **Deployment Guide**: `DEPLOYMENT_REPORT.md`
- **API Reference**: See `/docs` endpoint when server is running
- **Test Examples**: `test_deployment.py`

**Happy Training!** 🚀
