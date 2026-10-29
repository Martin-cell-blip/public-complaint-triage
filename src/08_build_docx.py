# -*- coding: utf-8 -*-
"""按最终参考标签、评测结果和成本公式填充 src/case_template.txt，用 pandoc 生成 Word 案例。
数字、表格与复核状态说明都在这里计算；正文里举的具体例子各依赖一个事实，复核若改变了这些事实，
脚本列出需要改写的段落后停止，不输出与数据不符的文档。
运行：python src/08_build_docx.py（需要 pandoc；在 03、04 之后运行）
"""
import os, re, subprocess, sys
from pathlib import Path
from common import ROOT, WINDOW_WEEKS, BRAND_WEEKLY, COST, load_ref, load_json, read_csv, review_state, quality_share, cost

REF_DOC = Path.home() / '.claude' / 'tools' / 'md2office' / 'ref_portrait.docx'
OUT = ROOT / '奶粉公开投诉分拣_AI小场景案例_完整版.docx'

data = read_csv(ROOT / 'data' / 'complaints.csv')
ref_rows = load_ref()
ref = {r['id']: r for r in ref_rows}
ai = {r['id']: r for r in load_json('labels/claude_labels.json')}
base = {r['id']: r for r in load_json('labels/baseline_labels.json')}
base2 = {r['id']: r for r in load_json('labels/baseline_v2_labels.json')}
summ = load_json('outputs/eval_summary.json')
q1 = read_csv(ROOT / 'outputs' / 'sql_Q1_类别分布.csv')
q2 = read_csv(ROOT / 'outputs' / 'sql_Q2_重复出现的具体问题.csv')
q2b = {r['类型']: int(r['条数']) for r in read_csv(ROOT / 'outputs' / 'sql_Q2b_活动权益里的规则类问题.csv')}
q3 = read_csv(ROOT / 'outputs' / 'sql_Q3_优先人工核查清单.csv')
state = review_state(ref_rows)
n = len(data)
cat_of = lambda pred, i: pred[i]['category']

# ---------- 正文举例依赖的事实：不成立就停 ----------
o_ids = [i for i in ref if ref[i]['ref_category'] == '订单发货']
o_to_a = [i for i in o_ids if base[i]['category'] == '活动权益']
base_wrong = {i for i in ref if base[i]['category'] != ref[i]['ref_category']}
v2_wrong = {i for i in ref if base2[i]['category'] != ref[i]['ref_category']}
v2_fixed = base_wrong - v2_wrong
v2_broken = v2_wrong - base_wrong
checks = [
    ('第五节「规则错在哪」第 1 条：百亿补贴超时不发货（17400304643）应为订单发货、被规则分进活动',
     '17400304643' in o_to_a),
    ('第五节「规则错在哪」第 2 条：赠品滑板车（17401788734）不是质量安全、却被规则判成质量安全',
     ref['17401788734']['ref_category'] != '质量安全' and base['17401788734']['category'] == '质量安全'),
    ('第五节「规则错在哪」第 3 条与附录 A：调换顺序后新错的应恰好是「赠品不发货」「拒发赠品」两条（17401080047、17400293346）',
     v2_broken == {'17401080047', '17400293346'}),
    ('开头摘要、第五节与附录 A：「规则在质量安全上 0 漏判」及据此的设计取舍', not summ['关键词基线']['质量安全_漏判']),
    ('开头摘要「AI 能区分词义重叠」与第五节「AI 正确的例子」：滑板车与百亿补贴两条 AI 与参考一致',
     all(ai[i]['category'] == ref[i]['ref_category'] for i in ('17401788734', '17400304643'))),
    ('第五节「难判断的例子」：17402080517 参考标为不需复核、AI 标为需复核',
     ref['17402080517']['ref_needs_review'] == '0' and ai['17402080517']['needs_review']),
]
weekly = n / WINDOW_WEEKS
q_share = quality_share(ref_rows)
c_series = cost(weekly, q_share)
checks.append(('开头摘要、第六节结论与附录 A：「按现在的量净价值是负的」', c_series['net'] < 0))
broken = [name for name, ok in checks if not ok]
if broken:
    sys.exit('以下段落依赖的事实已因标签变化而不成立，需先改写 src/case_template.txt：\n- ' + '\n- '.join(broken))

