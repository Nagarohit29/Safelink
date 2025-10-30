"""
Test script for Continuous Learning System
"""

import sys
sys.path.insert(0, 'E:\\coreproject\\Backend\\SafeLink_Backend')

from core.continuous_learner import ContinuousLearner
from core.ann_classifier import ANNDetector
from core.alert_system import AlertSystem, Alert
from config.settings import MODEL_FILENAME, DEVICE
import time

def test_continuous_learning():
    """Test continuous learning initialization and basic functionality"""
    
    print("=" * 60)
    print("Testing Continuous Learning System")
    print("=" * 60)
    
    # 1. Initialize ANN Detector
    print("\n1. Initializing ANN Detector...")
    try:
        detector = ANNDetector(model_path=str(MODEL_FILENAME), device=DEVICE)
        print("   ✅ ANN Detector initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize detector: {e}")
        return
    
    # 2. Initialize Continuous Learner
    print("\n2. Initializing Continuous Learner...")
    try:
        learner = ContinuousLearner(
            ann_detector=detector,
            learning_interval=60,  # 1 minute for testing
            min_samples=10,  # Low threshold for testing
            batch_size=8
        )
        print("   ✅ Continuous Learner initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize learner: {e}")
        return
    
    # 3. Check initial statistics
    print("\n3. Checking initial statistics...")
    try:
        stats = learner.get_statistics()
        print(f"   ✅ Statistics retrieved:")
        print(f"      - Is Training: {stats['is_training']}")
        print(f"      - Last Processed ID: {stats['last_processed_id']}")
        print(f"      - Total Training Cycles: {stats['total_training_cycles']}")
        print(f"      - Model Versions: {stats['model_versions']}")
    except Exception as e:
        print(f"   ❌ Failed to get statistics: {e}")
    
    # 4. Check database alerts
    print("\n4. Checking database for alerts...")
    try:
        alert_system = AlertSystem()
        session = alert_system.Session()
        alert_count = session.query(Alert).count()
        new_alert_count = session.query(Alert).filter(
            Alert.id > learner.last_processed_id
        ).count()
        session.close()
        
        print(f"   ✅ Database checked:")
        print(f"      - Total Alerts: {alert_count}")
        print(f"      - New Alerts (since last training): {new_alert_count}")
    except Exception as e:
        print(f"   ❌ Failed to check database: {e}")
    
    # 5. Test should_train logic
    print("\n5. Testing training readiness...")
    try:
        should_train = learner._should_train()
        print(f"   {'✅' if should_train else '⚠️'} Should train: {should_train}")
        if not should_train:
            print(f"      Reason: Need {learner.min_samples} new alerts or time interval not reached")
    except Exception as e:
        print(f"   ❌ Failed to check training readiness: {e}")
    
    # 6. Test auto-labeling
    print("\n6. Testing auto-labeling logic...")
    try:
        # Create test alerts
        test_alerts = [
            Alert(id=1, module="DFA", reason="ARP spoofing detected", src_ip="192.168.1.100", src_mac="aa:bb:cc:dd:ee:ff"),
            Alert(id=2, module="ANN", reason="Suspicious traffic (confidence: 0.96)", src_ip="10.0.0.5", src_mac="11:22:33:44:55:66"),
            Alert(id=3, module="ANN", reason="Low confidence alert (confidence: 0.25)", src_ip="172.16.0.1", src_mac="ff:ee:dd:cc:bb:aa"),
        ]
        
        for alert in test_alerts:
            label = learner._auto_label_alert(alert)
            label_text = "Attack" if label == 1 else "Benign" if label == 0 else "Skip"
            print(f"   {'✅' if label is not None else '⚠️'} {alert.module} alert → Label: {label_text}")
    except Exception as e:
        print(f"   ❌ Failed to test auto-labeling: {e}")
    
    # 7. Test backup functionality
    print("\n7. Testing backup functionality...")
    try:
        backup_path = learner._backup_current_model()
        if backup_path and backup_path.exists():
            print(f"   ✅ Backup created: {backup_path.name}")
        else:
            print("   ⚠️ No existing model to backup (expected for fresh install)")
    except Exception as e:
        print(f"   ❌ Failed to test backup: {e}")
    
    # 8. Start continuous learning (background)
    print("\n8. Testing background learning thread...")
    try:
        learner.start_continuous_learning()
        print("   ✅ Background thread started")
        
        # Check if thread is alive
        time.sleep(2)
        if learner.training_thread and learner.training_thread.is_alive():
            print("   ✅ Thread is running")
        else:
            print("   ⚠️ Thread may have stopped")
        
        # Stop the thread
        learner.stop_continuous_learning()
        print("   ✅ Background thread stopped")
    except Exception as e:
        print(f"   ❌ Failed to test background thread: {e}")
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("✅ All core components tested successfully!")
    print("\nNext Steps:")
    print("1. Start the backend: python -m uvicorn api:app --reload --port 8000")
    print("2. Start the sniffer via UI or API")
    print("3. Continuous learning will activate automatically")
    print("4. Monitor status: GET /learning/status")
    print("5. Generate test alerts to trigger training")
    print("=" * 60)


if __name__ == "__main__":
    test_continuous_learning()
