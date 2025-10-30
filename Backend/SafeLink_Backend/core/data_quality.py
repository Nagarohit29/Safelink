"""
Training Data Quality Checks

Validates training data quality through comprehensive checks.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """
    Comprehensive quality checks for training data.
    
    Checks:
    - Label consistency
    - Feature ranges
    - Missing values
    - Outliers
    - Class imbalance
    - Data type validity
    - Feature correlation
    """
    
    def __init__(self):
        """Initialize quality checker."""
        self.quality_report = {}
        logger.info("DataQualityChecker initialized")
    
    def check_label_consistency(self, df: pd.DataFrame, label_col: str = 'label') -> Dict:
        """
        Check label consistency.
        
        Args:
            df: Input DataFrame
            label_col: Label column name
            
        Returns:
            Check results
        """
        results = {
            "check": "label_consistency",
            "passed": True,
            "issues": [],
            "stats": {}
        }
        
        if label_col not in df.columns:
            results["passed"] = False
            results["issues"].append(f"Label column '{label_col}' not found")
            return results
        
        # Check for valid values (0 or 1 for binary classification)
        unique_labels = df[label_col].unique()
        results["stats"]["unique_labels"] = unique_labels.tolist()
        
        invalid_labels = [l for l in unique_labels if l not in [0, 1]]
        if invalid_labels:
            results["passed"] = False
            results["issues"].append(f"Invalid labels found: {invalid_labels}")
        
        # Check for null labels
        null_count = df[label_col].isnull().sum()
        results["stats"]["null_count"] = int(null_count)
        
        if null_count > 0:
            results["passed"] = False
            results["issues"].append(f"Found {null_count} null labels")
        
        # Class distribution
        if not invalid_labels and null_count == 0:
            class_counts = df[label_col].value_counts()
            results["stats"]["class_distribution"] = {
                str(k): int(v) for k, v in class_counts.items()
            }
        
        return results
    
    def check_feature_ranges(self, df: pd.DataFrame, 
                            expected_ranges: Optional[Dict[str, Tuple[float, float]]] = None,
                            label_col: str = 'label') -> Dict:
        """
        Check if features are within expected ranges.
        
        Args:
            df: Input DataFrame
            expected_ranges: Dict of {column: (min, max)}
            label_col: Label column to exclude
            
        Returns:
            Check results
        """
        results = {
            "check": "feature_ranges",
            "passed": True,
            "issues": [],
            "stats": {}
        }
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        feature_cols = [col for col in numeric_cols if col != label_col]
        
        for col in feature_cols:
            col_min = float(df[col].min())
            col_max = float(df[col].max())
            col_mean = float(df[col].mean())
            col_std = float(df[col].std())
            
            results["stats"][col] = {
                "min": col_min,
                "max": col_max,
                "mean": col_mean,
                "std": col_std
            }
            
            # Check against expected ranges
            if expected_ranges and col in expected_ranges:
                expected_min, expected_max = expected_ranges[col]
                
                if col_min < expected_min or col_max > expected_max:
                    results["passed"] = False
                    results["issues"].append(
                        f"{col}: range [{col_min:.2f}, {col_max:.2f}] "
                        f"outside expected [{expected_min}, {expected_max}]"
                    )
            
            # Check for infinite values
            inf_count = np.isinf(df[col]).sum()
            if inf_count > 0:
                results["passed"] = False
                results["issues"].append(f"{col}: {inf_count} infinite values")
        
        return results
    
    def check_missing_values(self, df: pd.DataFrame, threshold: float = 0.05) -> Dict:
        """
        Check for missing values.
        
        Args:
            df: Input DataFrame
            threshold: Max acceptable missing ratio (default 5%)
            
        Returns:
            Check results
        """
        results = {
            "check": "missing_values",
            "passed": True,
            "issues": [],
            "stats": {}
        }
        
        total_cells = df.shape[0] * df.shape[1]
        total_missing = df.isnull().sum().sum()
        missing_ratio = total_missing / total_cells if total_cells > 0 else 0
        
        results["stats"]["total_missing"] = int(total_missing)
        results["stats"]["missing_ratio"] = float(missing_ratio)
        
        # Per-column missing values
        for col in df.columns:
            missing_count = df[col].isnull().sum()
            if missing_count > 0:
                col_ratio = missing_count / len(df)
                results["stats"][col] = {
                    "missing_count": int(missing_count),
                    "missing_ratio": float(col_ratio)
                }
                
                if col_ratio > threshold:
                    results["passed"] = False
                    results["issues"].append(
                        f"{col}: {missing_count} missing ({col_ratio*100:.2f}%) exceeds threshold"
                    )
        
        return results
    
    def check_outliers(self, df: pd.DataFrame, method: str = 'iqr',
                      threshold: float = 3.0, label_col: str = 'label') -> Dict:
        """
        Check for outliers in features.
        
        Args:
            df: Input DataFrame
            method: 'iqr' or 'zscore'
            threshold: IQR multiplier (1.5-3) or Z-score (2-3)
            label_col: Label column to exclude
            
        Returns:
            Check results
        """
        results = {
            "check": "outliers",
            "passed": True,
            "issues": [],
            "stats": {}
        }
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        feature_cols = [col for col in numeric_cols if col != label_col]
        
        total_outliers = 0
        
        for col in feature_cols:
            outlier_count = 0
            
            if method == 'iqr':
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                outlier_count = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
            
            elif method == 'zscore':
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                outlier_count = (z_scores > threshold).sum()
            
            if outlier_count > 0:
                outlier_ratio = outlier_count / len(df)
                total_outliers += outlier_count
                
                results["stats"][col] = {
                    "outlier_count": int(outlier_count),
                    "outlier_ratio": float(outlier_ratio)
                }
                
                # Warn if >10% outliers
                if outlier_ratio > 0.10:
                    results["issues"].append(
                        f"{col}: {outlier_count} outliers ({outlier_ratio*100:.2f}%)"
                    )
        
        results["stats"]["total_outliers"] = int(total_outliers)
        results["stats"]["method"] = method
        
        return results
    
    def check_class_imbalance(self, df: pd.DataFrame, label_col: str = 'label',
                             threshold: float = 0.3) -> Dict:
        """
        Check for class imbalance.
        
        Args:
            df: Input DataFrame
            label_col: Label column name
            threshold: Min acceptable minority/majority ratio (0.3 = 30%)
            
        Returns:
            Check results
        """
        results = {
            "check": "class_imbalance",
            "passed": True,
            "issues": [],
            "stats": {}
        }
        
        if label_col not in df.columns:
            results["passed"] = False
            results["issues"].append(f"Label column '{label_col}' not found")
            return results
        
        class_counts = df[label_col].value_counts()
        results["stats"]["class_distribution"] = {
            str(k): int(v) for k, v in class_counts.items()
        }
        
        if len(class_counts) < 2:
            results["passed"] = False
            results["issues"].append("Only one class present in dataset")
            return results
        
        majority_count = class_counts.max()
        minority_count = class_counts.min()
        imbalance_ratio = minority_count / majority_count
        
        results["stats"]["imbalance_ratio"] = float(imbalance_ratio)
        results["stats"]["majority_count"] = int(majority_count)
        results["stats"]["minority_count"] = int(minority_count)
        
        if imbalance_ratio < threshold:
            results["passed"] = False
            results["issues"].append(
                f"Class imbalance detected: ratio {imbalance_ratio:.3f} < threshold {threshold}"
            )
        
        return results
    
    def check_data_types(self, df: pd.DataFrame) -> Dict:
        """
        Check data type validity.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Check results
        """
        results = {
            "check": "data_types",
            "passed": True,
            "issues": [],
            "stats": {}
        }
        
        for col in df.columns:
            dtype = str(df[col].dtype)
            results["stats"][col] = dtype
            
            # Check for object type columns (should be avoided for ML)
            if dtype == 'object':
                unique_count = df[col].nunique()
                sample_values = df[col].dropna().head(3).tolist()
                
                results["issues"].append(
                    f"{col}: object dtype (unique={unique_count}, samples={sample_values})"
                )
        
        return results
    
    def check_feature_correlation(self, df: pd.DataFrame, threshold: float = 0.95,
                                 label_col: str = 'label') -> Dict:
        """
        Check for highly correlated features.
        
        Args:
            df: Input DataFrame
            threshold: Correlation threshold for flagging (0.95 = 95%)
            label_col: Label column to exclude
            
        Returns:
            Check results
        """
        results = {
            "check": "feature_correlation",
            "passed": True,
            "issues": [],
            "stats": {}
        }
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        feature_cols = [col for col in numeric_cols if col != label_col]
        
        if len(feature_cols) < 2:
            return results
        
        # Compute correlation matrix
        corr_matrix = df[feature_cols].corr().abs()
        
        # Find highly correlated pairs
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                if corr_matrix.iloc[i, j] > threshold:
                    high_corr_pairs.append({
                        "feature1": corr_matrix.columns[i],
                        "feature2": corr_matrix.columns[j],
                        "correlation": float(corr_matrix.iloc[i, j])
                    })
        
        results["stats"]["high_correlation_pairs"] = high_corr_pairs
        results["stats"]["count"] = len(high_corr_pairs)
        
        if high_corr_pairs:
            results["issues"].append(
                f"Found {len(high_corr_pairs)} highly correlated feature pairs (>{threshold})"
            )
        
        return results
    
    def run_all_checks(self, df: pd.DataFrame, label_col: str = 'label',
                      expected_ranges: Optional[Dict] = None) -> Dict:
        """
        Run all quality checks.
        
        Args:
            df: Input DataFrame
            label_col: Label column name
            expected_ranges: Expected feature ranges
            
        Returns:
            Comprehensive quality report
        """
        logger.info(f"Running quality checks on dataset: {df.shape}")
        
        report = {
            "dataset_shape": df.shape,
            "timestamp": pd.Timestamp.now().isoformat(),
            "checks": [],
            "overall_passed": True,
            "total_issues": 0
        }
        
        # Run all checks
        checks = [
            self.check_label_consistency(df, label_col),
            self.check_feature_ranges(df, expected_ranges, label_col),
            self.check_missing_values(df),
            self.check_outliers(df, label_col=label_col),
            self.check_class_imbalance(df, label_col),
            self.check_data_types(df),
            self.check_feature_correlation(df, label_col=label_col)
        ]
        
        for check in checks:
            report["checks"].append(check)
            if not check["passed"]:
                report["overall_passed"] = False
            report["total_issues"] += len(check["issues"])
        
        self.quality_report = report
        
        # Log summary
        logger.info(f"Quality checks complete: "
                   f"{'PASSED' if report['overall_passed'] else 'FAILED'}, "
                   f"{report['total_issues']} issues found")
        
        return report
    
    def get_report(self) -> Dict:
        """Get last quality report."""
        return self.quality_report.copy()
    
    def print_report(self, report: Optional[Dict] = None):
        """
        Print quality report in readable format.
        
        Args:
            report: Report dictionary (uses last report if None)
        """
        report = report or self.quality_report
        
        if not report:
            print("No quality report available")
            return
        
        print("\n" + "="*80)
        print("DATA QUALITY REPORT")
        print("="*80)
        print(f"Dataset Shape: {report['dataset_shape']}")
        print(f"Timestamp: {report['timestamp']}")
        print(f"Overall Status: {'✓ PASSED' if report['overall_passed'] else '✗ FAILED'}")
        print(f"Total Issues: {report['total_issues']}")
        print("="*80)
        
        for check in report["checks"]:
            status = "✓ PASS" if check["passed"] else "✗ FAIL"
            print(f"\n[{status}] {check['check'].upper()}")
            
            if check["issues"]:
                print("  Issues:")
                for issue in check["issues"]:
                    print(f"    - {issue}")
            
            if check["stats"]:
                print("  Statistics:")
                for key, value in list(check["stats"].items())[:5]:  # Show first 5
                    if isinstance(value, dict):
                        print(f"    {key}: {value}")
                    else:
                        print(f"    {key}: {value}")
        
        print("\n" + "="*80)


# Global instance
_quality_checker = None


def get_quality_checker() -> DataQualityChecker:
    """Get singleton quality checker instance."""
    global _quality_checker
    if _quality_checker is None:
        _quality_checker = DataQualityChecker()
    return _quality_checker
