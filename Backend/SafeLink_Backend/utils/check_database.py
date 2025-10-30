"""Check alerts in the SafeLink database."""
import sqlite3
from datetime import datetime

def check_database():
    """Display alerts from the database."""
    try:
        conn = sqlite3.connect('safelink.db')
        cursor = conn.cursor()
        
        # Count total alerts
        cursor.execute('SELECT COUNT(*) FROM alerts')
        total = cursor.fetchone()[0]
        print(f"\n{'='*60}")
        print(f"  Total Alerts in Database: {total}")
        print(f"{'='*60}\n")
        
        if total == 0:
            print("No alerts found in database yet.")
            print("Make sure the sniffer is running and you've generated attack traffic.")
            return
        
        # Get latest 10 alerts
        cursor.execute('''
            SELECT id, timestamp, source_ip, dest_ip, protocol, 
                   alert_type, confidence, threat_level 
            FROM alerts 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''')
        
        print("Latest 10 Alerts:\n")
        print(f"{'ID':<5} {'Time':<20} {'Source IP':<15} {'Dest IP':<15} {'Type':<15} {'Confidence':<12} {'Threat':<10}")
        print("-" * 110)
        
        for row in cursor.fetchall():
            alert_id, timestamp, src_ip, dst_ip, protocol, alert_type, confidence, threat = row
            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = timestamp[:19] if timestamp else 'N/A'
            
            print(f"{alert_id:<5} {time_str:<20} {src_ip:<15} {dst_ip:<15} {alert_type:<15} {confidence:<12.2f} {threat:<10}")
        
        # Get attack type summary
        print(f"\n{'='*60}")
        print("  Attack Type Summary")
        print(f"{'='*60}\n")
        
        cursor.execute('''
            SELECT alert_type, COUNT(*) as count, AVG(confidence) as avg_conf
            FROM alerts 
            GROUP BY alert_type
            ORDER BY count DESC
        ''')
        
        print(f"{'Attack Type':<20} {'Count':<10} {'Avg Confidence':<15}")
        print("-" * 50)
        for row in cursor.fetchall():
            attack_type, count, avg_conf = row
            print(f"{attack_type:<20} {count:<10} {avg_conf:<15.2f}")
        
        # Get top attackers
        print(f"\n{'='*60}")
        print("  Top Attackers")
        print(f"{'='*60}\n")
        
        cursor.execute('''
            SELECT source_ip, COUNT(*) as attack_count
            FROM alerts 
            GROUP BY source_ip
            ORDER BY attack_count DESC
            LIMIT 5
        ''')
        
        print(f"{'Source IP':<20} {'Attack Count':<15}")
        print("-" * 40)
        for row in cursor.fetchall():
            src_ip, count = row
            print(f"{src_ip:<20} {count:<15}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except FileNotFoundError:
        print("Database file 'safelink.db' not found!")
        print("Make sure you're in the Backend/SafeLink_Backend directory.")

if __name__ == "__main__":
    check_database()
