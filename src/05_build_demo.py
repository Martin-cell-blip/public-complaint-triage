# -*- coding: utf-8 -*-
"""把 41 条样本与 Claude 离线分类结果嵌进单页演示：demo/投诉分拣演示.html（双击即可打开，无需服务器）。
运行：python src/05_build_demo.py
"""
import json
from common import ROOT, load_ref, load_json, read_csv, review_state

texts = {r['id']: r for r in read_csv(ROOT / 'data' / 'complaints.csv')}
ai = load_json('labels/claude_labels.json')
state = review_state(load_ref())
sample = [{**a, 'date': texts[a['id']]['date'], 'text': texts[a['id']]['text'], 'url': texts[a['id']]['url']} for a in ai]

html = (ROOT / 'src' / 'demo_template.html').read_text(encoding='utf-8')
html = html.replace('/*DATA*/null', json.dumps(sample, ensure_ascii=False)).replace('__REVIEW_NOTE__', state['short'])
out = ROOT / 'demo' / '投诉分拣演示.html'
out.parent.mkdir(exist_ok=True)
out.write_text(html, encoding='utf-8')
print('写出：', out, f"（{len(sample)} 条；{state['short']}）")
