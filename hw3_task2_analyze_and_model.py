# -*- coding: utf-8 -*-
"""
线性相关分析与框架频次统计
随机森林建立模型，分析影响模型下载量的核心因素
"""

import csv, os
from scipy.stats import pearsonr
import numpy as np
from sklearn.ensemble import RandomForestRegressor
BASE = os.path.dirname(os.path.abspath(__file__))
FILES = [
    ("cleaned_hf_text_generation_top100.csv", "文本生成"),
    ("cleaned_hf_image_classification_top100.csv", "图像分类"),
    ("cleaned_hf_text_to_image_top100.csv", "文本生成图像"),
]
print("=" * 70)
print("一、各方向下载量与点赞数的线性相关分析")
print("=" * 70)
for fname, label in FILES:
    path = os.path.join(BASE, fname)
    downloads, likes = [], []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            d = int(row["累计下载量"])
            l = int(row["社区点赞数"])
            downloads.append(d)
            likes.append(l)

    r, p = pearsonr(downloads, likes)
    print(f"\n  [{label}]")
    print(f"    样本量 n         = {len(downloads)}")
    print(f"    下载量均值        = {sum(downloads)/len(downloads):,.0f}")
    print(f"    点赞数均值        = {sum(likes)/len(likes):.1f}")
    print(f"    相关系数        = {r:.6f}")
    print(f"    p-value          = {p:.6e}")
    print(f"    统计学显著性      = {'显著 (p<0.05)' if p < 0.05 else '不显著 (p>=0.05)'}")

print("\n" + "=" * 70)
print("二、各方向支持框架出现频次与占比")
print("=" * 70)
for fname, label in FILES:
    path = os.path.join(BASE, fname)
    freq = {}
    total = 0
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            for fw in row["支持框架"].split(", "):
                fw = fw.strip()
                if fw:
                    freq[fw] = freq.get(fw, 0) + 1
                    total += 1

    print(f"\n  [{label}]")
    print(f"  {'框架':25s} {'出现次数':>8s} {'占比':>8s}")
    print(f"  {'-'*25} {'-'*8} {'-'*8}")
    for fw, cnt in sorted(freq.items(), key=lambda x: -x[1]):
        print(f"  {fw:25s} {cnt:8d} {cnt/total*100:7.2f}%")
print("\n分析完成")

print("=" * 70)
print("三、随机森林建模分析特征重要性")
print("=" * 70)
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, "cleaned_hf_text_generation_top100.csv")
RANDOM_STATE = 42
rows = []
with open(DATA_FILE, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        rows.append(row)
print("样本量: " + str(len(rows)))
print()

#开源协议保留出现 >= 3 次
lic_counts = {}
for r in rows:
    lic_counts[r["开源协议"]] = lic_counts.get(r["开源协议"], 0) + 1
kept_licenses = sorted([lic for lic in lic_counts if lic_counts[lic] >= 3])
dropped_lic = [lic for lic in lic_counts if lic_counts[lic] < 3]
if dropped_lic:
    print("剔除的低频协议: " + str(dropped_lic))
for r in rows:
    for lic in kept_licenses:
        r["协议_" + lic] = 1 if r["开源协议"] == lic else 0

#支持框架保留出现 >= 3 次
fw_counts = {}
for r in rows:
    for fw in r["支持框架"].split(", "):
        fw = fw.strip()
        if fw:
            fw_counts[fw] = fw_counts.get(fw, 0) + 1
kept_frameworks = sorted([fw for fw in fw_counts if fw_counts[fw] >= 3])
dropped_fw = [fw for fw in fw_counts if fw_counts[fw] < 3]
if dropped_fw:
    print("剔除的低频框架: " + str(dropped_fw))
print()
for r in rows:
    fws = set(fw.strip() for fw in r["支持框架"].split(", ") if fw.strip())
    for fw in kept_frameworks:
        r["框架_" + fw] = 1 if fw in fws else 0

#参数规模填补
param_values = []
for r in rows:
    vs = r["参数量(数值)"]
    u = r["参数量(单位)"]
    if vs != "" and u != "":
        v = float(vs)
        param_values.append(v * 1000 if u == "B" else v)
param_median = float(np.median(param_values))
print("参数中位数: " + str(param_median) + "M")
for r in rows:
    vs = r["参数量(数值)"]
    u = r["参数量(单位)"]
    if vs != "" and u != "":
        v = float(vs)
        r["参数量_M"] = v * 1000 if u == "B" else v
        r["参数缺失"] = 0
    else:
        r["参数量_M"] = param_median
        r["参数缺失"] = 1

#关联论文
for r in rows:
    r["有关联论文"] = 1 if r["关联论文(ArXiv)"] != "" else 0

#特征矩阵
feature_cols = []
feature_cols += ["协议_" + lic for lic in kept_licenses]
feature_cols += ["框架_" + fw for fw in kept_frameworks]
feature_cols += ["参数量_M", "参数缺失", "有关联论文"]

print("保留特征数: " + str(len(feature_cols)))
print("特征: " + str(feature_cols))
print()

X = np.array([[r[col] for col in feature_cols] for r in rows], dtype=float)
y = np.array([int(r["累计下载量"]) for r in rows], dtype=float)
print()

rf = RandomForestRegressor(n_estimators=200, random_state=RANDOM_STATE)
rf.fit(X, y)

importances = rf.feature_importances_
sorted_idx = np.argsort(importances)[::-1]

print("特征重要性排序:")
print("  {:<35s} {:>10s}".format("特征", "重要性得分"))
print("  " + "-"*35 + " " + "-"*10)
for idx in sorted_idx:
    print("  {:<35s} {:>10.6f}".format(feature_cols[idx], importances[idx]))

print()
print("建模完成")
