"""
Dataset Balancing Tools API

Standalone API/CLI tool for class balancing operations.
Supports SMOTE, random sampling, and class weights.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, Literal
import argparse
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class DatasetBalancer:
    """
    Standalone dataset balancing tool.
    
    Supports:
    - Random undersampling
    - Random oversampling
    - SMOTE (if available)
    - Class weight computation
    """
    
    def __init__(self):
        """Initialize dataset balancer."""
        self.has_smote = self._check_smote()
        logger.info(f"DatasetBalancer initialized (SMOTE available: {self.has_smote})")
    
    def _check_smote(self) -> bool:
        """Check if imbalanced-learn is available."""
        try:
            from imblearn.over_sampling import SMOTE
            return True
        except ImportError:
            return False
    
    def undersample(self, df: pd.DataFrame, label_col: str = 'label',
                   target_ratio: float = 1.0, random_state: int = 42) -> pd.DataFrame:
        """
        Random undersampling of majority class.
        
        Args:
            df: Input DataFrame
            label_col: Label column name
            target_ratio: Target minority/majority ratio (1.0 = balanced)
            random_state: Random seed
            
        Returns:
            Undersampled DataFrame
        """
        class_counts = df[label_col].value_counts()
        minority_class = class_counts.idxmin()
        majority_class = class_counts.idxmax()
        
        minority_count = class_counts[minority_class]
        target_majority_count = int(minority_count / target_ratio)
        
        # Split by class
        minority_df = df[df[label_col] == minority_class]
        majority_df = df[df[label_col] == majority_class]
        
        # Undersample majority
        majority_sampled = majority_df.sample(n=min(target_majority_count, len(majority_df)),
                                             random_state=random_state)
        
        # Combine
        balanced_df = pd.concat([minority_df, majority_sampled], ignore_index=True)
        
        logger.info(f"Undersampled: {len(df)} -> {len(balanced_df)} samples")
        return balanced_df
    
    def oversample(self, df: pd.DataFrame, label_col: str = 'label',
                  target_ratio: float = 1.0, random_state: int = 42) -> pd.DataFrame:
        """
        Random oversampling of minority class.
        
        Args:
            df: Input DataFrame
            label_col: Label column name
            target_ratio: Target minority/majority ratio (1.0 = balanced)
            random_state: Random seed
            
        Returns:
            Oversampled DataFrame
        """
        class_counts = df[label_col].value_counts()
        minority_class = class_counts.idxmin()
        majority_class = class_counts.idxmax()
        
        majority_count = class_counts[majority_class]
        target_minority_count = int(majority_count * target_ratio)
        
        # Split by class
        minority_df = df[df[label_col] == minority_class]
        majority_df = df[df[label_col] == majority_class]
        
        # Oversample minority with replacement
        minority_sampled = minority_df.sample(n=target_minority_count,
                                             replace=True,
                                             random_state=random_state)
        
        # Combine
        balanced_df = pd.concat([majority_df, minority_sampled], ignore_index=True)
        
        logger.info(f"Oversampled: {len(df)} -> {len(balanced_df)} samples")
        return balanced_df
    
    def smote(self, df: pd.DataFrame, label_col: str = 'label',
             target_ratio: float = 1.0, k_neighbors: int = 5,
             random_state: int = 42) -> pd.DataFrame:
        """
        SMOTE (Synthetic Minority Oversampling Technique).
        
        Args:
            df: Input DataFrame
            label_col: Label column name
            target_ratio: Target minority/majority ratio (1.0 = balanced)
            k_neighbors: Number of nearest neighbors for SMOTE
            random_state: Random seed
            
        Returns:
            SMOTE-balanced DataFrame
        """
        if not self.has_smote:
            logger.error("SMOTE requires imbalanced-learn: pip install imbalanced-learn")
            raise ImportError("imbalanced-learn not available")
        
        from imblearn.over_sampling import SMOTE as SMOTESampler
        
        X = df.drop(columns=[label_col])
        y = df[label_col]
        
        # Apply SMOTE
        smote_sampler = SMOTESampler(
            sampling_strategy=target_ratio,
            k_neighbors=k_neighbors,
            random_state=random_state
        )
        
        X_resampled, y_resampled = smote_sampler.fit_resample(X, y)
        
        # Reconstruct DataFrame
        balanced_df = pd.DataFrame(X_resampled, columns=X.columns)
        balanced_df[label_col] = y_resampled
        
        logger.info(f"SMOTE balanced: {len(df)} -> {len(balanced_df)} samples")
        return balanced_df
    
    def compute_class_weights(self, df: pd.DataFrame, 
                             label_col: str = 'label') -> Dict[int, float]:
        """
        Compute class weights for imbalanced datasets.
        
        Args:
            df: Input DataFrame
            label_col: Label column name
            
        Returns:
            Dict mapping class labels to weights
        """
        class_counts = df[label_col].value_counts()
        total_samples = len(df)
        n_classes = len(class_counts)
        
        # weight = total_samples / (n_classes * class_count)
        weights = {}
        for class_label, count in class_counts.items():
            weights[int(class_label)] = total_samples / (n_classes * count)
        
        logger.info(f"Computed class weights: {weights}")
        return weights
    
    def balance(self, df: pd.DataFrame, method: Literal['undersample', 'oversample', 'smote'],
               label_col: str = 'label', target_ratio: float = 1.0,
               **kwargs) -> pd.DataFrame:
        """
        Balance dataset using specified method.
        
        Args:
            df: Input DataFrame
            method: Balancing method
            label_col: Label column name
            target_ratio: Target minority/majority ratio
            **kwargs: Additional method-specific parameters
            
        Returns:
            Balanced DataFrame
        """
        if method == 'undersample':
            return self.undersample(df, label_col, target_ratio, **kwargs)
        elif method == 'oversample':
            return self.oversample(df, label_col, target_ratio, **kwargs)
        elif method == 'smote':
            return self.smote(df, label_col, target_ratio, **kwargs)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def analyze_balance(self, df: pd.DataFrame, label_col: str = 'label') -> Dict:
        """
        Analyze class balance in dataset.
        
        Args:
            df: Input DataFrame
            label_col: Label column name
            
        Returns:
            Balance analysis report
        """
        class_counts = df[label_col].value_counts()
        
        if len(class_counts) < 2:
            return {
                "error": "Need at least 2 classes",
                "class_counts": class_counts.to_dict()
            }
        
        majority_count = class_counts.max()
        minority_count = class_counts.min()
        imbalance_ratio = minority_count / majority_count
        
        return {
            "total_samples": len(df),
            "n_classes": len(class_counts),
            "class_distribution": class_counts.to_dict(),
            "majority_class": int(class_counts.idxmax()),
            "minority_class": int(class_counts.idxmin()),
            "majority_count": int(majority_count),
            "minority_count": int(minority_count),
            "imbalance_ratio": float(imbalance_ratio),
            "is_balanced": imbalance_ratio >= 0.8,  # 80% threshold
            "class_weights": self.compute_class_weights(df, label_col)
        }


def cli_main():
    """Command-line interface for dataset balancing."""
    parser = argparse.ArgumentParser(description="Dataset Balancing Tool")
    
    parser.add_argument('input_file', type=str, help="Input CSV file")
    parser.add_argument('--output', '-o', type=str, help="Output CSV file")
    parser.add_argument('--method', '-m', type=str, 
                       choices=['undersample', 'oversample', 'smote'],
                       default='oversample',
                       help="Balancing method")
    parser.add_argument('--label-col', type=str, default='label',
                       help="Label column name")
    parser.add_argument('--target-ratio', type=float, default=1.0,
                       help="Target minority/majority ratio (1.0 = balanced)")
    parser.add_argument('--analyze-only', action='store_true',
                       help="Only analyze balance, don't resample")
    parser.add_argument('--random-state', type=int, default=42,
                       help="Random seed")
    
    args = parser.parse_args()
    
    # Load dataset
    print(f"Loading dataset: {args.input_file}")
    df = pd.read_csv(args.input_file)
    print(f"Loaded {len(df)} samples")
    
    # Initialize balancer
    balancer = DatasetBalancer()
    
    # Analyze
    print("\n" + "="*60)
    print("CLASS BALANCE ANALYSIS")
    print("="*60)
    analysis = balancer.analyze_balance(df, args.label_col)
    
    for key, value in analysis.items():
        if key != "class_weights":
            print(f"{key}: {value}")
    
    print("\nClass Weights:")
    for class_label, weight in analysis["class_weights"].items():
        print(f"  Class {class_label}: {weight:.4f}")
    
    if args.analyze_only:
        sys.exit(0)
    
    # Balance
    print("\n" + "="*60)
    print(f"BALANCING WITH METHOD: {args.method.upper()}")
    print("="*60)
    
    balanced_df = balancer.balance(
        df,
        method=args.method,
        label_col=args.label_col,
        target_ratio=args.target_ratio,
        random_state=args.random_state
    )
    
    # Analyze balanced dataset
    print("\nBalanced Dataset Analysis:")
    balanced_analysis = balancer.analyze_balance(balanced_df, args.label_col)
    print(f"Total samples: {balanced_analysis['total_samples']}")
    print(f"Imbalance ratio: {balanced_analysis['imbalance_ratio']:.4f}")
    print(f"Class distribution: {balanced_analysis['class_distribution']}")
    
    # Save
    if args.output:
        output_file = args.output
    else:
        input_path = Path(args.input_file)
        output_file = input_path.parent / f"{input_path.stem}_balanced.csv"
    
    balanced_df.to_csv(output_file, index=False)
    print(f"\nSaved balanced dataset to: {output_file}")


# Global instance
_balancer = None


def get_balancer() -> DatasetBalancer:
    """Get singleton balancer instance."""
    global _balancer
    if _balancer is None:
        _balancer = DatasetBalancer()
    return _balancer


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli_main()
