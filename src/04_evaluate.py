# -*- coding: utf-8 -*-
"""AI（Claude 子代理离线批量分类）与关键词基线，对照参考标签比较，输出逐条对照与汇总。
只读取已有的 AI 与规则预测，不会因参考标签改动而重新生成预测；复核状态按 reference_labels.csv 的 label_status 实际取值写进说明。
运行：python src/04_evaluate.py
"""
import csv, json
from common import ROOT, load_ref, load_json, read_csv, review_state

texts = {r['id']: r for r in read_csv(ROOT / 'data' / 'complaints.csv')}
ref_rows = load_ref()
ref = {r['id']: r for r in ref_rows}
ai = {r['id']: r for r in load_json('labels/claude_labels.json')}
base = {r['id']: r for r in load_json('labels/baseline_labels.json')}
base2 = {r['id']: r for r in load_json('labels/baseline_v2_labels.json')}
assert set(ref) == set(ai) == set(base) == set(base2) == set(texts), 'id 集合不一致'
state = review_state(ref_rows)


def score(pred):
    n = len(ref)
    cat_ok = sum(pred[i]['category'] == ref[i]['ref_category'] for i in ref)
    q_ref = {i for i in ref if ref[i]['ref_category'] == '质量安全'}
    q_pred = {i for i in ref if pred[i]['category'] == '质量安全'}
    h_ref = {i for i in ref if ref[i]['ref_health'] == '1'}
    h_pred = {i for i in ref if pred[i]['health_signal']}
    r_ref = {i for i in ref if ref[i]['ref_needs_review'] == '1'}
    r_pred = {i for i in ref if pred[i]['needs_review']}
    return {
        '类别一致': f'{cat_ok}/{n}',
        '类别不一致': sorted(i for i in ref if pred[i]['category'] != ref[i]['ref_category']),
        '质量安全_漏判': sorted(q_ref - q_pred),
        '质量安全_误判': sorted(q_pred - q_ref),
        '健康症状_漏判': sorted(h_ref - h_pred),
        '健康症状_误判': sorted(h_pred - h_ref),
        '需复核_一致': f'{sum((i in r_ref) == (i in r_pred) for i in ref)}/{n}',
        '需复核_不一致': sorted(i for i in ref if (i in r_ref) != (i in r_pred)),
        '标记需复核条数': len(r_pred),
    }


summary = {'AI（Claude）': score(ai), '关键词基线': score(base), '关键词基线v2（仅调换顺序）': score(base2),
           'AI 依据片段为原文逐字子串': f"{sum(ai[i]['evidence'] in texts[i]['text'] for i in ref)}/{len(ref)}",
           'AI 输出含批次号且原文确有': [i for i in ref if ai[i]['batch_no'] and ai[i]['batch_no'] in texts[i]['text']],
           '复核状态': state['short'], '已人工复核条数': f"{state['k']}/{state['n']}",
           '说明': state['long']}

rows = []
for i in ref:
    rows.append({
        'id': i, '标题': texts[i]['title'], '参考类别': ref[i]['ref_category'], '子问题': ref[i]['subtag'],
        '参考标签状态': ref[i]['label_status'],
        '基线类别': base[i]['category'], '基线命中词': base[i]['matched_keyword'], '基线v2类别': base2[i]['category'],
        'AI类别': ai[i]['category'], 'AI依据原文': ai[i]['evidence'],
        'AI健康信号': int(ai[i]['health_signal']), 'AI需复核': int(ai[i]['needs_review']), 'AI复核理由': ai[i]['review_reason'],
        '基线对': int(base[i]['category'] == ref[i]['ref_category']), 'AI对': int(ai[i]['category'] == ref[i]['ref_category']),
        '原文链接': texts[i]['url'],
    })
out = ROOT / 'outputs'
out.mkdir(exist_ok=True)
with (out / 'eval_cases.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
(out / 'eval_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')

print(f"复核状态：{state['short']}")
for name, pred in [('关键词基线', base), ('关键词基线v2（仅调换顺序）', base2), ('AI', ai)]:
    wrong = [i for i in ref if pred[i]['category'] != ref[i]['ref_category']]
    print(f'\n{name}：类别一致 {len(ref) - len(wrong)}/{len(ref)}')
    for i in wrong:
        hint = f"命中「{pred[i]['matched_keyword']}」" if 'matched_keyword' in pred[i] else f"依据「{pred[i]['evidence']}」"
        print(f"  {i} 参考={ref[i]['ref_category']} 预测={pred[i]['category']}（{hint}） | {texts[i]['title']}")
print('\nAI 需复核与参考不一致：')
for i in summary['AI（Claude）']['需复核_不一致']:
    print(f"  {i} 参考={ref[i]['ref_needs_review']} AI={int(ai[i]['needs_review'])} 理由「{ai[i]['review_reason']}」 | {texts[i]['title']}")
