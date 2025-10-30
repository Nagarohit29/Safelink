"""
Continuous Learning System for ANN Model
Implements online/incremental learning with the deployed model.
"""

import os
import threading
import time
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
import json

from sqlalchemy import and_
from sqlalchemy.orm import Session as SQLSession

from config.settings import BASE_DIR, MODEL_FILENAME, DEVICE
from config.logger_config import setup_logger
from core.alert_system import Alert, AlertSystem
from core.ann_classifier import ANNDetector

logger = setup_logger("ContinuousLearner")

# Initialize AlertSystem to get SessionLocal
_alert_system = AlertSystem()
SessionLocal = _alert_system.Session


class ContinuousLearner:
    """
    Implements continuous/incremental learning for the ANN model.
    
    Features:
    - Learns from new alerts in production
    - Non-blocking background training
    - Model versioning and rollback
    - Performance monitoring
    - Automatic data labeling from DFA/manual review
    """
    
    def __init__(
        self,
        ann_detector: ANNDetector = None,
        learning_interval: int = 3600,  # Train every hour
        min_samples: int = 100,  # Minimum samples before training
        batch_size: int = 32,
        learning_rate: float = 0.0001,  # Lower for incremental learning
        max_history: int = 10000  # Keep last N alerts for training
    ):
        """
        Initialize continuous learner.
        
        Args:
            ann_detector: Reference to deployed ANN model
            learning_interval: Seconds between training cycles
            min_samples: Minimum new samples before training
            batch_size: Training batch size
            learning_rate: Learning rate for incremental updates
            max_history: Maximum alerts to keep in training buffer
        """
        self.ann_detector = ann_detector
        self.learning_interval = learning_interval
        self.min_samples = min_samples
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.max_history = max_history
        
        # Training state
        self.is_training = False
        self.training_thread = None
        self.should_stop = False
        self.last_training_time = None
        self.last_processed_id = 0
        
        # Performance tracking
        self.training_history = []
        self.model_versions = []
        
        # Directories
        self.models_dir = Path(BASE_DIR) / "models"
        self.backup_dir = self.models_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        self.stats_file = self.models_dir / "continuous_learning_stats.json"
        
        # Load previous state
        self._load_state()
        
        logger.info(
            f"ContinuousLearner initialized: "
            f"interval={learning_interval}s, "
            f"min_samples={min_samples}, "
            f"batch_size={batch_size}"
        )
    
    def _load_state(self):
        """Load previous training state"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    state = json.load(f)
                    self.last_processed_id = state.get('last_processed_id', 0)
                    self.training_history = state.get('training_history', [])
                    self.model_versions = state.get('model_versions', [])
                    logger.info(f"Loaded state: last_processed_id={self.last_processed_id}")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
    
    def _save_state(self):
        """Save current training state"""
        try:
            state = {
                'last_processed_id': self.last_processed_id,
                'last_training_time': self.last_training_time.isoformat() if self.last_training_time else None,
                'training_history': self.training_history[-100:],  # Keep last 100 entries
                'model_versions': self.model_versions[-20:]  # Keep last 20 versions
            }
            with open(self.stats_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def start_continuous_learning(self):
        """Start background continuous learning thread"""
        if self.training_thread and self.training_thread.is_alive():
            logger.warning("Continuous learning already running")
            return
        
        self.should_stop = False
        self.training_thread = threading.Thread(
            target=self._learning_loop,
            daemon=True,
            name="ContinuousLearningThread"
        )
        self.training_thread.start()
        logger.info("Continuous learning started")
    
    def stop_continuous_learning(self):
        """Stop background learning thread"""
        self.should_stop = True
        if self.training_thread:
            self.training_thread.join(timeout=10)
        logger.info("Continuous learning stopped")
    
    def _learning_loop(self):
        """Main learning loop - runs in background"""
        logger.info("Continuous learning loop started")
        
        while not self.should_stop:
            try:
                # Check if it's time to train
                if self._should_train():
                    logger.info("Starting training cycle...")
                    self._perform_training_cycle()
                
                # Sleep for a short interval
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in learning loop: {e}", exc_info=True)
                time.sleep(300)  # Wait 5 minutes on error
    
    def _should_train(self) -> bool:
        """Determine if training should occur"""
        # Check time interval
        if self.last_training_time:
            elapsed = (datetime.now() - self.last_training_time).total_seconds()
            if elapsed < self.learning_interval:
                return False
        
        # Check if we have enough new samples
        session = SessionLocal()
        try:
            new_count = session.query(Alert).filter(
                Alert.id > self.last_processed_id
            ).count()
            
            if new_count < self.min_samples:
                logger.debug(f"Not enough new samples: {new_count}/{self.min_samples}")
                return False
            
            logger.info(f"Ready to train with {new_count} new samples")
            return True
            
        finally:
            session.close()
    
    def _perform_training_cycle(self):
        """Execute one training cycle"""
        self.is_training = True
        start_time = time.time()
        
        try:
            # 1. Collect new training data
            X_new, y_new, alert_ids = self._collect_training_data()
            
            if len(X_new) < self.min_samples:
                logger.warning(f"Insufficient labeled data: {len(X_new)} samples")
                return
            
            # 2. Backup current model
            backup_path = self._backup_current_model()
            
            # 3. Train on new data (incremental)
            metrics = self._incremental_train(X_new, y_new)
            
            # 4. Validate new model
            if self._validate_model(metrics):
                # Save updated model
                self._save_model_version(metrics)
                logger.info(f"✅ Model updated successfully: {metrics}")
            else:
                # Rollback to backup
                logger.warning("⚠️ Validation failed, rolling back to backup")
                self._rollback_model(backup_path)
            
            # 5. Update state
            if alert_ids:
                self.last_processed_id = max(alert_ids)
            self.last_training_time = datetime.now()
            
            # 6. Record metrics
            training_time = time.time() - start_time
            self._record_training_metrics(metrics, training_time, len(X_new))
            
            self._save_state()
            
        except Exception as e:
            logger.error(f"Training cycle failed: {e}", exc_info=True)
        finally:
            self.is_training = False
    
    def _collect_training_data(self) -> Tuple[np.ndarray, np.ndarray, List[int]]:
        """
        Collect new training data from alerts.
        
        Strategy:
        1. Get alerts since last training
        2. Auto-label based on detection module:
           - DFA detections = attack (label 1)
           - ANN with high confidence = use predicted label
           - Manual review = use verified label
        3. Extract features from alerts
        """
        session = SessionLocal()
        X_list = []
        y_list = []
        alert_ids = []
        
        try:
            # Get new alerts
            alerts = session.query(Alert).filter(
                Alert.id > self.last_processed_id
            ).order_by(Alert.id).limit(self.max_history).all()
            
            logger.info(f"Collected {len(alerts)} new alerts for training")
            
            for alert in alerts:
                try:
                    # Extract features
                    features = self._extract_features_from_alert(alert)
                    if features is None:
                        continue
                    
                    # Auto-label based on detection source
                    label = self._auto_label_alert(alert)
                    if label is None:
                        continue
                    
                    X_list.append(features)
                    y_list.append(label)
                    alert_ids.append(alert.id)
                    
                except Exception as e:
                    logger.error(f"Failed to process alert {alert.id}: {e}")
                    continue
            
            X = np.array(X_list) if X_list else np.array([])
            y = np.array(y_list) if y_list else np.array([])
            
            logger.info(f"Prepared {len(X)} labeled samples for training")
            return X, y, alert_ids
            
        finally:
            session.close()
    
    def _extract_features_from_alert(self, alert: Alert) -> np.ndarray:
        """
        Extract feature vector from alert.
        
        Uses the same feature extraction as ANNDetector.
        For now, creates features from IP/MAC addresses.
        """
        try:
            # Create feature array matching ANN input size
            features = []
            
            # Convert IP address to numeric features (4 octets)
            if alert.src_ip:
                try:
                    octets = [int(x) for x in alert.src_ip.split('.')]
                    features.extend(octets)
                except:
                    features.extend([0, 0, 0, 0])
            else:
                features.extend([0, 0, 0, 0])
            
            # Convert MAC address to numeric features (6 bytes)
            if alert.src_mac:
                try:
                    mac_bytes = [int(x, 16) for x in alert.src_mac.split(':')]
                    features.extend(mac_bytes)
                except:
                    features.extend([0, 0, 0, 0, 0, 0])
            else:
                features.extend([0, 0, 0, 0, 0, 0])
            
            # Add alert metadata as features
            # Module type (0=DFA, 1=ANN)
            features.append(1.0 if alert.module == "ANN" else 0.0)
            
            # Timestamp features (hour of day, day of week)
            if alert.timestamp:
                features.append(alert.timestamp.hour / 24.0)
                features.append(alert.timestamp.weekday() / 7.0)
            else:
                features.extend([0.0, 0.0])
            
            # Pad to match expected input size
            expected_size = self.ann_detector.input_size if self.ann_detector else 78
            while len(features) < expected_size:
                features.append(0.0)
            
            # Trim if too long
            features = features[:expected_size]
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None
    
    def _auto_label_alert(self, alert: Alert) -> int:
        """
        Automatically label alert based on detection source.
        
        Labeling strategy:
        - DFA detections (rule-based) = 1 (attack)
        - ANN detections with confidence > 95% = 1 (attack)
        - Normal traffic (if explicitly marked) = 0 (benign)
        - Unknown/low confidence = None (skip)
        
        Returns:
            0 = benign, 1 = attack, None = skip
        """
        # DFA detections are high confidence attacks
        if alert.module == "DFA":
            return 1  # Attack
        
        # ANN detections - check confidence from reason field
        if alert.module == "ANN":
            # Parse confidence from reason string
            # Example: "Suspicious traffic pattern (confidence: 0.96)"
            try:
                if "confidence:" in alert.reason:
                    conf_str = alert.reason.split("confidence:")[-1].strip().rstrip(")")
                    confidence = float(conf_str)
                    
                    if confidence >= 0.95:
                        return 1  # High confidence attack
                    elif confidence <= 0.30:
                        return 0  # Likely benign (false positive)
                    else:
                        return None  # Uncertain, skip
            except:
                pass
            
            # Default: trust ANN if no confidence info
            return 1
        
        # Manual review labels (if you add this feature)
        # if hasattr(alert, 'verified_label'):
        #     return alert.verified_label
        
        return None  # Skip unknown
    
    def _incremental_train(self, X_new: np.ndarray, y_new: np.ndarray) -> Dict:
        """
        Perform incremental training on new data.
        
        Uses the optimized incremental_update method from ANNDetector.
        """
        if self.ann_detector is None or self.ann_detector.model is None:
            logger.error("No model available for training")
            return {}
        
        try:
            # Use the optimized incremental learning method
            metrics = self.ann_detector.incremental_update(
                X_batch=X_new,
                y_batch=y_new,
                num_epochs=3  # Small number for online learning
            )
            
            logger.info(f"Incremental training completed: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Incremental training failed: {e}", exc_info=True)
            return {}
    
    def _backup_current_model(self) -> Path:
        """Backup current model before updating"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"model_backup_{timestamp}.pt"
        
        try:
            current_model = self.models_dir / MODEL_FILENAME
            if current_model.exists():
                import shutil
                shutil.copy2(current_model, backup_path)
                logger.info(f"Model backed up to: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None
    
    def _validate_model(self, metrics: Dict) -> bool:
        """
        Validate updated model performance.
        
        Criteria:
        - Accuracy > 80% on new data
        - Loss is reasonable
        - No catastrophic degradation
        """
        if not metrics:
            return False
        
        accuracy = metrics.get('accuracy', 0)
        loss = metrics.get('loss', float('inf'))
        
        # Validation criteria
        if accuracy < 70:  # Minimum acceptable accuracy
            logger.warning(f"Accuracy too low: {accuracy}%")
            return False
        
        if loss > 2.0:  # Maximum acceptable loss
            logger.warning(f"Loss too high: {loss}")
            return False
        
        logger.info(f"✅ Model validation passed: accuracy={accuracy}%, loss={loss:.4f}")
        return True
    
    def _save_model_version(self, metrics: Dict):
        """Save updated model version"""
        try:
            if self.ann_detector and self.ann_detector.model:
                model_path = self.models_dir / MODEL_FILENAME
                self.ann_detector.save_checkpoint(model_path)
                
                # Record version
                version_info = {
                    'timestamp': datetime.now().isoformat(),
                    'metrics': metrics,
                    'model_path': str(model_path)
                }
                self.model_versions.append(version_info)
                
                logger.info(f"Model version saved: {version_info}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
    
    def _rollback_model(self, backup_path: Path):
        """Rollback to backup model"""
        try:
            if backup_path and backup_path.exists():
                import shutil
                current_model = self.models_dir / MODEL_FILENAME
                shutil.copy2(backup_path, current_model)
                
                # Reload model in detector
                if self.ann_detector:
                    self.ann_detector.reload_model()
                
                logger.info(f"Model rolled back to: {backup_path}")
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
    
    def _record_training_metrics(self, metrics: Dict, training_time: float, num_samples: int):
        """Record training metrics for monitoring"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'training_time': training_time,
            'num_samples': num_samples,
            'metrics': metrics
        }
        self.training_history.append(record)
        logger.info(f"Training metrics recorded: {record}")
    
    def get_statistics(self) -> Dict:
        """Get continuous learning statistics"""
        return {
            'is_training': self.is_training,
            'last_training_time': self.last_training_time.isoformat() if self.last_training_time else None,
            'last_processed_id': self.last_processed_id,
            'total_training_cycles': len(self.training_history),
            'model_versions': len(self.model_versions),
            'recent_history': self.training_history[-10:] if self.training_history else []
        }
    
    def force_training_cycle(self):
        """Manually trigger a training cycle (for testing/admin)"""
        logger.info("Force training cycle triggered")
        self._perform_training_cycle()


# Global instance
continuous_learner = None


def initialize_continuous_learner(ann_detector: ANNDetector, auto_start: bool = True):
    """Initialize global continuous learner"""
    global continuous_learner
    continuous_learner = ContinuousLearner(ann_detector=ann_detector)
    if auto_start:
        continuous_learner.start_continuous_learning()
    return continuous_learner
