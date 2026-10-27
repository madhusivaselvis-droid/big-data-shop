"""Simulates a live shop: drops a JSON micro-batch into landing/ every TICK seconds."""
import datetime as dt, json, os, random, sqlite3, time

TICK = float(os.environ.get('TICK', '2'))
os.makedirs('landing', exist_ok=True)
con = sqlite3.connect('ecom.db')
users = [r[0] for r in con.execute('select user_id from users')]
prods = con.execute('select product_id, price from products').fetchall()

def last(t, c):
    v = con.execute('select max(%s) from %s' % (c, t)).fetchone()[0]
    return int(v[1:]) if v else 0

ctr = {'E': last('events', 'event_id'), 'O': last('orders', 'order_id'),
       'I': last('order_items', 'order_item_id'), 'R': last('reviews', 'review_id')}
def nid(k):
    ctr[k] += 1
    return '%s%08d' % (k, ctr[k])

TYPES, W = ['view', 'cart', 'wishlist', 'purchase'], [60, 18, 10, 12]
STATUS = ['processing'] * 50 + ['shipped'] * 30 + ['completed'] * 10 + ['cancelled'] * 6 + ['returned'] * 4
TEXT = ['Works perfectly!', 'Excellent product, will buy again.', 'Fast shipping and good packaging.',
        'Value for money.', 'Decent product for the price.', 'Highly recommend this brand.',
        'Customer service was helpful.', 'Color was different from images.',
        'Not as expected, quality is poor.', 'Item arrived damaged.']
recent = []
print('Generator running. Ctrl+C to stop.')
while True:
    now, rows = dt.datetime.now().isoformat(), []
    for _ in range(random.randint(5, 15)):
        u, (p, price), t = random.choice(users), random.choice(prods), random.choices(TYPES, W)[0]
        if t == 'purchase':
            oid, lines = nid('O'), []
            for _ in range(random.randint(1, 3)):
                pid, pr = random.choice(prods)
                q = random.randint(1, 3)
                lines.append((pid, q, pr, round(pr * q, 2)))
            total = round(sum(l[3] for l in lines), 2)
            for pid, q, pr, tot in lines:
                rows.append({'kind': 'order_item', 'order_item_id': nid('I'), 'order_id': oid, 'user_id': u,
                             'product_id': pid, 'quantity': q, 'item_price': pr, 'item_total': tot,
                             'order_date': now, 'order_status': random.choice(STATUS), 'total_amount': total})
            recent.append((oid, u, lines[0][0]))
            p = lines[0][0]
        rows.append({'kind': 'event', 'event_id': nid('E'), 'user_id': u, 'product_id': p,
                     'event_type': t, 'event_timestamp': now})
    if recent and random.random() < 0.3:
        oid, u, p = random.choice(recent[-50:])
        rows.append({'kind': 'review', 'review_id': nid('R'), 'order_id': oid, 'user_id': u, 'product_id': p,
                     'rating': random.choices([5, 4, 3, 2, 1], [35, 30, 15, 10, 10])[0],
                     'review_text': random.choice(TEXT), 'review_date': now})
    tmp = 'landing/_tmp'
    with open(tmp, 'w') as f:
        f.write('\n'.join(json.dumps(r) for r in rows))
    os.replace(tmp, 'landing/b_%d.json' % time.time_ns())   # atomic hand-off to Spark
    print(dt.datetime.now().strftime('%H:%M:%S'), len(rows), 'records ->', 'landing/')
    time.sleep(TICK)
