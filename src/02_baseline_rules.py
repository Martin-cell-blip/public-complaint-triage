# -*- coding: utf-8 -*-
"""关键词规则基线：与 AI 用同一批文本、同一套类别。按「质量安全 → 活动权益 → 订单发货」顺序取第一个命中，都不命中记「其他」。
这是一个运营同学一下午就能写出来的版本，故意不调参，用来回答「AI 比简单规则多做到了什么」。
运行：python src/02_baseline_rules.py
"""
import csv, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = [
    ('质量安全', r'异物|虫|怪味|有味道|变质|结块|絮状|颗粒|毛发|卷毛|拉稀|拉肚子|吐奶|勺'),
    ('活动权益', r'集罐|扫码|买一送一|买一赠一|赠品|补贴|积分|活动|权益|兑换|礼赠|送一罐'),
    ('订单发货', r'不发货|拒发|拒绝发货|发货|订单异常|拦截|取消.*订单|限购'),
]
HEALTH = r'拉稀|拉肚子|腹泻|吐奶|呕吐|便秘|大便干结|过敏|发烧'

# v2 只调换顺序（订单发货提到活动权益前面），用来检验「是不是排个序就能修好」
VARIANTS = {'baseline_labels.json': RULES, 'baseline_v2_labels.json': [RULES[0], RULES[2], RULES[1]]}
rows = list(csv.DictReader((ROOT / 'data' / 'complaints.csv').open(encoding='utf-8-sig')))

from collections import Counter
for fname, rules in VARIANTS.items():
    out = []
    for r in rows:
        cat, hit = '其他', ''
        for name, pat in rules:
            m = re.search(pat, r['text'])
            if m:
                cat, hit = name, m.group(0)
                break
        health = bool(re.search(HEALTH, r['text']))
        out.append({'id': r['id'], 'category': cat, 'matched_keyword': hit, 'health_signal': health,
                    'needs_review': cat == '质量安全' or health})
    (ROOT / 'labels' / fname).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(fname, '类别分布：', dict(Counter(o['category'] for o in out)))