# ---------- 计算填充值 ----------
def fmt(x, d=1):
    return f'{x:.{d}f}'.replace('-', '−')

cat_order = ['质量安全', '活动权益', '订单发货', '其他', '信息不足']
q1d = {r['类别']: r for r in q1}
q1_sentence = '，'.join(f"{c} {q1d[c]['条数']} 条" for c in cat_order if c in q1d)
replied_sentence = '，'.join(f"{c} {q1d[c]['列表显示已回复']}/{q1d[c]['条数']}" for c in ['活动权益', '质量安全'] if c in q1d)

DESC = {
    '异物/虫': '涉及{ch}；单号 17401992912 写到连续两罐出现异物',
    '集罐不累计': '线上与线下不累计、异地不累计、翻拍不计、扫码后显示超出活动范围',
    '订单异常拒发': '同一地址买两箱、分单购买、地址异常被拒发',
    '赠品问题': '承诺的赠品不发，或赠品本身有缺陷',
    '扫码手机号/账号': '扫码手机号须与报名手机号一致，但事先未告知',
    '活动过期/规则未告知': '活动到期或限制条件在购买时未告知',
    '空罐丢失锁权益': '空罐丢弃后无法扫内码，剩余补贴被锁',
}
shown = [r for r in q2 if int(r['独立投诉数']) >= 3]
rest = [r for r in q2 if int(r['独立投诉数']) < 3]
q2_rows = []
for r in shown:
    ch = '、'.join(c for c in dict.fromkeys(r['文本提及渠道'].split(',')) if c != '未说明')
    q2_rows.append(f"| {r['子问题'].replace('/', ' / ')} | {r['独立投诉数']} | {DESC.get(r['子问题'], '').format(ch=ch)} |")
q2_more = (f"另有 {len(rest)} 个子问题各出现 2 次（{'、'.join(r['子问题'] for r in rest)}），见 Excel“SQL结果”表。\n\n" if rest else '')

q3_top = '；'.join(f"{r['投诉单号']}（{r['子问题']}：{r['排序理由'].rstrip('；').replace('；', '、')}）" for r in q3[:4])

label = {'AI（Claude）': 'AI（Claude）', '关键词基线': '关键词规则', '关键词基线v2（仅调换顺序）': '规则（只调换顺序）'}
eval_rows = []
for key in ['关键词基线', '关键词基线v2（仅调换顺序）', 'AI（Claude）']:
    s = summ[key]
    basis = f"{summ['AI 依据片段为原文逐字子串']} 条依据可在原文逐字找到" if key.startswith('AI') else '只有命中的关键词'
    eval_rows.append(f"| {label[key]} | {s['类别一致']} | {len(s['质量安全_漏判'])} | {len(s['质量安全_误判'])} | {basis} |")

ai_wrong = summ['AI（Claude）']['类别不一致']
if ai_wrong:
    lines = [f"{i}：参考为{ref[i]['ref_category']}，AI 判为{ai[i]['category']}，依据“{ai[i]['evidence']}”" for i in ai_wrong]
    ai_disagree_block = f"**AI 与参考标签不一致的 {len(ai_wrong)} 条：** " + '；'.join(lines) + '。\n\n'
else:
    ai_disagree_block = ''

sem = {i for i in (base_wrong | v2_wrong) if ai[i]['category'] == ref[i]['ref_category']}
kw = list(dict.fromkeys(base[i]['matched_keyword'] for i in o_to_a))

