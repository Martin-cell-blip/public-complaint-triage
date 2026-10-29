-- 飞鹤星飞帆系列 · 黑猫投诉公开样本（2026-07-15 至 2026-10-15，41 条）分析查询
-- 表：complaints（01_prepare.py 生成）、ref（labels/reference_labels.csv，由 03_run_sql.py 载入）
-- 口径提醒：这是公开投诉样本，占比只描述样本结构，不代表整体投诉率；参考标签的复核状态以 reference_labels.csv 的 label_status 为准。
-- 每段以「-- @名称」开头，03_run_sql.py 按段执行并导出。

-- @Q1_类别分布
SELECT r.ref_category                                   AS 类别,
       COUNT(*)                                         AS 条数,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM complaints), 1) AS 样本占比_pct,
       SUM(c.status = '已回复')                          AS 列表显示已回复,
       SUM(c.health_mention)                            AS 提到健康症状
FROM complaints c JOIN ref r USING (id)
GROUP BY r.ref_category
ORDER BY 条数 DESC;

-- @Q1b_按月与类别
SELECT substr(c.date, 1, 7) AS 月份, r.ref_category AS 类别, COUNT(*) AS 条数
FROM complaints c JOIN ref r USING (id)
GROUP BY 月份, 类别
ORDER BY 月份, 条数 DESC;

-- @Q2_重复出现的具体问题
-- 「重复」= 同一子问题出现在 ≥2 条不同投诉单号里；同一投诉人多次投诉无法识别（昵称未保存），这里按单号计
SELECT r.subtag                         AS 子问题,
       r.ref_category                   AS 类别,
       COUNT(DISTINCT c.id)             AS 独立投诉数,
       MIN(c.date)                      AS 最早,
       MAX(c.date)                      AS 最近,
       GROUP_CONCAT(DISTINCT c.channel_mentioned) AS 文本提及渠道
FROM complaints c JOIN ref r USING (id)
GROUP BY r.subtag, r.ref_category
HAVING COUNT(DISTINCT c.id) >= 2
ORDER BY 独立投诉数 DESC;

-- @Q2b_活动权益里的规则类问题
-- 集罐/扫码/空罐/账号 这四类都是「规则没讲清或系统限制」而不是「承诺没兑现」，单列出来给活动运营
SELECT CASE WHEN r.subtag IN ('集罐不累计', '空罐丢失锁权益', '扫码手机号/账号', '活动过期/规则未告知')
            THEN '规则/系统限制' ELSE '承诺未兑现（赠品/积分）' END AS 类型,
       COUNT(*) AS 条数
FROM complaints c JOIN ref r USING (id)
WHERE r.ref_category = '活动权益'
GROUP BY 类型;

-- @Q3_优先人工核查清单
-- 只排质量安全与写到健康症状的记录；分数只用于排序，不是风险评估
SELECT c.id                                   AS 投诉单号,
       c.date                                 AS 日期,
       r.ref_category                         AS 类别,
       r.subtag                               AS 子问题,
       c.health_mention * 3
       + (c.batch_no <> '') * 2
       + (c.text LIKE '%连续%' OR c.text LIKE '%两罐%' OR c.text LIKE '%三次%' OR c.text LIKE '%多次%') * 2
       + (c.status = '未回复')                AS 排序分,
       TRIM(
         CASE WHEN c.health_mention = 1 THEN '写到食用后症状；' ELSE '' END ||
         CASE WHEN c.batch_no <> '' THEN '有批次号可追溯：' || c.batch_no || '；' ELSE '' END ||
         CASE WHEN (c.text LIKE '%连续%' OR c.text LIKE '%两罐%' OR c.text LIKE '%三次%' OR c.text LIKE '%多次%')
              THEN '写到多罐/多次；' ELSE '' END ||
         CASE WHEN c.status = '未回复' THEN '列表显示未回复；' ELSE '' END
       )                                      AS 排序理由,
       c.url                                  AS 原文链接
FROM complaints c JOIN ref r USING (id)
WHERE r.ref_category = '质量安全' OR c.health_mention = 1
ORDER BY 排序分 DESC, c.date DESC;
