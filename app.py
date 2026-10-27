import sqlite3, time
from contextlib import closing
import pandas as pd, plotly.express as px, streamlit as st

st.set_page_config(page_title='ShopPulse | Live e-commerce analytics', page_icon='🛍️', layout='wide')
PAL = ['#4F46E5', '#0EA5E9', '#F59E0B', '#10B981', '#EF4444', '#8B5CF6', '#EC4899', '#64748B']
px.defaults.template = 'plotly_white'
px.defaults.color_discrete_sequence = PAL
VALID = "order_status not in ('cancelled','returned')"

st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp {font-family:'Plus Jakarta Sans',sans-serif; background:#FFFFFF;}
.block-container {padding-top:1.6rem; max-width:1440px;}
h1 {font-weight:800; letter-spacing:-.8px; color:#0F172A; margin-bottom:0;}
.sub {color:#64748B; margin:2px 0 18px; font-size:15px;}
.dot {display:inline-block; width:9px; height:9px; border-radius:50%; background:#10B981; margin-right:8px;
      animation:pulse 1.6s infinite;}
@keyframes pulse {0%{box-shadow:0 0 0 0 rgba(16,185,129,.55)} 100%{box-shadow:0 0 0 10px rgba(16,185,129,0)}}
.kpi {background:#FFFFFF; border:1px solid #E2E8F0; border-left:5px solid var(--c); border-radius:12px;
      padding:14px 18px; box-shadow:0 2px 10px rgba(15,23,42,.05);}
.kpi small {color:#64748B; font-weight:600; font-size:13px;}
.kpi h2 {margin:2px 0 0; font-size:29px; font-weight:800; color:#0F172A;}
.kpi em {font-style:normal; font-size:12.5px; font-weight:600; color:#059669;}
.stTabs [data-baseweb="tab"] {font-weight:600; font-size:15px;}
</style>''', unsafe_allow_html=True)

def q(sql, params=()):
    try:
        with closing(sqlite3.connect('ecom.db', timeout=30)) as c:
            return pd.read_sql(sql, c, params=params)
    except Exception:
        return pd.DataFrame()

K = [0]
def show(fig, h=340):
    K[0] += 1
    fig.update_layout(height=h, margin=dict(t=48, b=10, l=10, r=10), paper_bgcolor='white', plot_bgcolor='white',
                      font=dict(family='Plus Jakarta Sans, sans-serif', color='#334155'),
                      title=dict(font=dict(size=16, color='#0F172A')),
                      legend=dict(orientation='h', y=-0.18, title=None))
    try:
        st.plotly_chart(fig, width='stretch', key='c%d' % K[0])
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, key='c%d' % K[0])

def table(df):
    try:
        st.dataframe(df, width='stretch', hide_index=True)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True)

def waiting(msg):
    st.info(msg)

st.title('🛍️ ShopPulse')
with st.sidebar:
    st.header('Dashboard settings')
    paused = st.toggle('Pause live updates', False)
    every = st.slider('Refresh every (seconds)', 2, 30, 3)
    topn = st.slider('Top products to show', 5, 20, 10)
    st.caption('Data flow: live generator, streaming pipeline, database, this dashboard.')

def body():
    K[0] = 0
    st.markdown("<p class=sub><span class=dot></span>Live data, last refreshed %s</p>" % time.strftime('%H:%M:%S'),
                unsafe_allow_html=True)
    k = q("select (select sum(total_amount) from orders where %s) rev,"
          "(select count(*) from orders) orders, (select count(*) from orders where %s) vo,"
          "(select count(distinct user_id) from events) shoppers, (select count(*) from events) events,"
          "(select count(*) from events where event_type='view') views,"
          "(select count(*) from events where event_type='purchase') buys" % (VALID, VALID))
    if k.empty:
        st.error('ecom.db not found. Run python db_init.py first.'); return
    k = k.iloc[0]
    prev = st.session_state.get('prev', {})
    cards = [('Revenue', '{:,.0f}'.format(k.rev), '#4F46E5', 'rev'), ('Orders', '{:,.0f}'.format(k.orders), '#0EA5E9', 'orders'),
             ('Active shoppers', '{:,.0f}'.format(k.shoppers), '#10B981', 'shoppers'),
             ('Events tracked', '{:,.0f}'.format(k.events), '#F59E0B', 'events'),
             ('Average order value', '{:,.2f}'.format(k.rev / max(k.vo, 1)), '#8B5CF6', None),
             ('View to purchase', '{:.1%}'.format(k.buys / max(k.views, 1)), '#EC4899', None)]
    for col, (lab, val, clr, key) in zip(st.columns(6), cards):
        d = ''
        if key and key in prev and k[key] > prev[key]:
            d = '<em>+{:,.0f} just now</em>'.format(k[key] - prev[key])
        col.markdown("<div class=kpi style='--c:%s'><small>%s</small><h2>%s</h2>%s</div>" % (clr, lab, val, d),
                     unsafe_allow_html=True)
    st.session_state['prev'] = {x: k[x] for x in ['rev', 'orders', 'shoppers', 'events']}
    st.write('')

    t = st.tabs(['Live overview', 'Customers', 'Recommendations', 'Basket rules', 'Reviews', 'Pipeline health'])

    with t[0]:
        a, b = st.columns([2, 1])
        lm = q('select minute, event_type, sum(n) n from live_minute group by 1, 2 order by 1 desc limit 240')
        with a:
            if lm.empty:
                waiting('No live traffic yet. Start generator.py and stream_pipeline.py.')
            else:
                show(px.area(lm.sort_values('minute'), x='minute', y='n', color='event_type',
                             title='Live traffic per minute', labels={'n': 'events', 'minute': ''}))
        with b:
            show(px.pie(q('select event_type, count(*) n from events group by 1'), names='event_type',
                        values='n', hole=.6, title='Behaviour mix'))
        a, b = st.columns(2)
        with a:
            rv = q("select substr(order_date,1,10) day, sum(total_amount) revenue from orders where %s "
                   "group by 1 order by 1 desc limit 45" % VALID).sort_values('day')
            fig = px.area(rv, x='day', y='revenue', title='Daily revenue (latest days)', labels={'day': ''})
            fig.update_xaxes(type='category', nticks=8)
            show(fig)
        with b:
            show(px.bar(q("select p.category, sum(oi.item_total) revenue from order_items oi "
                          "join orders o using(order_id) join products p using(product_id) where o.%s "
                          "group by 1 order by 2 desc" % VALID), x='category', y='revenue', color='category',
                        title='Revenue by category').update_layout(showlegend=False))
        a, b = st.columns([3, 2])
        with a:
            tp = q("select p.product_name, p.category, sum(oi.item_total) revenue from order_items oi "
                   "join orders o using(order_id) join products p using(product_id) where o.%s "
                   "group by oi.product_id order by 3 desc limit ?" % VALID, (topn,)).sort_values('revenue')
            show(px.bar(tp, x='revenue', y='product_name', orientation='h', color='category',
                        title='Top %d products by revenue' % topn, labels={'product_name': ''}), 400)
        with b:
            st.markdown('**Latest customer activity**')
            table(q("select substr(e.event_timestamp,12,8) time, e.user_id, p.product_name product, "
                    "e.event_type action from events e join products p using(product_id) "
                    "order by e.event_timestamp desc limit 14"))

    with t[1]:
        r = q('select * from rfm')
        if r.empty:
            waiting('Segments appear after batch_ml.py finishes its first run.')
        else:
            seg = r.groupby('segment').agg(customers=('user_id', 'count'), avg_recency_days=('recency', 'mean'),
                                           avg_orders=('frequency', 'mean'), avg_spend=('monetary', 'mean')
                                           ).round(1).reset_index()
            a, b = st.columns(2)
            with a:
                show(px.bar(seg, x='segment', y='customers', color='segment', title='Customers per segment')
                     .update_layout(showlegend=False))
            with b:
                show(px.scatter(r.sample(min(len(r), 2500), random_state=1), x='frequency', y='monetary',
                                color='segment', opacity=.7, title='Order count vs spend'))
            table(seg)

    with t[2]:
        rc = q('select distinct user_id from recs order by 1')
        if rc.empty:
            waiting('Recommendations appear after batch_ml.py finishes its first run.')
        else:
            uid = st.selectbox('Choose a customer', rc.user_id.tolist(), key='uid')
            u = q('select r.rk as rank, r.product_id, p.product_name, p.category, p.brand, p.price, '
                  'round(r.score, 3) score from recs r join products p using(product_id) '
                  'where r.user_id = ? order by r.rk', (uid,))
            seg = q('select segment from rfm where user_id = ?', (uid,))
            if len(seg):
                st.success('Segment: ' + seg.segment.iloc[0])
            show(px.bar(u, x='product_name', y='score', color='category', title='Top 10 picks for ' + uid,
                        labels={'product_name': ''}))
            table(u)

    with t[3]:
        ru = q('select * from rules order by lift desc')
        if ru.empty:
            waiting('No rules yet. They appear after batch_ml.py runs and enough orders exist.')
        else:
            show(px.scatter(ru, x='support', y='confidence', size='lift', color='lift', hover_name='if_buys',
                            title='Category association rules (bubble size is lift)',
                            color_continuous_scale='Blues'))
            table(ru.round(3))

    with t[4]:
        a, b = st.columns(2)
        with a:
            show(px.pie(q("select case when rating>=4 then 'Positive' when rating=3 then 'Neutral' "
                          "else 'Negative' end sentiment, count(*) n from reviews group by 1"),
                        names='sentiment', values='n', hole=.6, color='sentiment', title='Review sentiment',
                        color_discrete_map={'Positive': '#10B981', 'Neutral': '#F59E0B', 'Negative': '#EF4444'}))
        with b:
            show(px.bar(q('select p.category, round(avg(r.rating), 2) avg_rating from reviews r '
                          'join products p using(product_id) group by 1 order by 2'), x='avg_rating',
                        y='category', orientation='h', color='avg_rating', color_continuous_scale='Blues',
                        title='Average rating by category'))
        show(px.bar(q('select review_text, count(*) n from reviews group by 1 order by 2'), x='n',
                    y='review_text', orientation='h', title='What customers say', labels={'review_text': ''}), 380)

    with t[5]:
        a, b = st.columns(2)
        with a:
            show(px.bar(q("select 'events' tbl, count(*) rows_in_db from events union all "
                          "select 'orders', count(*) from orders union all select 'order_items', count(*) "
                          "from order_items union all select 'reviews', count(*) from reviews union all "
                          "select 'users', count(*) from users union all select 'products', count(*) from products"),
                        x='tbl', y='rows_in_db', color='tbl', title='Rows in database')
                 .update_layout(showlegend=False))
        with b:
            pl = q('select * from pipeline_log order by batch_id desc limit 30')
            if pl.empty:
                waiting('Pipeline has not loaded a batch yet.')
            else:
                show(px.line(pl.sort_values('batch_id'), x='batch_id', y='records', markers=True,
                             title='Records loaded per Spark micro-batch'))
        st.markdown('**Machine learning job**')
        table(q('select * from ml_status'))
        st.markdown('**Recent micro-batches**')
        table(q('select * from pipeline_log order by batch_id desc limit 10'))

st.fragment(body, run_every=None if paused else every)()
