"""Creates the 6 CSV files (same columns as your dataset) in data/. Used only when you have not added your own."""
import os
import numpy as np, pandas as pd

rng = np.random.default_rng(42)
os.makedirs('data', exist_ok=True)
NU, NP, NE, NO = 10000, 2000, 80000, 20000
CATS = ['Clothing', 'Groceries', 'Sports', 'Electronics', 'Home & Kitchen', 'Toys', 'Pet Supplies', 'Books',
        'Automotive', 'Beauty']
BRANDS = ['Astra', 'NeoTech', 'Acme', 'Nimbus', 'Zenith', 'Everest', 'Harbor', 'Orion', 'GreenLeaf', 'Solace',
          'Willow', 'Pulse']
NOUNS = ['Pro', 'Max', 'Lite', 'Plus', 'Air', 'Edge', 'One', 'Prime', 'Go', 'Flex', 'Core', 'Neo']
CITIES = ['Chennai', 'Mumbai', 'Delhi', 'Bengaluru', 'Hyderabad', 'Pune', 'Kolkata', 'Kochi', 'Madurai',
          'Nagercoil', 'Jaipur', 'Surat', 'Lucknow', 'Coimbatore', 'Nagpur']
POS = ['Works perfectly!', 'Excellent product, will buy again.', 'Fast shipping and good packaging.',
       'Value for money.', 'Highly recommend this brand.', 'Customer service was helpful.']
NEU = ['Decent product for the price.']
NEG = ['Color was different from images.', 'Not as expected, quality is poor.', 'Item arrived damaged.']
now = pd.Timestamp.now()

def stamp(n, days):
    return pd.Series(now - pd.to_timedelta(rng.integers(0, days * 86400, n), unit='s')).dt.strftime(
        '%Y-%m-%dT%H:%M:%S.%f')

users = pd.DataFrame({'user_id': ['U%06d' % i for i in range(1, NU + 1)]})
users['name'] = ['Customer %d' % i for i in range(1, NU + 1)]
users['email'] = ['customer%d@example.com' % i for i in range(1, NU + 1)]
users['gender'] = rng.choice(['Male', 'Female', 'Other'], NU, p=[.48, .48, .04])
users['city'] = rng.choice(CITIES, NU)
users['signup_date'] = pd.Series(now - pd.to_timedelta(rng.integers(150, 700, NU), unit='D')).dt.strftime('%d-%m-%Y')

cat_idx = rng.integers(0, 10, NP)
products = pd.DataFrame({'product_id': ['P%06d' % i for i in range(1, NP + 1)]})
products['brand'] = rng.choice(BRANDS, NP)
products['product_name'] = products.brand + ' ' + rng.choice(NOUNS, NP)
products['category'] = np.array(CATS)[cat_idx]
products['price'] = rng.uniform(5, 500, NP).round(2)
products['rating'] = rng.uniform(2.5, 5, NP).round(2)
products = products[['product_id', 'product_name', 'category', 'brand', 'price', 'rating']]

fav = rng.integers(0, 10, NU)                       # each customer prefers one category
by_cat = [np.where(cat_idx == c)[0] for c in range(10)]
def pick(uidx):                                      # 60% of picks come from the favourite category
    prod = rng.integers(0, NP, len(uidx))
    use = rng.random(len(uidx)) < 0.6
    for c in range(10):
        m = use & (fav[uidx] == c)
        prod[m] = rng.choice(by_cat[c], m.sum())
    return prod

eu = rng.integers(0, NU, NE)
events = pd.DataFrame({'event_id': ['E%08d' % i for i in range(1, NE + 1)], 'user_id': users.user_id.values[eu],
                       'product_id': products.product_id.values[pick(eu)],
                       'event_type': rng.choice(['view', 'cart', 'wishlist', 'purchase'], NE, p=[.55, .18, .12, .15]),
                       'event_timestamp': stamp(NE, 120)})

ou = rng.integers(0, NU, NO)
k = rng.choice([1, 2, 3], NO, p=[.5, .3, .2])
oidx = np.repeat(np.arange(NO), k)
ip = pick(ou[oidx])
first = np.r_[True, oidx[1:] != oidx[:-1]]                 # companion categories give real basket rules
first_cat = cat_idx[ip[first]][np.cumsum(first) - 1]
comp = (~first) & (rng.random(len(ip)) < 0.5)
for c in range(10):
    m = comp & (((first_cat + 3) % 10) == c)
    ip[m] = rng.choice(by_cat[c], m.sum())
qty = rng.choice([1, 2, 3], len(oidx))
price = products.price.values[ip]
items = pd.DataFrame({'order_item_id': ['I%08d' % i for i in range(1, len(oidx) + 1)],
                      'order_id': ['O%08d' % (i + 1) for i in oidx], 'product_id': products.product_id.values[ip],
                      'user_id': users.user_id.values[ou[oidx]], 'quantity': qty, 'item_price': price,
                      'item_total': (price * qty).round(2)})
orders = pd.DataFrame({'order_id': ['O%08d' % i for i in range(1, NO + 1)], 'user_id': users.user_id.values[ou],
                       'order_date': stamp(NO, 120),
                       'order_status': rng.choice(['processing', 'completed', 'cancelled', 'returned', 'shipped'],
                                                  NO, p=[.2, .4, .1, .08, .22]),
                       'total_amount': np.bincount(oidx, weights=items.item_total.values).round(2)})

ri = rng.choice(len(items), 15000, replace=False)
rating = rng.choice([1, 2, 3, 4, 5], 15000, p=[.08, .09, .15, .3, .38])
text = [rng.choice(POS) if r >= 4 else rng.choice(NEU) if r == 3 else rng.choice(NEG) for r in rating]
reviews = pd.DataFrame({'review_id': ['R%08d' % i for i in range(1, 15001)], 'order_id': items.order_id.values[ri],
                        'product_id': items.product_id.values[ri], 'user_id': items.user_id.values[ri],
                        'rating': rating, 'review_text': text, 'review_date': stamp(15000, 100)})

for n, d in [('users', users), ('products', products), ('orders', orders), ('order_items', items),
             ('events', events), ('reviews', reviews)]:
    d.to_csv('data/%s.csv' % n, index=False)
    print('created data/%s.csv  (%d rows)' % (n, len(d)))
