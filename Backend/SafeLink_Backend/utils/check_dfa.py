"""Check database schema and show DFA detection information."""
import sqlite3

def check_schema():
    """Display database schema and sample data."""
    try:
        conn = sqlite3.connect('safelink.db')
        cursor = conn.cursor()
        
        print("\n" + "="*70)
        print("  Alerts Table Schema")
        print("="*70 + "\n")
        
        cursor.execute('PRAGMA table_info(alerts)')
        schema = cursor.fetchall()
        
        print(f"{'Column':<15} {'Type':<15} {'Nullable':<10} {'Default':<15} {'PK':<5}")
        print("-" * 70)
        for row in schema:
            col_id, name, col_type, not_null, default, pk = row
            nullable = "NOT NULL" if not_null else "NULL"
            default_val = default if default else ""
            pk_marker = "✓" if pk else ""
            print(f"{name:<15} {col_type:<15} {nullable:<10} {default_val:<15} {pk_marker:<5}")
        
        # Check for DFA alerts
        print("\n" + "="*70)
        print("  DFA Detection Status")
        print("="*70 + "\n")
        
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE module = 'DFA'")
        dfa_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE module = 'ANN'")
        ann_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM alerts")
        total_count = cursor.fetchone()[0]
        
        print(f"Total Alerts: {total_count}")
        print(f"  ├─ DFA Alerts: {dfa_count}")
        print(f"  └─ ANN Alerts: {ann_count}")
        
        if dfa_count > 0:
            print("\n" + "="*70)
            print("  DFA Detections (Latest 10)")
            print("="*70 + "\n")
            
            cursor.execute('''
                SELECT id, timestamp, reason, src_ip, src_mac 
                FROM alerts 
                WHERE module = 'DFA'
                ORDER BY timestamp DESC 
                LIMIT 10
            ''')
            
            print(f"{'ID':<6} {'Time':<20} {'Reason':<40}")
            print("-" * 110)
            
            for row in cursor.fetchall():
                alert_id, timestamp, reason, src_ip, src_mac = row
                time_str = timestamp[:19] if timestamp else 'N/A'
                reason_short = reason[:60] + "..." if len(reason) > 60 else reason
                print(f"{alert_id:<6} {time_str:<20} {reason_short:<40}")
                if src_ip or src_mac:
                    print(f"       └─ IP: {src_ip or 'N/A'}, MAC: {src_mac or 'N/A'}")
        else:
            print("\n⚠ No DFA alerts found yet.")
            print("\nDFA detects ARP spoofing attacks:")
            print("  1. IP-MAC Conflicts: When same IP appears with different MAC addresses")
            print("  2. Gratuitous ARP Floods: Excessive ARP replies in short time")
            print("  3. Unauthorized ARP Replies: ARP responses without requests")
        
        if ann_count > 0:
            print("\n" + "="*70)
            print("  ANN Detections (Latest 10)")
            print("="*70 + "\n")
            
            cursor.execute('''
                SELECT id, timestamp, reason, src_ip, src_mac 
                FROM alerts 
                WHERE module = 'ANN'
                ORDER BY timestamp DESC 
                LIMIT 10
            ''')
            
            print(f"{'ID':<6} {'Time':<20} {'Reason':<40}")
            print("-" * 110)
            
            for row in cursor.fetchall():
                alert_id, timestamp, reason, src_ip, src_mac = row
                time_str = timestamp[:19] if timestamp else 'N/A'
                reason_short = reason[:60] + "..." if len(reason) > 60 else reason
                print(f"{alert_id:<6} {time_str:<20} {reason_short:<40}")
                if src_ip or src_mac:
                    print(f"       └─ IP: {src_ip or 'N/A'}, MAC: {src_mac or 'N/A'}")
        
        print("\n" + "="*70)
        print("  How DFA Works in SafeLink")
        print("="*70)
        print("""
The DFA (Deterministic Finite Automaton) Filter monitors ARP traffic for:

1. IP-MAC Mapping Conflicts
   • Tracks which MAC address is associated with each IP
   • Alerts when an IP appears with a different MAC (possible ARP spoofing)
   
2. Gratuitous ARP Flooding
   • Counts ARP packets from each MAC address
   • Default threshold: 5 packets in 5 seconds
   • Excessive ARPs indicate cache poisoning attempt

3. These alerts appear in:
   • Dashboard: http://localhost:5173/
   • Alerts Page: http://localhost:5173/alerts  
   • Database: alerts table with module='DFA'
   • Real-time via WebSocket to connected clients

⚠ Note: DFA only analyzes ARP packets, not TCP/IP traffic
""")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except FileNotFoundError:
        print("Database file 'safelink.db' not found!")

if __name__ == "__main__":
    check_schema()
