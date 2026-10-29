# -*- coding: utf-8 -*-
"""读取黑猫投诉公开版 JSON（data/public/，由 00_anonymize.py 从原始件脱敏生成）→ 清洗、派生字段
→ data/complaints.csv + data/case.db（SQLite 表 complaints）。
运行：python src/01_prepare.py
"""
import json, re, sqlite3, csv, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'public' / 'heimao_xingfeifan_20261015_public.json'
CSV_OUT = ROOT / 'data' / 'complaints.csv'
DB = ROOT / 'data' / 'case.db'

if not RAW.exists():
    raise SystemExit(f'公开版数据不存在：{RAW}。持有原始件时先运行 python src/00_anonymize.py 生成。')
raw = json.loads(RAW.read_text(encoding='utf-8'))

# 文本提及的渠道：只认明写的平台/门店词，没写就是「未说明」；提及≠购买渠道（如「等小程序更新」也会命中），只作粗分
CHANNELS = [
    ('京东', r'京东'), ('天猫/淘宝', r'天猫|淘宝'), ('抖音', r'抖音'), ('拼多多', r'拼多多'),
    ('飞鹤小程序/星妈会', r'小程序|星妈会'),
    ('线下门店', r'门店|实体店|母婴店|孩子王|代理|商行|生活馆|乐友|授权店|宝城店|店面'),
]
HEALTH = r'拉稀|拉肚子|腹泻|吐奶|呕吐|便秘|大便干结|过敏|发烧|湿疹|住院'
BATCH = r'批次[号]?\s*[:：]?\s*([0-9A-Z]{8,})'

rows, seen = [], set()
for r in raw['rows']:
    if r['id'] in seen:          # 去重：按平台投诉单号
        continue
    seen.add(r['id'])
    text = f"{r['title']}。{r['excerpt']}"
    channels = [name for name, pat in CHANNELS if re.search(pat, text)]
    m = re.search(BATCH, text)
    rows.append({
        'id': r['id'],
        'date': r['date'],
        'week': f"{r['date'][:4]}-W{datetime.date.fromisoformat(r['date']).isocalendar()[1]:02d}",
        'status': r['status'],
        'title': r['title'],
        'excerpt': r['excerpt'],
        'text': text,
        'demand': r['demand'],
        'channel_mentioned': '、'.join(channels) if channels else '未说明',
        'truncated': int(r['excerpt'].endswith('...')),
        'health_mention': int(bool(re.search(HEALTH, text))),
        'batch_no': m.group(1) if m else '',
        'text_len': len(text),
        'url': f"https://tousu.sina.com.cn/complaint/view/{r['id']}/",
    })

with CSV_OUT.open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)

DB.unlink(missing_ok=True)
con = sqlite3.connect(DB)
cols = list(rows[0])
con.execute(f"CREATE TABLE complaints ({', '.join(c + (' TEXT PRIMARY KEY' if c == 'id' else '') for c in cols)})")
con.executemany(f"INSERT INTO complaints VALUES ({','.join('?' * len(cols))})", [tuple(r[c] for c in cols) for r in rows])
con.commit(); con.close()

print(f"原始 {len(raw['rows'])} 条 → 去重后 {len(rows)} 条；摘要被截断 {sum(r['truncated'] for r in rows)} 条；"
      f"提到健康症状 {sum(r['health_mention'] for r in rows)} 条；写明批次号 {sum(bool(r['batch_no']) for r in rows)} 条")
print('写出：', CSV_OUT, DB)
