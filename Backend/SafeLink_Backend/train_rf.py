"""
Train Random Forest Model
"""
from models.random_forest_trainer import train_from_csv

print("Starting Random Forest training...")
print("Dataset: data/All_Labelled.csv")
print("=" * 60)

trainer, train_metrics, test_metrics = train_from_csv(
    csv_path='data/All_Labelled.csv',
    label_col='Label',  # Correct column name
    test_size=0.2,
    n_estimators=100,
    max_depth=30,
    class_weight='balanced',
    random_state=42
)

print("\n" + "=" * 60)
print("TRAINING COMPLETE")
print("=" * 60)
print(f"\nTraining Metrics:")
print(f"  Accuracy: {train_metrics['accuracy']:.4f}")
print(f"  Precision: {train_metrics['precision']:.4f}")
print(f"  Recall: {train_metrics['recall']:.4f}")
print(f"  F1 Score: {train_metrics['f1_score']:.4f}")
if 'roc_auc' in train_metrics:
    print(f"  ROC-AUC: {train_metrics['roc_auc']:.4f}")
print(f"  CV Accuracy: {train_metrics['cv_accuracy_mean']:.4f} ± {train_metrics['cv_accuracy_std']:.4f}")

print(f"\nTest Metrics:")
print(f"  Accuracy: {test_metrics['accuracy']:.4f}")
print(f"  Precision: {test_metrics['precision']:.4f}")
print(f"  Recall: {test_metrics['recall']:.4f}")
print(f"  F1 Score: {test_metrics['f1_score']:.4f}")
if 'roc_auc' in test_metrics:
    print(f"  ROC-AUC: {test_metrics['roc_auc']:.4f}")

print(f"\nModel saved to: models/random_forest_model.joblib")
print(f"Classification report saved to: models/classification_report_rf.txt")
print("=" * 60)
