# -*- coding: utf-8 -*-
"""执行 src/analysis.sql 的每段查询（SQLite），打印结果并导出 outputs/sql_*.csv。
运行：python src/03_run_sql.py
"""
import csv, re, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs'
OUT.mkdir(exist_ok=True)

con = sqlite3.connect(ROOT / 'data' / 'case.db')
ref = list(csv.DictReader((ROOT / 'labels' / 'reference_labels.csv').open(encoding='utf-8-sig')))
con.execute('DROP TABLE IF EXISTS ref')
con.execute('CREATE TABLE ref (id TEXT PRIMARY KEY, ref_category TEXT, ref_health INT, ref_needs_review INT, subtag TEXT, note TEXT, label_status TEXT)')
con.executemany('INSERT INTO ref VALUES (?,?,?,?,?,?,?)', [tuple(r.values()) for r in ref])

sql = (ROOT / 'src' / 'analysis.sql').read_text(encoding='utf-8')
for name, body in re.findall(r'-- @(\S+)\n(.*?)(?=\n-- @|\Z)', sql, flags=re.S):
    cur = con.execute(body)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print(f'\n== {name}（{len(rows)} 行）')
    print(' | '.join(cols))
    for row in rows:
        print(' | '.join(str(x) for x in row))
    with (OUT / f'sql_{name}.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
con.commit(); con.close()
