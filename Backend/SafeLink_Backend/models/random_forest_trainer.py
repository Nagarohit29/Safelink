"""
Random Forest Training Pipeline

Provides Random Forest classifier training, evaluation, and comparison with ANN.
"""

import logging
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, roc_curve
)
from sklearn.preprocessing import StandardScaler, LabelEncoder

logger = logging.getLogger(__name__)


class RandomForestTrainer:
    """
    Random Forest classifier training and evaluation.
    
    Features:
    - Training with cross-validation
    - Comprehensive evaluation metrics
    - Model serialization
    - Performance comparison with ANN
    - Feature importance analysis
    - Automatic categorical feature encoding
    """
    
    def __init__(self, model_dir: str = "models"):
        """
        Initialize Random Forest trainer.
        
        Args:
            model_dir: Directory to save models
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.model: Optional[RandomForestClassifier] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_names: Optional[List[str]] = None
        self.label_encoders: Dict[str, LabelEncoder] = {}  # For categorical features
        self.target_encoder: Optional[LabelEncoder] = None  # For target labels
        self.training_history: Dict[str, Any] = {}
        
        logger.info("RandomForestTrainer initialized")
    
    def _encode_categorical_features(self, X: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
        """
        Encode categorical features using LabelEncoder.
        
        Args:
            X: Feature DataFrame
            is_training: Whether this is training (fit encoders) or prediction (use existing encoders)
            
        Returns:
            DataFrame with encoded features
        """
        X_encoded = X.copy()
        categorical_cols = X.select_dtypes(include=['object']).columns
        
        for col in categorical_cols:
            if is_training:
                self.label_encoders[col] = LabelEncoder()
                # Handle missing values
                X_encoded[col] = X_encoded[col].fillna('missing')
                X_encoded[col] = self.label_encoders[col].fit_transform(X_encoded[col].astype(str))
            else:
                if col in self.label_encoders:
                    # Handle unseen categories
                    X_encoded[col] = X_encoded[col].fillna('missing')
                    # Map unseen values to a default (-1)
                    def safe_transform(x):
                        try:
                            return self.label_encoders[col].transform([str(x)])[0]
                        except ValueError:
                            return -1
                    X_encoded[col] = X_encoded[col].apply(safe_transform)
        
        return X_encoded
    
    def train(self, 
              X_train: np.ndarray, 
              y_train: np.ndarray,
              n_estimators: int = 100,
              max_depth: Optional[int] = None,
              min_samples_split: int = 2,
              min_samples_leaf: int = 1,
              max_features: str = 'sqrt',
              class_weight: Optional[str] = 'balanced',
              random_state: int = 42,
              n_jobs: int = -1,
              verbose: int = 0) -> Dict[str, Any]:
        """
        Train Random Forest classifier.
        
        Args:
            X_train: Training features (DataFrame or ndarray)
            y_train: Training labels
            n_estimators: Number of trees
            max_depth: Maximum tree depth (None = unlimited)
            min_samples_split: Min samples to split node
            min_samples_leaf: Min samples in leaf
            max_features: Features to consider for split
            class_weight: Class weights ('balanced' or None)
            random_state: Random seed
            n_jobs: Parallel jobs (-1 = all CPUs)
            verbose: Verbosity level
            
        Returns:
            Training metrics
        """
        logger.info(f"Training Random Forest: n_estimators={n_estimators}, "
                   f"max_depth={max_depth}, class_weight={class_weight}")
        
        start_time = datetime.now()
        
        # Convert to DataFrame if needed for categorical encoding
        if isinstance(X_train, pd.DataFrame):
            X_train = self._encode_categorical_features(X_train, is_training=True)
            X_train = X_train.values
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Create model
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            max_features=max_features,
            class_weight=class_weight,
            random_state=random_state,
            n_jobs=n_jobs,
            verbose=verbose
        )
        
        # Train
        self.model.fit(X_train_scaled, y_train)
        
        # Cross-validation
        cv_scores = cross_val_score(
            self.model, X_train_scaled, y_train, 
            cv=5, scoring='accuracy', n_jobs=n_jobs
        )
        
        # Training predictions
        y_pred_train = self.model.predict(X_train_scaled)
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        # Determine if binary or multi-class
        n_classes = len(np.unique(y_train))
        average_method = 'binary' if n_classes == 2 else 'weighted'
        
        # Metrics
        metrics = {
            'accuracy': float(accuracy_score(y_train, y_pred_train)),
            'precision': float(precision_score(y_train, y_pred_train, average=average_method, zero_division=0)),
            'recall': float(recall_score(y_train, y_pred_train, average=average_method, zero_division=0)),
            'f1_score': float(f1_score(y_train, y_pred_train, average=average_method, zero_division=0)),
            'cv_accuracy_mean': float(cv_scores.mean()),
            'cv_accuracy_std': float(cv_scores.std()),
            'training_time': training_time,
            'n_estimators': n_estimators,
            'max_depth': max_depth,
            'n_samples': len(y_train),
            'n_classes': n_classes
        }
        
        # Add ROC-AUC for binary classification only
        if n_classes == 2:
            y_proba_train = self.model.predict_proba(X_train_scaled)[:, 1]
            metrics['roc_auc'] = float(roc_auc_score(y_train, y_proba_train))
        
        self.training_history = {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'hyperparameters': {
                'n_estimators': n_estimators,
                'max_depth': max_depth,
                'min_samples_split': min_samples_split,
                'min_samples_leaf': min_samples_leaf,
                'max_features': max_features,
                'class_weight': class_weight
            }
        }
        
        logger.info(f"Training complete: Accuracy={metrics['accuracy']:.4f}, "
                   f"F1={metrics['f1_score']:.4f}, Time={training_time:.2f}s")
        
        return metrics
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """
        Evaluate model on test set.
        
        Args:
            X_test: Test features
            y_test: Test labels
            
        Returns:
            Evaluation metrics
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained. Call train() first.")
        
        logger.info(f"Evaluating on {len(y_test)} test samples")
        
        # Scale features
        X_test_scaled = self.scaler.transform(X_test)
        
        # Predictions
        y_pred = self.model.predict(X_test_scaled)
        
        # Determine if binary or multi-class
        n_classes = len(np.unique(y_test))
        average_method = 'binary' if n_classes == 2 else 'weighted'
        
        # Metrics
        metrics = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision': float(precision_score(y_test, y_pred, average=average_method, zero_division=0)),
            'recall': float(recall_score(y_test, y_pred, average=average_method, zero_division=0)),
            'f1_score': float(f1_score(y_test, y_pred, average=average_method, zero_division=0)),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'n_samples': len(y_test),
            'n_classes': n_classes
        }
        
        # Add ROC-AUC for binary classification only
        if n_classes == 2:
            y_proba = self.model.predict_proba(X_test_scaled)[:, 1]
            metrics['roc_auc'] = float(roc_auc_score(y_test, y_proba))
        
        # Classification report
        class_report = classification_report(y_test, y_pred, output_dict=True)
        metrics['classification_report'] = class_report
        
        logger.info(f"Evaluation: Accuracy={metrics['accuracy']:.4f}, "
                   f"F1={metrics['f1_score']:.4f}")
        
        return metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict labels.
        
        Args:
            X: Features
            
        Returns:
            Predicted labels
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained")
        
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict probabilities.
        
        Args:
            X: Features
            
        Returns:
            Class probabilities
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained")
        
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)
    
    def get_feature_importance(self, feature_names: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Get feature importances.
        
        Args:
            feature_names: List of feature names
            
        Returns:
            Dict mapping feature names to importance scores
        """
        if self.model is None:
            raise ValueError("Model not trained")
        
        importances = self.model.feature_importances_
        
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(len(importances))]
        
        # Sort by importance
        importance_dict = {
            name: float(imp) 
            for name, imp in zip(feature_names, importances)
        }
        
        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
    
    def save_model(self, filename: str = "random_forest_model.joblib"):
        """
        Save model to disk.
        
        Args:
            filename: Output filename
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained")
        
        model_path = self.model_dir / filename
        scaler_path = self.model_dir / filename.replace('.joblib', '_scaler.joblib')
        encoders_path = self.model_dir / filename.replace('.joblib', '_encoders.joblib')
        
        # Save model and scaler
        joblib.dump(self.model, model_path)
        joblib.dump(self.scaler, scaler_path)
        
        # Save encoders (both feature and target)
        encoders_data = {
            'label_encoders': self.label_encoders,
            'target_encoder': self.target_encoder
        }
        joblib.dump(encoders_data, encoders_path)
        
        # Save training history
        history_path = self.model_dir / filename.replace('.joblib', '_history.json')
        with open(history_path, 'w') as f:
            json.dump(self.training_history, f, indent=2)
        
        logger.info(f"Model saved to {model_path}")
    
    def load_model(self, filename: str = "random_forest_model.joblib"):
        """
        Load model from disk.
        
        Args:
            filename: Model filename
        """
        model_path = self.model_dir / filename
        scaler_path = self.model_dir / filename.replace('.joblib', '_scaler.joblib')
        encoders_path = self.model_dir / filename.replace('.joblib', '_encoders.joblib')
        history_path = self.model_dir / filename.replace('.joblib', '_history.json')
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        self.model = joblib.load(model_path)
        
        if scaler_path.exists():
            self.scaler = joblib.load(scaler_path)
        
        # Load encoders
        if encoders_path.exists():
            encoders_data = joblib.load(encoders_path)
            self.label_encoders = encoders_data.get('label_encoders', {})
            self.target_encoder = encoders_data.get('target_encoder', None)
        
        if history_path.exists():
            with open(history_path, 'r') as f:
                self.training_history = json.load(f)
        
        logger.info(f"Model loaded from {model_path}")
    
    def compare_with_ann(self, ann_metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Compare Random Forest performance with ANN.
        
        Args:
            ann_metrics: ANN evaluation metrics
            
        Returns:
            Comparison report
        """
        if not self.training_history:
            raise ValueError("Random Forest not trained")
        
        rf_metrics = self.training_history['metrics']
        
        comparison = {
            'random_forest': {
                'accuracy': rf_metrics.get('accuracy', 0),
                'precision': rf_metrics.get('precision', 0),
                'recall': rf_metrics.get('recall', 0),
                'f1_score': rf_metrics.get('f1_score', 0),
                'roc_auc': rf_metrics.get('roc_auc', 0),
                'training_time': rf_metrics.get('training_time', 0)
            },
            'ann': {
                'accuracy': ann_metrics.get('accuracy', 0),
                'precision': ann_metrics.get('precision', 0),
                'recall': ann_metrics.get('recall', 0),
                'f1_score': ann_metrics.get('f1_score', 0),
                'roc_auc': ann_metrics.get('roc_auc', 0),
                'training_time': ann_metrics.get('training_time', 0)
            },
            'differences': {}
        }
        
        # Calculate differences (positive = RF better)
        for metric in ['accuracy', 'precision', 'recall', 'f1_score', 'roc_auc']:
            rf_val = comparison['random_forest'][metric]
            ann_val = comparison['ann'][metric]
            comparison['differences'][metric] = rf_val - ann_val
        
        # Determine winner
        rf_wins = sum(1 for v in comparison['differences'].values() if v > 0)
        ann_wins = sum(1 for v in comparison['differences'].values() if v < 0)
        
        if rf_wins > ann_wins:
            comparison['winner'] = 'random_forest'
        elif ann_wins > rf_wins:
            comparison['winner'] = 'ann'
        else:
            comparison['winner'] = 'tie'
        
        comparison['summary'] = (
            f"Random Forest wins on {rf_wins}/5 metrics, "
            f"ANN wins on {ann_wins}/5 metrics"
        )
        
        logger.info(f"Model comparison: {comparison['winner']} - {comparison['summary']}")
        
        return comparison


def train_from_csv(csv_path: str, 
                   label_col: str = 'label',
                   test_size: float = 0.2,
                   **rf_params) -> Tuple[RandomForestTrainer, Dict, Dict]:
    """
    Train Random Forest from CSV file.
    
    Args:
        csv_path: Path to CSV file
        label_col: Label column name
        test_size: Test set proportion
        **rf_params: Random Forest hyperparameters
        
    Returns:
        Tuple of (trainer, train_metrics, test_metrics)
    """
    # Load data
    df = pd.read_csv(csv_path)
    
    # Split features and labels
    X = df.drop(columns=[label_col])  # Keep as DataFrame for categorical encoding
    y = df[label_col].values
    
    # Encode target labels if they're strings
    trainer = RandomForestTrainer()
    if y.dtype == object or isinstance(y[0], str):
        trainer.target_encoder = LabelEncoder()
        y = trainer.target_encoder.fit_transform(y)
        logger.info(f"Encoded target labels: {list(trainer.target_encoder.classes_)}")
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    # Train
    train_metrics = trainer.train(X_train, y_train, **rf_params)
    
    # Evaluate (need to encode test data too)
    if isinstance(X_test, pd.DataFrame):
        X_test_encoded = trainer._encode_categorical_features(X_test, is_training=False)
        X_test = X_test_encoded.values
    test_metrics = trainer.evaluate(X_test, y_test)
    
    # Save
    trainer.save_model()
    
    return trainer, train_metrics, test_metrics


# Global instance
_rf_trainer = None


def get_rf_trainer() -> RandomForestTrainer:
    """Get singleton Random Forest trainer instance."""
    global _rf_trainer
    if _rf_trainer is None:
        _rf_trainer = RandomForestTrainer()
        try:
            _rf_trainer.load_model()
        except FileNotFoundError:
            logger.info("No saved Random Forest model found")
    return _rf_trainer


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python random_forest_trainer.py <dataset.csv>")
        sys.exit(1)
    
    logging.basicConfig(level=logging.INFO)
    
    csv_path = sys.argv[1]
    trainer, train_metrics, test_metrics = train_from_csv(csv_path)
    
    print("\n" + "="*60)
    print("RANDOM FOREST TRAINING COMPLETE")
    print("="*60)
    print(f"\nTraining Metrics:")
    for k, v in train_metrics.items():
        print(f"  {k}: {v}")
    
    print(f"\nTest Metrics:")
    for k, v in test_metrics.items():
        if k != 'classification_report' and k != 'confusion_matrix':
            print(f"  {k}: {v}")
    
    print("\nModel saved to models/random_forest_model.joblib")
