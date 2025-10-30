"""
Automated Data Curation Pipeline

Provides tools for cleaning, validating, and curating training data from alerts.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)


class DataCurator:
    """
    Automated data curation pipeline for ML training data.
    
    Features:
    - Duplicate removal
    - Label validation
    - Class balancing
    - Quality metrics
    - Data versioning
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize data curator.
        
        Args:
            output_dir: Directory to save curated datasets
        """
        self.output_dir = output_dir or Path("data/curated")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            "total_samples": 0,
            "duplicates_removed": 0,
            "invalid_labels": 0,
            "missing_values": 0,
            "outliers_removed": 0,
            "class_distribution": {},
            "feature_stats": {}
        }
        
        logger.info(f"DataCurator initialized, output_dir={self.output_dir}")
    
    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate rows from dataset.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with duplicates removed
        """
        initial_count = len(df)
        df_clean = df.drop_duplicates()
        duplicates = initial_count - len(df_clean)
        
        self.stats["duplicates_removed"] = duplicates
        
        if duplicates > 0:
            logger.info(f"Removed {duplicates} duplicate samples ({duplicates/initial_count*100:.2f}%)")
        
        return df_clean
    
    def validate_labels(self, df: pd.DataFrame, label_col: str = 'label') -> pd.DataFrame:
        """
        Validate and clean label column.
        
        Args:
            df: Input DataFrame
            label_col: Name of label column
            
        Returns:
            DataFrame with valid labels only
        """
        if label_col not in df.columns:
            logger.error(f"Label column '{label_col}' not found")
            return df
        
        # Check for valid binary labels (0 or 1)
        valid_labels = df[label_col].isin([0, 1])
        invalid_count = (~valid_labels).sum()
        
        if invalid_count > 0:
            logger.warning(f"Found {invalid_count} invalid labels, removing...")
            self.stats["invalid_labels"] = invalid_count
            df = df[valid_labels]
        
        return df
    
    def handle_missing_values(self, df: pd.DataFrame, strategy: str = 'drop') -> pd.DataFrame:
        """
        Handle missing values in dataset.
        
        Args:
            df: Input DataFrame
            strategy: 'drop', 'mean', 'median', 'mode', 'zero'
            
        Returns:
            DataFrame with missing values handled
        """
        missing_count = df.isnull().sum().sum()
        
        if missing_count == 0:
            return df
        
        self.stats["missing_values"] = missing_count
        logger.info(f"Found {missing_count} missing values, strategy={strategy}")
        
        if strategy == 'drop':
            df = df.dropna()
        elif strategy == 'mean':
            df = df.fillna(df.mean(numeric_only=True))
        elif strategy == 'median':
            df = df.fillna(df.median(numeric_only=True))
        elif strategy == 'mode':
            df = df.fillna(df.mode().iloc[0])
        elif strategy == 'zero':
            df = df.fillna(0)
        
        return df
    
    def remove_outliers(self, df: pd.DataFrame, columns: Optional[List[str]] = None,
                       method: str = 'iqr', threshold: float = 1.5) -> pd.DataFrame:
        """
        Remove outliers from numeric columns.
        
        Args:
            df: Input DataFrame
            columns: Columns to check for outliers (None = all numeric)
            method: 'iqr' or 'zscore'
            threshold: IQR multiplier (1.5) or Z-score threshold (3)
            
        Returns:
            DataFrame with outliers removed
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        initial_count = len(df)
        mask = pd.Series([True] * len(df), index=df.index)
        
        for col in columns:
            if col not in df.columns:
                continue
            
            if method == 'iqr':
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                mask &= (df[col] >= lower_bound) & (df[col] <= upper_bound)
            
            elif method == 'zscore':
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                mask &= z_scores < threshold
        
        df_clean = df[mask]
        outliers_removed = initial_count - len(df_clean)
        
        self.stats["outliers_removed"] = outliers_removed
        
        if outliers_removed > 0:
            logger.info(f"Removed {outliers_removed} outliers ({outliers_removed/initial_count*100:.2f}%)")
        
        return df_clean
    
    def balance_classes(self, df: pd.DataFrame, label_col: str = 'label',
                       strategy: str = 'undersample', target_ratio: float = 1.0) -> pd.DataFrame:
        """
        Balance class distribution.
        
        Args:
            df: Input DataFrame
            label_col: Name of label column
            strategy: 'undersample', 'oversample', or 'smote'
            target_ratio: Desired minority/majority ratio (1.0 = equal)
            
        Returns:
            Balanced DataFrame
        """
        if label_col not in df.columns:
            return df
        
        class_counts = df[label_col].value_counts()
        majority_class = class_counts.idxmax()
        minority_class = class_counts.idxmin()
        
        majority_count = class_counts[majority_class]
        minority_count = class_counts[minority_class]
        
        logger.info(f"Class distribution before balancing: {dict(class_counts)}")
        
        if strategy == 'undersample':
            # Random undersample majority class
            target_count = int(minority_count / target_ratio)
            
            majority_df = df[df[label_col] == majority_class]
            minority_df = df[df[label_col] == minority_class]
            
            majority_sampled = majority_df.sample(n=min(target_count, len(majority_df)), random_state=42)
            df_balanced = pd.concat([majority_sampled, minority_df], ignore_index=True)
        
        elif strategy == 'oversample':
            # Random oversample minority class
            target_count = int(majority_count * target_ratio)
            
            majority_df = df[df[label_col] == majority_class]
            minority_df = df[df[label_col] == minority_class]
            
            minority_sampled = minority_df.sample(n=target_count, replace=True, random_state=42)
            df_balanced = pd.concat([majority_df, minority_sampled], ignore_index=True)
        
        elif strategy == 'smote':
            # SMOTE requires sklearn
            try:
                from imblearn.over_sampling import SMOTE
                
                X = df.drop(columns=[label_col])
                y = df[label_col]
                
                smote = SMOTE(sampling_strategy=target_ratio, random_state=42)
                X_resampled, y_resampled = smote.fit_resample(X, y)
                
                df_balanced = pd.DataFrame(X_resampled, columns=X.columns)
                df_balanced[label_col] = y_resampled
            except ImportError:
                logger.warning("imbalanced-learn not installed, falling back to oversample")
                return self.balance_classes(df, label_col, 'oversample', target_ratio)
        else:
            return df
        
        balanced_counts = df_balanced[label_col].value_counts()
        logger.info(f"Class distribution after balancing: {dict(balanced_counts)}")
        
        return df_balanced
    
    def compute_statistics(self, df: pd.DataFrame, label_col: str = 'label') -> Dict:
        """
        Compute dataset statistics.
        
        Args:
            df: Input DataFrame
            label_col: Name of label column
            
        Returns:
            Statistics dictionary
        """
        stats = {
            "total_samples": len(df),
            "num_features": len(df.columns) - 1,  # Exclude label
            "class_distribution": {},
            "feature_stats": {}
        }
        
        # Class distribution
        if label_col in df.columns:
            class_counts = df[label_col].value_counts()
            stats["class_distribution"] = {
                str(k): int(v) for k, v in class_counts.items()
            }
            stats["class_balance_ratio"] = (
                min(class_counts) / max(class_counts) 
                if len(class_counts) > 1 else 1.0
            )
        
        # Feature statistics
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col == label_col:
                continue
            
            stats["feature_stats"][col] = {
                "mean": float(df[col].mean()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "missing": int(df[col].isnull().sum())
            }
        
        self.stats.update(stats)
        return stats
    
    def curate(self, df: pd.DataFrame, label_col: str = 'label',
               remove_dups: bool = True,
               handle_missing: str = 'drop',
               remove_outliers_flag: bool = True,
               balance: Optional[str] = None,
               balance_ratio: float = 1.0) -> Tuple[pd.DataFrame, Dict]:
        """
        Full curation pipeline.
        
        Args:
            df: Input DataFrame
            label_col: Name of label column
            remove_dups: Remove duplicates
            handle_missing: Missing value strategy
            remove_outliers_flag: Remove outliers
            balance: Class balancing strategy (None, 'undersample', 'oversample', 'smote')
            balance_ratio: Target class ratio for balancing
            
        Returns:
            Tuple of (curated DataFrame, statistics)
        """
        logger.info(f"Starting data curation pipeline on {len(df)} samples")
        
        self.stats["total_samples"] = len(df)
        df_curated = df.copy()
        
        # Step 1: Remove duplicates
        if remove_dups:
            df_curated = self.remove_duplicates(df_curated)
        
        # Step 2: Validate labels
        df_curated = self.validate_labels(df_curated, label_col)
        
        # Step 3: Handle missing values
        df_curated = self.handle_missing_values(df_curated, strategy=handle_missing)
        
        # Step 4: Remove outliers
        if remove_outliers_flag:
            feature_cols = [col for col in df_curated.columns if col != label_col]
            df_curated = self.remove_outliers(df_curated, columns=feature_cols)
        
        # Step 5: Balance classes
        if balance:
            df_curated = self.balance_classes(df_curated, label_col, strategy=balance, 
                                             target_ratio=balance_ratio)
        
        # Step 6: Compute statistics
        stats = self.compute_statistics(df_curated, label_col)
        
        logger.info(f"Curation complete: {len(df_curated)} samples remaining "
                   f"({len(df_curated)/len(df)*100:.2f}% of original)")
        
        return df_curated, stats
    
    def save_curated_dataset(self, df: pd.DataFrame, name: str, 
                            stats: Optional[Dict] = None) -> Path:
        """
        Save curated dataset with metadata.
        
        Args:
            df: Curated DataFrame
            name: Dataset name
            stats: Statistics dictionary
            
        Returns:
            Path to saved dataset
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Save dataset
        df.to_csv(filepath, index=False)
        logger.info(f"Saved curated dataset: {filepath}")
        
        # Save metadata
        if stats:
            meta_filepath = self.output_dir / f"{name}_{timestamp}_metadata.json"
            import json
            with open(meta_filepath, 'w') as f:
                json.dump(stats, f, indent=2)
            logger.info(f"Saved metadata: {meta_filepath}")
        
        return filepath
    
    def get_statistics(self) -> Dict:
        """Get curation statistics."""
        return self.stats.copy()


# Global instance
_data_curator = None


def get_data_curator(**kwargs) -> DataCurator:
    """Get singleton data curator instance."""
    global _data_curator
    if _data_curator is None:
        _data_curator = DataCurator(**kwargs)
    return _data_curator