todo_label = {
    'none': f'请熟悉业务的人逐条复核 {n} 条参考标签，再重算一致率。',
    'partial': f"已复核 {state['k']}/{n} 条，剩余 {n - state['k']} 条复核完后重算一致率。",
    'all': '已由作者逐条复核；下一步请熟悉业务的同事不看原标签独立标注一遍，检验标注本身是否一致。',
}[state['mode']]
appx_label = {
    'none': '参考标签也是 Claude 辅助标注的，所以我用一致率找错误类型，下一步是人工复核。',
    'partial': f"参考标签由 Claude 辅助起草，已人工复核 {state['k']}/{n} 条，所以我用一致率找错误类型。",
    'all': '参考标签由 Claude 辅助起草、我逐条人工复核；复核时看得到原标签，所以我用一致率找错误类型。',
}[state['mode']]

ctx = {
    'n': n, 'n_trunc': sum(r['truncated'] == '1' for r in data), 'weekly_round': round(weekly),
    'review_short': state['short'], 'review_long': state['long'],
    'q1_sentence': q1_sentence, 'replied_sentence': replied_sentence,
    'q2_rows': '\n'.join(q2_rows), 'q2_more': q2_more,
    'act_n': q1d['活动权益']['条数'], 'rule_n': q2b.get('规则/系统限制', 0), 'promise_n': q2b.get('承诺未兑现（赠品/积分）', 0),
    'q3_top': q3_top, 'eval_rows': '\n'.join(eval_rows), 'ai_disagree_block': ai_disagree_block,
    'o_ref': len(o_ids), 'o_to_a': len(o_to_a), 'o_keywords': ''.join(f'“{k}”' for k in kw),
    'v2_fixed': len(v2_fixed), 'v2_broken': len(v2_broken), 'sem_n': len(sem),
    'yiwu_n': next(r['独立投诉数'] for r in q2 if r['子问题'] == '异物/虫'),
    'c_manual': COST['manual_min'], 'c_review': COST['review_min'], 'c_wage': COST['wage'],
    'c_model': COST['model_yuan'], 'c_maint': COST['maint_hours'],
    'q_frac': f"{sum(r['ref_category'] == '质量安全' for r in ref_rows)}/{n}",
    'weekly_1': fmt(weekly), 'net_series': fmt(c_series['net']),
    'brand_weekly': BRAND_WEEKLY, 'net_brand': fmt(cost(BRAND_WEEKLY, q_share)['net']),
    'breakeven': round(c_series['breakeven']),
    'net_50': fmt(cost(50, q_share)['net']), 'net_200': fmt(cost(200, q_share)['net']),
    'cost_conclusion': (f"按现在的公开投诉量，单独做不划算，用关键词规则加一个 Excel 模板就够了。"
                        f"只有扩展到电商差评或工单、每周量超过约 {round(c_series['breakeven'])} 条时，才值得试点。"),
    'todo_label': todo_label, 'appx_label': appx_label,
}

tpl = (ROOT / 'src' / 'case_template.txt').read_text(encoding='utf-8')
missing = sorted(set(re.findall(r'\{\{(\w+)\}\}', tpl)) - set(ctx))
if missing:
    sys.exit('模板里有未提供的占位符：' + '、'.join(missing))
filled = re.sub(r'\{\{(\w+)\}\}', lambda m: str(ctx[m.group(1)]), tpl)

# 两份输出：根目录为完整版（含附录 A 面试讲稿与附录 B 本机运行说明，不入仓库）；
# docs/ 为公开版（去掉附录 A、B，正文与附录 C 不变），仓库里只放公开版。
PUBLIC_OUT = ROOT / 'docs' / '奶粉公开投诉分拣_AI小场景案例.docx'
public = re.sub(r'\n# 附录 A：.*?(?=\n# 附录 C：)', '\n', filled, flags=re.S)
assert '附录 A' not in public and '附录 B' not in public and '# 附录 C' in public
PUBLIC_OUT.parent.mkdir(exist_ok=True)
for path, text in [(OUT, filled), (PUBLIC_OUT, public)]:
    subprocess.run(['pandoc', '-f', 'markdown', '-o', str(path), '--reference-doc', str(REF_DOC), '--resource-path', str(ROOT)],
                   input=text.encode('utf-8'), check=True, cwd=ROOT)
    print(f"写出：{path}（{state['short']}；AI 类别一致 {summ['AI（Claude）']['类别一致']}，规则 {summ['关键词基线']['类别一致']}）")
