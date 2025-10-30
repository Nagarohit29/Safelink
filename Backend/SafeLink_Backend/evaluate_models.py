"""
Comprehensive Model Evaluation Script

Generates evaluation metrics, confusion matrices, training curves, and ROC-AUC plots
for both Random Forest and ANN models with high-quality visualizations (DPI=300).
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import (
    confusion_matrix, classification_report, roc_curve, auc,
    precision_recall_curve, accuracy_score, precision_score, 
    recall_score, f1_score
)
from sklearn.model_selection import train_test_split
import json

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10

# Directories
MODELS_DIR = Path("models")
PLOTS_DIR = MODELS_DIR / "evaluation_plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset(csv_path='data/All_Labelled.csv', label_col='Label', test_size=0.2):
    """Load and split dataset."""
    print(f"\n{'='*60}")
    print("Loading Dataset")
    print(f"{'='*60}")
    
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded {len(df):,} samples")
    print(f"   Features: {len(df.columns) - 1}")
    print(f"   Classes: {sorted(df[label_col].unique())}")
    
    # Class distribution
    print(f"\n   Class Distribution:")
    for label, count in df[label_col].value_counts().items():
        print(f"     {label}: {count:,} ({count/len(df)*100:.1f}%)")
    
    # Split
    X = df.drop(columns=[label_col])
    y = df[label_col].values
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    print(f"\n   Split: {len(X_train):,} train, {len(X_test):,} test")
    
    return X_train, X_test, y_train, y_test, df


def evaluate_random_forest(X_train, X_test, y_train, y_test):
    """Evaluate Random Forest model."""
    print(f"\n{'='*60}")
    print("Evaluating Random Forest Model")
    print(f"{'='*60}")
    
    from models.random_forest_trainer import RandomForestTrainer
    
    # Load model
    trainer = RandomForestTrainer()
    try:
        trainer.load_model()
        print("✅ Model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return None
    
    # Encode test labels if they're strings
    if trainer.target_encoder and (y_test.dtype == object or isinstance(y_test[0], str)):
        y_test_encoded = trainer.target_encoder.transform(y_test)
        class_names = trainer.target_encoder.classes_
    else:
        y_test_encoded = y_test
        class_names = np.unique(y_test)
    
    # Encode categorical features for test set (BEFORE converting to array)
    if isinstance(X_test, pd.DataFrame):
        X_test_encoded = trainer._encode_categorical_features(X_test, is_training=False)
        X_test_array = X_test_encoded.values
    else:
        X_test_array = X_test
    
    # Scale features
    X_test_scaled = trainer.scaler.transform(X_test_array)
    
    # Predictions
    y_pred = trainer.model.predict(X_test_scaled)
    y_pred_proba = trainer.model.predict_proba(X_test_scaled)
    
    # Decode predictions for display
    if trainer.target_encoder:
        y_test_decoded = y_test  # Original string labels
        y_pred_decoded = trainer.target_encoder.inverse_transform(y_pred)
    else:
        y_test_decoded = y_test
        y_pred_decoded = y_pred
    
    # Metrics
    metrics = {
        'accuracy': accuracy_score(y_test_encoded, y_pred),
        'precision': precision_score(y_test_encoded, y_pred, average='binary'),
        'recall': recall_score(y_test_encoded, y_pred, average='binary'),
        'f1_score': f1_score(y_test_encoded, y_pred, average='binary')
    }
    
    print(f"\n   Performance Metrics:")
    print(f"     Accuracy:  {metrics['accuracy']:.4f}")
    print(f"     Precision: {metrics['precision']:.4f}")
    print(f"     Recall:    {metrics['recall']:.4f}")
    print(f"     F1 Score:  {metrics['f1_score']:.4f}")
    
    # Generate plots
    print(f"\n   Generating visualizations...")
    
    # 1. Confusion Matrix
    plot_confusion_matrix(
        y_test_decoded, y_pred_decoded, class_names,
        "Random Forest - Confusion Matrix",
        PLOTS_DIR / "rf_confusion_matrix.png"
    )
    
    # 2. ROC Curve
    plot_roc_curve(
        y_test_encoded, y_pred_proba, class_names,
        "Random Forest - ROC Curve",
        PLOTS_DIR / "rf_roc_curve.png"
    )
    
    # 3. Feature Importance
    plot_feature_importance(
        trainer, top_n=20,
        title="Random Forest - Top 20 Feature Importance",
        save_path=PLOTS_DIR / "rf_feature_importance.png"
    )
    
    # 4. Classification Report
    report = classification_report(y_test_decoded, y_pred_decoded, output_dict=True)
    plot_classification_report(
        report, class_names,
        "Random Forest - Classification Report",
        PLOTS_DIR / "rf_classification_report.png"
    )
    
    # Save metrics
    metrics_data = {
        'model': 'Random Forest',
        'metrics': metrics,
        'classification_report': report,
        'n_estimators': trainer.model.n_estimators,
        'max_depth': trainer.model.max_depth,
        'test_samples': len(y_test)
    }
    
    with open(PLOTS_DIR / "rf_metrics.json", 'w') as f:
        json.dump(metrics_data, f, indent=2)
    
    print(f"   ✅ Saved 4 visualizations to {PLOTS_DIR}/")
    
    return metrics


def evaluate_ann(X_train, X_test, y_train, y_test):
    """Evaluate ANN model."""
    print(f"\n{'='*60}")
    print("Evaluating ANN Model")
    print(f"{'='*60}")
    
    from core.ann_classifier import ANNDetector
    import torch
    from pathlib import Path
    
    # Check if model exists
    model_path = MODELS_DIR / "ann_model.pt"
    if not model_path.exists():
        print(f"⚠️  ANN model not found at {model_path}")
        print("   Skipping ANN evaluation")
        return None
    
    try:
        # Load model (automatically loads in __init__)
        detector = ANNDetector(model_path=str(model_path))
        print("✅ Model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return None
    
    # Prepare data - use only numeric columns that model was trained on
    if isinstance(X_test, pd.DataFrame):
        # Get numeric columns matching the model's expected input
        X_test_numeric = X_test[detector.numeric_cols].values
    else:
        X_test_numeric = X_test
    
    # Encode labels
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    y_test_encoded = le.fit_transform(y_test)
    class_names = le.classes_
    
    # Predictions using batch predict
    predictions = detector.predict_batch(X_test_numeric)
    y_pred = np.array([pred for pred, _ in predictions])
    y_pred_proba_pos = np.array([prob for _, prob in predictions])
    
    # Create probability array for both classes
    y_pred_proba = np.column_stack([1 - y_pred_proba_pos, y_pred_proba_pos])
    
    # Decode predictions
    y_test_decoded = le.inverse_transform(y_test_encoded)
    y_pred_decoded = le.inverse_transform(y_pred)
    
    # Metrics
    metrics = {
        'accuracy': accuracy_score(y_test_encoded, y_pred),
        'precision': precision_score(y_test_encoded, y_pred, average='binary'),
        'recall': recall_score(y_test_encoded, y_pred, average='binary'),
        'f1_score': f1_score(y_test_encoded, y_pred, average='binary')
    }
    
    print(f"\n   Performance Metrics:")
    print(f"     Accuracy:  {metrics['accuracy']:.4f}")
    print(f"     Precision: {metrics['precision']:.4f}")
    print(f"     Recall:    {metrics['recall']:.4f}")
    print(f"     F1 Score:  {metrics['f1_score']:.4f}")
    
    # Generate plots
    print(f"\n   Generating visualizations...")
    
    # 1. Confusion Matrix
    plot_confusion_matrix(
        y_test_decoded, y_pred_decoded, class_names,
        "ANN - Confusion Matrix",
        PLOTS_DIR / "ann_confusion_matrix.png"
    )
    
    # 2. ROC Curve
    plot_roc_curve(
        y_test_encoded, y_pred_proba, class_names,
        "ANN - ROC Curve",
        PLOTS_DIR / "ann_roc_curve.png"
    )
    
    # 3. Training History (if available)
    history_path = MODELS_DIR / "training_history.json"
    if history_path.exists():
        try:
            with open(history_path, 'r') as f:
                history = json.load(f)
            plot_training_curves(
                history,
                "ANN - Training History",
                PLOTS_DIR / "ann_training_curves.png"
            )
            print("   ✅ Training curves plotted")
        except Exception as e:
            print(f"   ⚠️  Could not plot training history: {e}")
    else:
        print(f"   ⚠️  Training history not found at {history_path}")
    
    # 4. Classification Report
    report = classification_report(y_test_decoded, y_pred_decoded, output_dict=True)
    plot_classification_report(
        report, class_names,
        "ANN - Classification Report",
        PLOTS_DIR / "ann_classification_report.png"
    )
    
    # Save metrics
    metrics_data = {
        'model': 'ANN',
        'metrics': metrics,
        'classification_report': report,
        'test_samples': len(y_test),
        'input_features': len(detector.numeric_cols)
    }
    
    with open(PLOTS_DIR / "ann_metrics.json", 'w') as f:
        json.dump(metrics_data, f, indent=2)
    
    print(f"   ✅ Saved visualizations to {PLOTS_DIR}/")
    
    return metrics


def plot_confusion_matrix(y_true, y_pred, class_names, title, save_path):
    """Plot confusion matrix with high quality."""
    cm = confusion_matrix(y_true, y_pred)
    
    # Normalize
    cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Absolute counts
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=class_names, yticklabels=class_names,
                ax=ax1, cbar_kws={'label': 'Count'})
    ax1.set_title(f'{title} (Counts)')
    ax1.set_ylabel('True Label')
    ax1.set_xlabel('Predicted Label')
    
    # Normalized
    sns.heatmap(cm_normalized, annot=True, fmt='.2%', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names,
                ax=ax2, cbar_kws={'label': 'Percentage'})
    ax2.set_title(f'{title} (Normalized)')
    ax2.set_ylabel('True Label')
    ax2.set_xlabel('Predicted Label')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_roc_curve(y_true, y_pred_proba, class_names, title, save_path):
    """Plot ROC curve with AUC."""
    # Handle binary classification
    if len(class_names) == 2:
        # Get probabilities for positive class
        if y_pred_proba.ndim == 2:
            y_scores = y_pred_proba[:, 1]
        else:
            y_scores = y_pred_proba
        
        # Compute ROC curve
        fpr, tpr, _ = roc_curve(y_true, y_scores, pos_label=1)
        roc_auc = auc(fpr, tpr)
        
        # Plot
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(fpr, tpr, color='darkorange', lw=2,
                label=f'ROC curve (AUC = {roc_auc:.4f})')
        ax.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--',
                label='Random Classifier')
        
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title(title)
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()


def plot_feature_importance(trainer, top_n=20, title="Feature Importance", save_path=None):
    """Plot feature importance for Random Forest."""
    importance_dict = trainer.get_feature_importance()
    
    # Get top N
    sorted_items = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:top_n]
    features, scores = zip(*sorted_items)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    y_pos = np.arange(len(features))
    
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(features)))
    ax.barh(y_pos, scores, color=colors)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(features)
    ax.invert_yaxis()
    ax.set_xlabel('Importance Score')
    ax.set_title(title)
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_classification_report(report_dict, class_names, title, save_path):
    """Plot classification report as heatmap."""
    # Extract metrics
    metrics = ['precision', 'recall', 'f1-score']
    data = []
    
    for class_name in class_names:
        if str(class_name) in report_dict:
            row = [report_dict[str(class_name)][m] for m in metrics]
            data.append(row)
    
    data = np.array(data)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    
    # Set ticks
    ax.set_xticks(np.arange(len(metrics)))
    ax.set_yticks(np.arange(len(class_names)))
    ax.set_xticklabels(metrics)
    ax.set_yticklabels(class_names)
    
    # Rotate x labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Add text annotations
    for i in range(len(class_names)):
        for j in range(len(metrics)):
            text = ax.text(j, i, f'{data[i, j]:.3f}',
                          ha="center", va="center", color="black", fontsize=12)
    
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label='Score')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_training_curves(history, title, save_path):
    """Plot training and validation loss/accuracy curves."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    epochs = range(1, len(history.get('train_loss', [])) + 1)
    
    # Loss curve
    if 'train_loss' in history:
        ax1.plot(epochs, history['train_loss'], 'b-', label='Training Loss', linewidth=2)
    if 'val_loss' in history:
        ax1.plot(epochs, history['val_loss'], 'r-', label='Validation Loss', linewidth=2)
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.set_title('Training and Validation Loss')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Accuracy curve
    if 'train_acc' in history:
        ax2.plot(epochs, history['train_acc'], 'b-', label='Training Accuracy', linewidth=2)
    if 'val_acc' in history:
        ax2.plot(epochs, history['val_acc'], 'r-', label='Validation Accuracy', linewidth=2)
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy')
    ax2.set_title('Training and Validation Accuracy')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.suptitle(title, fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def compare_models(rf_metrics, ann_metrics):
    """Compare RF and ANN models visually."""
    if not rf_metrics or not ann_metrics:
        print("\n⚠️  Skipping model comparison (missing metrics)")
        return
    
    print(f"\n{'='*60}")
    print("Model Comparison")
    print(f"{'='*60}")
    
    metrics = ['accuracy', 'precision', 'recall', 'f1_score']
    rf_scores = [rf_metrics[m] for m in metrics]
    ann_scores = [ann_metrics[m] for m in metrics]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, rf_scores, width, label='Random Forest',
                   color='skyblue', edgecolor='black')
    bars2 = ax.bar(x + width/2, ann_scores, width, label='ANN',
                   color='lightcoral', edgecolor='black')
    
    ax.set_ylabel('Score')
    ax.set_title('Random Forest vs ANN - Performance Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels([m.replace('_', ' ').title() for m in metrics])
    ax.legend()
    ax.set_ylim([0, 1.1])
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.3f}',
                   ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "model_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Print comparison
    print(f"\n   Metric Comparison:")
    print(f"   {'Metric':<15} {'Random Forest':<15} {'ANN':<15} {'Winner':<10}")
    print(f"   {'-'*55}")
    for i, metric in enumerate(metrics):
        rf_score = rf_scores[i]
        ann_score = ann_scores[i]
        winner = "RF" if rf_score > ann_score else "ANN" if ann_score > rf_score else "Tie"
        print(f"   {metric.replace('_', ' ').title():<15} {rf_score:<15.4f} {ann_score:<15.4f} {winner:<10}")
    
    print(f"\n   ✅ Saved comparison plot to {PLOTS_DIR}/model_comparison.png")


