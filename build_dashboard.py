from pathlib import Path
import html, json
import pandas as pd

PAGE_CSS = '*{box-sizing:border-box}body{margin:0;background:#f3f6fa;color:#1e293b;font:15px/1.5 Segoe UI,Arial,sans-serif}.wrap{max-width:1100px;margin:32px auto;padding:0 22px}.hero{background:linear-gradient(120deg,#123b5d,#176b87);color:white;padding:28px 32px;border-radius:18px}.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.8}.hero h1{margin:5px 0;font-size:28px}.hero p{margin:0;max-width:800px;color:#d9ecf3}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:18px 0}.card,.panel{background:white;border:1px solid #e2e8f0;border-radius:14px;padding:18px;box-shadow:0 3px 12px #0f172a0a}.card small{display:block;color:#64748b}.card strong{display:block;font-size:23px;margin-top:6px;color:#123b5d}.panel h2{font-size:18px;margin:0 0 6px}.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}.tabs button{border:1px solid #cbd5e1;background:white;color:#334155;border-radius:20px;padding:7px 13px;cursor:pointer}.tabs button.active{background:#14558a;color:#fff;border-color:#14558a}.barrow{display:grid;grid-template-columns:minmax(120px,220px) 1fr 90px;gap:12px;align-items:center;margin:12px 0}.label{font-size:13px;color:#334155}.track{height:15px;border-radius:20px;background:#edf2f7;overflow:hidden}.bar{height:100%;border-radius:20px;background:linear-gradient(90deg,#20a4a8,#23679a)}.value{text-align:right;font-variant-numeric:tabular-nums;font-size:13px;color:#475569}.note{background:#fff9e8;border-left:4px solid #e0a72e;padding:14px 16px;border-radius:8px;margin-top:15px;color:#5b4b2b}.foot{font-size:12px;color:#64748b;margin:18px 2px}@media(max-width:600px){.barrow{grid-template-columns:100px 1fr 70px}.hero{padding:22px}.wrap{padding:0 12px}}'

def pct(x): return f'{x:.1%}'
def count(x): return f'{x:,.0f}'
def render(title, intro, cards, charts, caveat, source):
    safe_cards=''.join(f'<div class="card"><small>{html.escape(k)}</small><strong>{html.escape(v)}</strong></div>' for k,v in cards)
    data=json.dumps({'charts':charts},ensure_ascii=False)
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} | Analytics Dashboard</title><style>{PAGE_CSS}</style></head><body><main class="wrap"><header class="hero"><div class="eyebrow">Portfolio analytics case study</div><h1>{html.escape(title)}</h1><p>{html.escape(intro)}</p></header><section class="cards">{safe_cards}</section><section class="panel"><h2>Explore the analysis</h2><p id="subtitle"></p><nav id="tabs" class="tabs"></nav><div id="chart" aria-live="polite"></div></section><aside class="note"><strong>Data limitation:</strong> {html.escape(caveat)}</aside><p class="foot">Source: {html.escape(source)}. Dashboard calculations are descriptive and should be interpreted in the context of the source data.</p></main><script>const DATA={data};const tabs=document.getElementById('tabs'),chart=document.getElementById('chart'),subtitle=document.getElementById('subtitle');function draw(i){{const d=DATA.charts[i];subtitle.textContent=d.title;chart.innerHTML='';const max=Math.max(...d.values.map(x=>x.value),1);d.values.forEach(x=>{{const row=document.createElement('div');row.className='barrow';const lab=document.createElement('div');lab.className='label';lab.textContent=x.label;const track=document.createElement('div');track.className='track';const bar=document.createElement('div');bar.className='bar';bar.style.width=Math.max(2,100*x.value/max)+'%';const val=document.createElement('span');val.className='value';val.textContent=x.display||x.value;track.appendChild(bar);row.append(lab,track,val);chart.appendChild(row)}});[...tabs.children].forEach((b,j)=>b.classList.toggle('active',j===i))}}DATA.charts.forEach((d,i)=>{{const b=document.createElement('button');b.textContent=d.tab;b.onclick=()=>draw(i);tabs.appendChild(b)}});draw(0);</script></body></html>'''
    Path(__file__).with_name('dashboard.html').write_text(page,encoding='utf-8')

DATA=Path(__file__).with_name('Online_Retail.xlsx')
df=pd.read_excel(DATA,engine='openpyxl')
df['InvoiceNo']=df['InvoiceNo'].astype(str)
df['InvoiceDate']=pd.to_datetime(df['InvoiceDate'],errors='coerce')
df['is_cancellation']=df['InvoiceNo'].str.upper().str.startswith('C')
df['line_value']=df['Quantity']*df['UnitPrice']
df['cancel_value']=df['line_value'].abs().where(df.is_cancellation,0)
df['month']=df.InvoiceDate.dt.to_period('M').astype(str)
df['Description']=df['Description'].fillna('Unknown')
df['Country']=df['Country'].fillna('Unknown')
monthly=df[df.is_cancellation].groupby('month').agg(value=('cancel_value','sum')).reset_index()
products=df[df.is_cancellation].groupby('Description').cancel_value.sum().sort_values(ascending=False).head(10)
countries=df[df.is_cancellation].groupby('Country').cancel_value.sum().sort_values(ascending=False).head(10)
def make_values(series): return [{'label':str(k)[:32],'value':float(v),'display':f'£{v:,.0f}'} for k,v in series.items()]
charts=[{'tab':'Monthly','title':'Cancellation-associated value by month (£)','values':make_values(monthly.set_index('month').value)},{'tab':'Descriptions','title':'Top descriptions associated with cancellation value (£)','values':make_values(products)},{'tab':'Countries','title':'Countries by cancellation-associated value (£)','values':make_values(countries)}]
cancelled=df[df.is_cancellation]
render('E-commerce Cancellations and Sales Value Analysis','An operations case study to locate cancellation patterns by month, item description, and country.',[('Transaction rows',count(len(df))),('Sales invoices',count(df.loc[~df.is_cancellation,'InvoiceNo'].nunique())),('Cancellation invoices',count(cancelled.InvoiceNo.nunique())),('Associated value',f'£{cancelled.cancel_value.sum():,.0f}')],charts,'Invoice numbers beginning with C identify cancellation records in this source. The calculated value is associated transaction value; the data does not contain reasons, confirmed refunds, margin, or recoverable revenue.','UCI Online Retail dataset: archive.ics.uci.edu/dataset/352/online-retail')
print('Wrote dashboard.html')
