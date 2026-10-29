# -*- coding: utf-8 -*-
"""脱敏：黑猫投诉原始采集件 → 公开版数据。
  输入  data/raw/heimao_xingfeifan_20261015.json   （原始件，不入仓库；见 .gitignore）
  输出  data/public/heimao_xingfeifan_20261015_public.json   （仓库里只放这一份，01_prepare.py 从它开始）
        data/public/anonymization_report.json              （每条规则替换了多少处、涉及哪些单号）
运行：python src/00_anonymize.py        原始件不存在时直接退出并提示；公开版已存在且内容相同时不改动文件
       python src/00_anonymize.py --check   只检查现有公开版是否仍含未脱敏片段，不读原始件（仓库里的人可以跑）

做了什么：
1. 字段白名单：只保留 id / date / status / title / excerpt / target / demand，其余键一律丢弃
   （原始件本就没有昵称、头像、用户 ID，白名单是为了换一份原始件也不会带进来）。
2. 文本内的标识符：
   - 平台已打星号的订单号、运单号、手机号片段（如 51274*********03426、139**********、260***-498************）→ ［编号已隐去］
   - 未打码的 11 位手机号 → ［手机号已隐去］
   - 连续 12 位以上的纯数字（订单号、证件号量级）→ ［编号已隐去］
   批次号（含字母，如 5F26QL202AI62）、金额、日期、罐数不受影响；投诉单号 id 是公开页面的 URL 编号，保留用于逐条核验。
3. 禁用键检查：输出里若出现 nick / avatar / uid / user / phone / mobile / author 之类的键名，脚本报错退出。
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw' / 'heimao_xingfeifan_20261015.json'
PUB_DIR = ROOT / 'data' / 'public'
PUB = PUB_DIR / 'heimao_xingfeifan_20261015_public.json'
REPORT = PUB_DIR / 'anonymization_report.json'

KEEP = ['id', 'date', 'status', 'title', 'excerpt', 'target', 'demand']
TEXT_FIELDS = ['title', 'excerpt', 'demand']
BANNED_KEYS = re.compile(r'nick|avatar|uid|user|phone|mobile|author|昵称|头像|手机', re.I)

# 顺序有意义：先处理带星号的片段，再处理裸号码
RULES = [
    ('platform_masked_identifier', re.compile(r'[0-9A-Za-z]*\*{2,}[0-9A-Za-z*\-]*'), '［编号已隐去］'),
    ('bare_mobile_number', re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)'), '［手机号已隐去］'),
    ('long_digit_run_12plus', re.compile(r'(?<!\d)\d{12,}(?!\d)'), '［编号已隐去］'),
]
# 只用于 --check：公开版里不应再出现这些形态
LEFTOVER = re.compile(r'\*{2,}|(?<!\d)1[3-9]\d{9}(?!\d)|(?<!\d)\d{12,}(?!\d)')


def scrub(text, counts, hit_ids, rid):
    for name, pat, repl in RULES:
        text, n = pat.subn(repl, text)
        if n:
            counts[name] = counts.get(name, 0) + n
            hit_ids.setdefault(name, set()).add(rid)
    return text


def check(pub_path):
    data = json.loads(pub_path.read_text(encoding='utf-8'))
    bad = []
    for r in data['rows']:
        extra = [k for k in r if k not in KEEP]
        banned = [k for k in r if BANNED_KEYS.search(k)]
        left = [m.group(0) for f in TEXT_FIELDS for m in LEFTOVER.finditer(r.get(f, ''))]
        if extra or banned or left:
            bad.append((r['id'], extra, banned, left))
    return bad


def main():
    if '--check' in sys.argv:
        if not PUB.exists():
            sys.exit(f'{PUB} 不存在，先运行 python src/00_anonymize.py')
        bad = check(PUB)
        if bad:
            sys.exit('公开版仍含未脱敏内容：\n' + '\n'.join(str(b) for b in bad))
        print(f'检查通过：{PUB} 只含白名单字段，文本里没有星号片段、裸手机号或 12 位以上纯数字。')
        return

    if not RAW.exists():
        sys.exit(f'原始件不存在：{RAW}\n仓库不含原始件；要复现分析请直接从 01_prepare.py 开始，它读取 {PUB.relative_to(ROOT)}。')
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    counts, hit_ids, dropped_keys = {}, {}, set()
    rows = []
    for r in raw['rows']:
        dropped_keys |= set(r) - set(KEEP)
        row = {k: r[k] for k in KEEP if k in r}
        for f in TEXT_FIELDS:
            if f in row:
                row[f] = scrub(row[f], counts, hit_ids, row['id'])
        rows.append(row)

    out = {k: raw[k] for k in ['source', 'page', 'collected_at', 'rows_all_loaded', 'filter', 'fields'] if k in raw}
    out['anonymized'] = {
        'script': 'src/00_anonymize.py',
        'kept_fields': KEEP,
        'rules': [name for name, _, _ in RULES],
        'note': '公开版：文本内平台已打码或可能标识个人的编号已替换为占位符；投诉单号 id 为黑猫投诉公开页面的 URL 编号，保留用于核验。',
    }
    out['rows'] = rows

    bad = [(r['id'], [k for k in r if BANNED_KEYS.search(k)]) for r in rows if any(BANNED_KEYS.search(k) for k in r)]
    if bad:
        sys.exit('输出中出现禁用键，已中止：' + str(bad))

    PUB_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, ensure_ascii=False, indent=1) + '\n'
    if PUB.exists() and PUB.read_text(encoding='utf-8') == text:
        print(f'公开版未变化：{PUB}')
    else:
        PUB.write_text(text, encoding='utf-8')
        print(f'写出：{PUB}（{len(rows)} 条）')

    report = {
        'raw_rows': len(raw['rows']), 'public_rows': len(rows),
        'dropped_keys': sorted(dropped_keys),
        'replacements': {k: {'count': counts[k], 'complaint_ids': sorted(hit_ids[k])} for k in counts},
        'leftover_check': 'passed' if not check(PUB) else 'FAILED',
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('替换统计：', json.dumps(report['replacements'], ensure_ascii=False))
    print('丢弃的字段：', report['dropped_keys'] or '无')
    if report['leftover_check'] != 'passed':
        sys.exit('脱敏后自检未通过，请查看 ' + str(REPORT))
    print('写出：', REPORT)


if __name__ == '__main__':
    main()
