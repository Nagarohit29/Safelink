"""Check if ANN has generated any alerts."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import DATABASE_URL
from core.alert_system import Alert

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Get ANN alerts
ann_alerts = session.query(Alert).filter(Alert.module == 'ANN').all()

print(f"Total ANN alerts: {len(ann_alerts)}\n")

if ann_alerts:
    print("Recent ANN Alerts:")
    print("-" * 80)
    for alert in ann_alerts[-10:]:  # Last 10
        print(f"[{alert.timestamp}] {alert.reason}")
        print(f"  Source: IP={alert.src_ip}, MAC={alert.src_mac}\n")
else:
    print("ℹ️  No ANN alerts yet.")
    print("\nThe ANN is running but hasn't detected anomalous traffic.")
    print("Generate some attacks with Bettercap to trigger ANN alerts!")

session.close()
