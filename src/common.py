# -*- coding: utf-8 -*-
"""各脚本共用：读标签、按实际复核状态生成说明文字、成本公式。
所有随复核结果变化的数字和措辞都从这里取，不在各脚本里写死。"""
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW_WEEKS = 13          # 样本窗口 2026-07-15 至 2026-10-15，按 13 周计
BRAND_WEEKLY = round(160 / 14, 1)   # 黑猫投诉该商家页全部品牌：160 条 / 14 周（2026-07-09 至 10-15，采集时实测）

# 成本假设（Excel「成本测算」表的黄色格使用同一组默认值）
COST = {'manual_min': 4, 'review_min': 1.5, 'wage': 60, 'model_yuan': 0.01, 'maint_hours': 2, 'build_days': 3}


def read_csv(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))


def load_ref():
    return read_csv(ROOT / 'labels' / 'reference_labels.csv')


def load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def review_state(ref):
    """按 label_status 的实际取值给出复核状态与三种长度的说明文字。"""
    n = len(ref)
    k = sum(r['label_status'] == '已人工复核' for r in ref)
    if k == 0:
        mode, short = 'none', '参考标签待人工复核'
        long = (f'一致率用来定位错误类型：参考标签由作者借助 Claude 标注、尚待人工复核，与 AI 同源，AI 的一致率会偏高；'
                f'{n} 条样本适合找出错误模式，不足以估计总体准确率。')
    elif k < n:
        mode, short = 'partial', f'参考标签 {k}/{n} 条已人工复核，其余待复核'
        long = (f'一致率用来定位错误类型：参考标签由作者借助 Claude 起草，已人工复核 {k}/{n} 条，未复核部分与 AI 同源，'
                f'AI 的一致率会偏高；{n} 条样本适合找出错误模式，不足以估计总体准确率。')
    else:
        mode, short = 'all', '参考标签已逐条人工复核'
        long = (f'一致率用来定位错误类型：参考标签由作者借助 Claude 起草后逐条人工复核，复核时看得到原标签、看不到 AI 与规则结果，'
                f'属于非独立标注，AI 的一致率仍可能偏高；{n} 条样本适合找出错误模式，不足以估计总体准确率。')
    return {'n': n, 'k': k, 'mode': mode, 'short': short, 'long': long}


def quality_share(ref):
    return sum(r['ref_category'] == '质量安全' for r in ref) / len(ref)


def cost(weekly, q_share, c=COST):
    """与 Excel 公式一致：只在非质量安全条目上节省；维护按每月 4.33 周折算。"""
    per_item = (1 - q_share) * (c['manual_min'] - c['review_min']) / 60 * c['wage']
    maint_week = c['maint_hours'] * c['wage'] / 4.33
    net = weekly * (per_item - c['model_yuan']) - maint_week
    breakeven = maint_week / (per_item - c['model_yuan'])
    return {'per_item': per_item, 'maint_week': maint_week, 'net': net, 'breakeven': breakeven}
