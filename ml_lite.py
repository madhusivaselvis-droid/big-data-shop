"""Analytics refresh (no Java): customer segments, recommendations, basket rules -> ecom.db.
python ml_lite.py        run once        python ml_lite.py 45     refresh every 45 seconds"""
import sqlite3, sys, time
import numpy as np, pandas as pd
from scipy.sparse import csr_matrix
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler

EVERY = int(sys.argv[1]) if len(sys.argv) > 1 else 0

def run():
    con = sqlite3.connect('ecom.db', timeout=60)
    rd = lambda sql: pd.read_sql(sql, con)

    # 1. Customer segments: RFM + KMeans
    o = rd("select user_id, order_id, order_date, total_amount from orders "
           "where order_status not in ('cancelled','returned')")
    o['order_date'] = pd.to_datetime(o.order_date, format='mixed')
    ref = o.order_date.max()
    r = o.groupby('user_id').agg(recency=('order_date', lambda s: (ref - s.max()).days),
                                 frequency=('order_id', 'count'), monetary=('total_amount', 'sum')).reset_index()
    X = StandardScaler().fit_transform(r[['recency', 'frequency', 'monetary']])
    r['c'] = KMeans(n_clusters=4, n_init=10, random_state=42).fit_predict(X)
    rank = r.groupby('c').monetary.mean().sort_values().index
    r['segment'] = r.c.map(dict(zip(rank, ['Low value', 'Regular', 'Loyal', 'Champions'])))
    r.drop(columns='c').to_sql('rfm', con, if_exists='replace', index=False)

    # 2. Recommendations: matrix factorisation (SVD) on weighted behaviour
    e = rd('select user_id, product_id, event_type from events')
    e['w'] = e.event_type.map({'view': 1.0, 'wishlist': 2.0, 'cart': 3.0, 'purchase': 5.0})
    i = e.groupby(['user_id', 'product_id'], as_index=False).w.sum()
    uid, uu = pd.factorize(i.user_id)
    pid, pp = pd.factorize(i.product_id)
    M = csr_matrix((np.log1p(i.w.values), (uid, pid)), shape=(len(uu), len(pp)))
    svd = TruncatedSVD(min(20, min(M.shape) - 1), random_state=42)
    U, V = svd.fit_transform(M), svd.components_
    out = []
    for s in range(0, len(uu), 2000):
        sc = U[s:s + 2000] @ V
        sc[M[s:s + 2000].toarray() > 0] = -1e9            # do not recommend what they already touched
        top = np.argpartition(-sc, 10, axis=1)[:, :10]
        for n, t in enumerate(top):
            for rk, j in enumerate(t[np.argsort(-sc[n, t])], 1):
                out.append((uu[s + n], pp[j], rk, float(sc[n, j])))
    pd.DataFrame(out, columns=['user_id', 'product_id', 'rk', 'score']).to_sql('recs', con, if_exists='replace',
                                                                              index=False)

    # 3. Basket rules between categories (support, confidence, lift)
    b = rd('select distinct oi.order_id, p.category from order_items oi join products p using(product_id)')
    n, cnt = b.order_id.nunique(), b.category.value_counts()
    pr = b.merge(b, on='order_id')
    pr = pr[pr.category_x != pr.category_y]
    pc = pr.groupby(['category_x', 'category_y']).size().reset_index(name='c')
    pc['support'] = pc.c / n
    pc['confidence'] = pc.c / pc.category_x.map(cnt)
    pc['lift'] = pc.confidence / (pc.category_y.map(cnt) / n)
    rl = pc[(pc.support >= 0.002) & (pc.confidence >= 0.05)].rename(
        columns={'category_x': 'if_buys', 'category_y': 'then_buys'})
    rl[['if_buys', 'then_buys', 'confidence', 'lift', 'support']].to_sql('rules', con, if_exists='replace',
                                                                          index=False)
    pd.DataFrame([{'refreshed_at': time.strftime('%H:%M:%S'), 'customers_segmented': len(r),
                   'users_with_recommendations': len(uu), 'basket_rules': len(rl)}]).to_sql(
        'ml_status', con, if_exists='replace', index=False)
    con.commit(); con.close()
    print('Analytics refreshed at', time.strftime('%H:%M:%S'))

run()
while EVERY:
    time.sleep(EVERY)
    run()
