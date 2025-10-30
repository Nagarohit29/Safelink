import argparse
from pathlib import Path
from core.ann_classifier import ANNDetector, train_model_from_csv
from config.settings import MODEL_FILENAME, DATASET_CSV, DEVICE
from core.packet_sniffer import start_sniffer
from core.alert_system import AlertSystem

def main():
    parser = argparse.ArgumentParser(description="SafeLink Backend")
    parser.add_argument("--train", action="store_true", help="Train model using dataset")
    parser.add_argument("--sniff", action="store_true", help="Start packet sniffer")
    parser.add_argument("--model", type=str, default=str(MODEL_FILENAME), help="Model path")
    parser.add_argument("--interface", type=str, default=None, help="Network interface to sniff on (e.g., eth0)")
    args = parser.parse_args()

    if args.train:
        print("Starting training...")
        train_model_from_csv(csv_path=DATASET_CSV, model_out_path=Path(args.model))
        print("Training completed.")

    if args.sniff:
        print("Loading model and starting sniffer...")
        detector = ANNDetector(model_path=args.model, device=DEVICE)
        alerts = AlertSystem()
        start_sniffer(interface=args.interface, dfa_callback=None, ann_detector=detector, alert_system=alerts)

if __name__ == "__main__":
    main()
