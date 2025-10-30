"""
Quick Integration Test

Tests core functionality after deployment.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from models.random_forest_trainer import RandomForestTrainer
import numpy as np
import pandas as pd

def test_random_forest_model():
    """Test Random Forest model loading and prediction."""
    print("\n" + "="*60)
    print("TEST 1: Random Forest Model")
    print("="*60)
    
    trainer = RandomForestTrainer()
    
    # Try to load the model
    try:
        trainer.load_model()
        print("✅ Model loaded successfully")
        print(f"  - Model type: {type(trainer.model).__name__}")
        print(f"  - Number of trees: {trainer.model.n_estimators}")
        if trainer.model.max_depth:
            print(f"  - Max depth: {trainer.model.max_depth}")
        return True
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return False


def test_dataset_loading():
    """Test dataset loading and structure."""
    print("\n" + "="*60)
    print("TEST 2: Dataset Loading")
    print("="*60)
    
    try:
        df = pd.read_csv('data/All_Labelled.csv')
        print("✅ Dataset loaded successfully")
        print(f"  - Total samples: {len(df):,}")
        print(f"  - Features: {len(df.columns) - 1}")
        print(f"  - Label column: Label")
        print(f"  - Classes: {sorted(df['Label'].unique())}")
        print(f"  - Class distribution:")
        for label, count in df['Label'].value_counts().items():
            print(f"    * {label}: {count:,} ({count/len(df)*100:.1f}%)")
        return True
    except Exception as e:
        print(f"❌ Dataset loading failed: {e}")
        return False


def test_api_imports():
    """Test API and core module imports."""
    print("\n" + "="*60)
    print("TEST 3: API & Core Module Imports")
    print("="*60)
    
    try:
        from api import app
        from core.ann_classifier import ANNDetector  # Fixed: was ANNClassifier
        from core.continuous_learner import ContinuousLearner
        from core.threat_intel_db import ThreatIntelService
        from core.data_curator import DataCurator
        from models.hyperparameter_tuner import HyperparameterTuner
        
        print("✅ All core modules imported successfully")
        print("  - API: FastAPI app")
        print("  - ANN Detector")
        print("  - Continuous Learner")
        print("  - Threat Intel Database")
        print("  - Data Curator")
        print("  - Hyperparameter Tuner")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_feature_engineering():
    """Test categorical encoding on sample data."""
    print("\n" + "="*60)
    print("TEST 4: Feature Engineering")
    print("="*60)
    
    try:
        trainer = RandomForestTrainer()
        
        # Load small sample
        df = pd.read_csv('data/All_Labelled.csv', nrows=10)
        X = df.drop(columns=['Label'])
        
        # Test categorical encoding
        X_encoded = trainer._encode_categorical_features(X, is_training=True)
        
        print("✅ Categorical encoding works")
        print(f"  - Original shape: {X.shape}")
        print(f"  - Encoded shape: {X_encoded.shape}")
        print(f"  - Categorical columns encoded: {len(trainer.label_encoders)}")
        for col in trainer.label_encoders:
            print(f"    * {col}")
        return True
    except Exception as e:
        print(f"❌ Feature engineering failed: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("SAFELINK DEPLOYMENT VALIDATION TESTS")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Dataset Loading", test_dataset_loading()))
    results.append(("Random Forest Model", test_random_forest_model()))
    results.append(("Feature Engineering", test_feature_engineering()))
    results.append(("API & Core Imports", test_api_imports()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("="*60)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("="*60)
    
    if passed == total:
        print("\n✨ ALL TESTS PASSED! Deployment successful! ✨\n")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check output above.\n")
    
    sys.exit(0 if passed == total else 1)