def main():
    """Main evaluation function."""
    print(f"\n{'='*60}")
    print("🎯 COMPREHENSIVE MODEL EVALUATION")
    print(f"{'='*60}")
    print(f"\nOutput directory: {PLOTS_DIR.absolute()}")
    print(f"DPI: 300 (High Quality)")
    
    # Load dataset
    X_train, X_test, y_train, y_test, df = load_dataset()
    
    # Evaluate Random Forest
    rf_metrics = evaluate_random_forest(X_train, X_test, y_train, y_test)
    
    # Evaluate ANN
    ann_metrics = evaluate_ann(X_train, X_test, y_train, y_test)
    
    # Compare models
    if rf_metrics and ann_metrics:
        compare_models(rf_metrics, ann_metrics)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 EVALUATION COMPLETE")
    print(f"{'='*60}")
    print(f"\nGenerated Files:")
    
    plot_files = sorted(PLOTS_DIR.glob("*.png"))
    for i, plot_file in enumerate(plot_files, 1):
        print(f"  {i}. {plot_file.name}")
    
    json_files = sorted(PLOTS_DIR.glob("*.json"))
    for i, json_file in enumerate(json_files, len(plot_files) + 1):
        print(f"  {i}. {json_file.name}")
    
    print(f"\n✨ All visualizations saved to: {PLOTS_DIR.absolute()}")
    print(f"✨ Total files generated: {len(plot_files) + len(json_files)}")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
