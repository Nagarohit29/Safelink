"""
Model Evaluation Results Summary

Displays comprehensive evaluation results for Random Forest and ANN models.
"""

import json
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt

PLOTS_DIR = Path("models/evaluation_plots")


def print_separator(char='=', length=70):
    """Print a separator line."""
    print(char * length)


def display_metrics(model_name, metrics_file):
    """Display metrics from JSON file."""
    if not metrics_file.exists():
        print(f"⚠️  Metrics file not found: {metrics_file}")
        return None
    
    with open(metrics_file, 'r') as f:
        data = json.load(f)
    
    print(f"\n📊 {model_name} Model Evaluation")
    print_separator()
    
    metrics = data['metrics']
    print(f"\nPerformance Metrics:")
    print(f"  Accuracy:  {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
    print(f"  Precision: {metrics['precision']:.4f} ({metrics['precision']*100:.2f}%)")
    print(f"  Recall:    {metrics['recall']:.4f} ({metrics['recall']*100:.2f}%)")
    print(f"  F1 Score:  {metrics['f1_score']:.4f} ({metrics['f1_score']*100:.2f}%)")
    
    if 'classification_report' in data:
        report = data['classification_report']
        print(f"\nPer-Class Performance:")
        for class_name in ['arp_spoofing', 'normal']:
            if class_name in report:
                class_metrics = report[class_name]
                print(f"\n  {class_name.upper()}:")
                print(f"    Precision: {class_metrics['precision']:.4f}")
                print(f"    Recall:    {class_metrics['recall']:.4f}")
                print(f"    F1-Score:  {class_metrics['f1-score']:.4f}")
                print(f"    Support:   {class_metrics['support']}")
    
    if 'n_estimators' in data:
        print(f"\nModel Configuration:")
        print(f"  Trees: {data['n_estimators']}")
        print(f"  Max Depth: {data['max_depth']}")
    
    if 'input_features' in data:
        print(f"\nModel Configuration:")
        print(f"  Input Features: {data['input_features']}")
    
    print(f"\nTest Set: {data['test_samples']:,} samples")
    
    return metrics


def list_visualizations():
    """List all generated visualization files."""
    print(f"\n🎨 Generated Visualizations")
    print_separator()
    
    plot_files = sorted(PLOTS_DIR.glob("*.png"))
    
    if not plot_files:
        print("⚠️  No visualization files found!")
        return
    
    print(f"\nHigh-Quality Images (DPI=300):")
    print(f"Location: {PLOTS_DIR.absolute()}\n")
    
    rf_plots = [f for f in plot_files if f.name.startswith('rf_')]
    ann_plots = [f for f in plot_files if f.name.startswith('ann_')]
    comparison_plots = [f for f in plot_files if 'comparison' in f.name]
    
    if rf_plots:
        print("Random Forest Visualizations:")
        for i, plot_file in enumerate(rf_plots, 1):
            size = plot_file.stat().st_size / 1024  # KB
            print(f"  {i}. {plot_file.name:<40} ({size:>7.1f} KB)")
    
    if ann_plots:
        print("\nANN Visualizations:")
        for i, plot_file in enumerate(ann_plots, 1):
            size = plot_file.stat().st_size / 1024  # KB
            print(f"  {i}. {plot_file.name:<40} ({size:>7.1f} KB)")
    
    if comparison_plots:
        print("\nModel Comparison:")
        for i, plot_file in enumerate(comparison_plots, 1):
            size = plot_file.stat().st_size / 1024  # KB
            print(f"  {i}. {plot_file.name:<40} ({size:>7.1f} KB)")


def compare_models(rf_metrics, ann_metrics):
    """Compare model performance."""
    if not rf_metrics or not ann_metrics:
        return
    
    print(f"\n⚖️  Model Comparison")
    print_separator()
    
    metrics_names = ['accuracy', 'precision', 'recall', 'f1_score']
    
    print(f"\n{'Metric':<15} {'Random Forest':<18} {'ANN':<18} {'Winner':<10} {'Diff':<10}")
    print_separator('-')
    
    for metric in metrics_names:
        rf_val = rf_metrics[metric]
        ann_val = ann_metrics[metric]
        diff = abs(rf_val - ann_val)
        winner = "RF" if rf_val > ann_val else "ANN" if ann_val > rf_val else "Tie"
        
        print(f"{metric.replace('_', ' ').title():<15} "
              f"{rf_val:<18.4f} "
              f"{ann_val:<18.4f} "
              f"{winner:<10} "
              f"±{diff:.4f}")
    
    # Overall winner
    rf_wins = sum(1 for m in metrics_names if rf_metrics[m] > ann_metrics[m])
    ann_wins = sum(1 for m in metrics_names if ann_metrics[m] > rf_metrics[m])
    
    print(f"\n{'='*70}")
    if rf_wins > ann_wins:
        print(f"🏆 Overall Winner: Random Forest ({rf_wins}/4 metrics)")
    elif ann_wins > rf_wins:
        print(f"🏆 Overall Winner: ANN ({ann_wins}/4 metrics)")
    else:
        print(f"🏆 Overall Result: Tie")


def main():
    """Main summary function."""
    print(f"\n{'='*70}")
    print("📈 MODEL EVALUATION RESULTS SUMMARY")
    print(f"{'='*70}")
    
    # Display RF metrics
    rf_metrics = display_metrics(
        "Random Forest",
        PLOTS_DIR / "rf_metrics.json"
    )
    
    # Display ANN metrics
    ann_metrics = display_metrics(
        "ANN",
        PLOTS_DIR / "ann_metrics.json"
    )
    
    # Compare models
    if rf_metrics and ann_metrics:
        compare_models(rf_metrics, ann_metrics)
    
    # List visualizations
    list_visualizations()
    
    print(f"\n{'='*70}")
    print("✅ EVALUATION SUMMARY COMPLETE")
    print(f"{'='*70}")
    print(f"\n📂 View all visualizations in: {PLOTS_DIR.absolute()}")
    print(f"💾 All images saved with DPI=300 for publication quality\n")


if __name__ == "__main__":
    main()
