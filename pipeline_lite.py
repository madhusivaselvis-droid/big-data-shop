"""Streaming pipeline (no Java): picks up micro-batch files from landing/ and loads them into ecom.db."""
import glob, json, os, sqlite3, time
import pandas as pd

TABLES = {
    'events': ('event', ['event_id', 'user_id', 'product_id', 'event_type', 'event_timestamp']),
    'orders': ('order_item', ['order_id', 'user_id', 'order_date', 'order_status', 'total_amount']),
    'order_items': ('order_item', ['order_item_id', 'order_id', 'product_id', 'user_id', 'quantity',
                                   'item_price', 'item_total']),
    'reviews': ('review', ['review_id', 'order_id', 'product_id', 'user_id', 'rating', 'review_text',
                           'review_date'])}
ALL = sorted({c for _, cols in TABLES.values() for c in cols} | {'kind'})
os.makedirs('landing/done', exist_ok=True)
batch = 0
print('Pipeline running: landing/ -> ecom.db')
while True:
    files = sorted(glob.glob('landing/b_*.json'))
    if files:
        rows = [json.loads(l) for f in files for l in open(f) if l.strip()]
        p = pd.DataFrame(rows).reindex(columns=ALL)
        con = sqlite3.connect('ecom.db', timeout=30)
        for table, (kind, cols) in TABLES.items():
            d = p[p.kind == kind][cols].drop_duplicates(cols[0])
            if len(d):
                d.to_sql(table, con, if_exists='append', index=False)
        ev = p[p.kind == 'event']
        if len(ev):
            m = pd.to_datetime(ev.event_timestamp).dt.strftime('%Y-%m-%d %H:%M:00')
            live = ev.groupby([m.rename('minute'), 'event_type']).size().reset_index(name='n')
            live.to_sql('live_minute', con, if_exists='append', index=False)
        batch += 1
        pd.DataFrame([{'batch_id': batch, 'time': time.strftime('%H:%M:%S'), 'records': len(p),
                       'events': len(ev), 'orders': p[p.kind == 'order_item'].order_id.nunique(),
                       'reviews': int((p.kind == 'review').sum())}]).to_sql('pipeline_log', con,
                                                                             if_exists='append', index=False)
        con.commit(); con.close()
        for f in files:
            os.replace(f, 'landing/done/' + os.path.basename(f))
        print('batch %d: %d records loaded' % (batch, len(p)))
    time.sleep(1)
