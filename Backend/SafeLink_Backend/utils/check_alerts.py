from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import DATABASE_URL
from core.alert_system import Alert

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

count = session.query(Alert).count()
print(f'Total alerts in database: {count}')

if count > 0:
    alerts = session.query(Alert).limit(5).all()
    print('\nFirst 5 alerts:')
    for a in alerts:
        print(f'ID={a.id}, Time={a.timestamp}, Module={a.module}, Reason={a.reason[:50] if a.reason else None}, IP={a.src_ip}')
else:
    print('\nNo alerts found. Creating a test alert...')
    from core.alert_system import AlertSystem
    alert_system = AlertSystem()
    alert_system.alert(
        module='TEST',
        reason='Test alert for CSV download',
        ip='192.168.1.100',
        mac='AA:BB:CC:DD:EE:FF',
        details={'test': True}
    )
    print('Test alert created!')

session.close()
