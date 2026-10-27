"""Loads the 6 CSV files from data/ into ecom.db. Creates sample CSVs first if data/ is empty."""
import os, shutil, sqlite3, subprocess, sys
import pandas as pd

if not os.path.exists('data/events.csv'):
    print('No CSV files in data/, creating sample data...')
    subprocess.run([sys.executable, 'make_sample_data.py'], check=True)
for d in ('landing', 'chk'):
    shutil.rmtree(d, ignore_errors=True)
os.makedirs('landing/done', exist_ok=True)
if os.path.exists('ecom.db'):
    os.remove('ecom.db')
con = sqlite3.connect('ecom.db')
con.execute('PRAGMA journal_mode=WAL')
for t in ['users', 'products', 'orders', 'order_items', 'events', 'reviews']:
    df = pd.read_csv('data/%s.csv' % t)
    df.to_sql(t, con, index=False)
    print('loaded %-12s %7d rows' % (t, len(df)))
con.execute('CREATE INDEX ix_ev_ts ON events(event_timestamp)')
con.execute('CREATE INDEX ix_ord_user ON orders(user_id)')
con.execute('CREATE INDEX ix_oi_order ON order_items(order_id)')
con.commit()
print('ecom.db ready')
