# -*- coding: utf-8 -*-
import csv, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output")
SRC = os.path.join(BASE, "cleaned_ai_jobs.csv")
RANDOM_STATE = 42

rows = []
with open(SRC, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f): rows.append(r)
print("Read " + str(len(rows)) + " rows\n")

#可视化
print("========== 可视化 ==========")
#城市分布
city_counts = collections.Counter(r["city"] for r in rows if r["city"])
top_cities = city_counts.most_common(15)
cities, counts = zip(*top_cities)
fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(range(len(cities)), counts, color="#4A90D9")
ax.set_yticks(range(len(cities))); ax.set_yticklabels(cities)
ax.set_xlabel("岗位数量"); ax.set_title("AI 岗位城市分布 Top 15")
for bar, v in zip(bars, counts):
    ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, str(v), va="center", fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_city_dist.png"), dpi=150); plt.close()
print("fig_city_dist.png已保存")

#学历要求分布
edu_labels = {0: "学历不限", 1: "大专", 2: "本科", 3: "硕士", 4: "博士"}
edu_counts = collections.Counter(r["education_code"] for r in rows)
labels = [edu_labels.get(int(k), k) for k in sorted(edu_counts.keys(), key=int)]
vals = [edu_counts[k] for k in sorted(edu_counts.keys(), key=int)]
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(labels, vals, color=["#999999","#5BA3E6","#4A90D9","#3A7BD5","#2E6DB4"][:len(labels)])
ax.set_ylabel("岗位数量"); ax.set_title("AI 岗位学历要求分布")
for bar, v in zip(bars, vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, str(v), ha="center", fontsize=10)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_edu_dist.png"), dpi=150); plt.close()
print("fig_edu_dist.png已保存")

#工作经验要求分布
exp_labels = {0: "经验不限/应届", 2: "1-3年", 4: "3-5年", 7: "5-10年", 12: "10年以上"}
exp_counts = collections.Counter(r["experience_years"] for r in rows)
labels_exp = [exp_labels.get(int(k), k) for k in sorted(exp_counts.keys(), key=int)]
vals_exp = [exp_counts[k] for k in sorted(exp_counts.keys(), key=int)]
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(labels_exp, vals_exp, color="#E8833A")
ax.set_ylabel("岗位数量"); ax.set_title("AI 岗位经验要求分布")
for bar, v in zip(bars, vals_exp):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, str(v), ha="center", fontsize=10)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_exp_dist.png"), dpi=150); plt.close()
print("fig_exp_dist.png已保存")

#薪资箱线图
SALARY_CAP = 80000
job_types = collections.Counter(r["job_type"] for r in rows)
valid_types = [jt for jt, n in job_types.most_common() if n >= 3]
data_by_type = {jt: [] for jt in valid_types}
for r in rows:
    jt = r["job_type"]
    if jt in data_by_type:
        data_by_type[jt].append(min(float(r["salary_avg"]), SALARY_CAP))
fig, ax = plt.subplots(figsize=(10, 6))
box_data = [data_by_type[jt] for jt in valid_types]
bp = ax.boxplot(box_data, positions=range(len(valid_types)), widths=0.6, patch_artist=True, medianprops={"color":"black","linewidth":1.5})
for patch, c in zip(bp["boxes"], plt.cm.Set2.colors[:len(valid_types)]):
    patch.set_facecolor(c)
ax.set_xticks(range(len(valid_types))); ax.set_xticklabels(valid_types, rotation=30, ha="right", fontsize=9)
ax.set_ylabel("月薪 (元)"); ax.set_ylim(0, 80000); ax.set_title("各岗位类型薪资分布（上限 80000 元）"); ax.grid(axis="y", alpha=0.3)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_salary_dist.png"), dpi=150); plt.close()
print("fig_salary_dist.png 已保存")

#高频技能
skill_counter = collections.Counter()
for r in rows:
    if r["skills"]:
        for s in r["skills"].split(","):
            s = s.strip()
            if s: skill_counter[s] += 1
print("\n总技能数:", len(skill_counter))
top15 = skill_counter.most_common(15)
if top15:
    names, counts = zip(*top15)
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(range(len(names)), counts, color="#E8833A")
    ax.set_yticks(range(len(names))); ax.set_yticklabels(names)
    ax.set_xlabel("出现次数"); ax.set_title("AI 岗位热门技能 Top 15")
    for bar, v in zip(bars, counts):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, str(v), va="center", fontsize=9)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_skills_top.png"), dpi=150); plt.close()
    print("fig_skills_top.png已保存")

#薪资对比
print("\n=== 各岗位类型薪资对比 ===")
print("{0:20s} {1:>5s} {2:>10s} {3:>10s} {4:>10s}".format("岗位类型","数量","平均月薪","最低月薪","最高月薪"))
print("-" * 55)
salary_by_jt = collections.defaultdict(list)
for r in rows: salary_by_jt[r["job_type"]].append(float(r["salary_avg"]))
for jt in sorted(salary_by_jt.keys(), key=lambda jt: np.mean(salary_by_jt[jt]), reverse=True):
    vals = salary_by_jt[jt]
    print("{0:20s} {1:5d} {2:10d} {3:10d} {4:10d}".format(jt, len(vals), int(np.mean(vals)), int(min(vals)), int(max(vals))))

#学历对比
print("\n=== 各岗位类型学历要求对比 ===")
print("{0:20s} {1:>8s} {2:>5s} {3:>5s} {4:>5s} {5:>5s}".format("岗位类型","平均学历","大专","本科","硕士","博士"))
print("-" * 50)
edu_by_jt = collections.defaultdict(list)
for r in rows: edu_by_jt[r["job_type"]].append(int(r["education_code"]))
for jt in sorted(edu_by_jt.keys(), key=lambda jt: -np.mean(edu_by_jt[jt])):
    vals = edu_by_jt[jt]; avg = np.mean(vals); cd = collections.Counter(vals)
    print("{0:20s} {1:5.2f} ({2:4s}) {3:5d} {4:5d} {5:5d} {6:5d}".format(jt, avg, edu_labels.get(round(avg),""), cd.get(1,0), cd.get(2,0), cd.get(3,0), cd.get(4,0)))

#薪资预测

print("\n========== 薪资模型 ==========")

edu = np.array([[float(r["education_code"])] for r in rows], dtype=float)
exp = np.array([[float(r["experience_years"])] for r in rows], dtype=float)
hot = np.array([[float(r["is_hot_city"])] for r in rows], dtype=float)
job_types_list = sorted(set(r["job_type"] for r in rows))
jt_map = {jt: i for i, jt in enumerate(job_types_list)}
jt_matrix = np.zeros((len(rows), len(job_types_list)), dtype=float)
for i, r in enumerate(rows): jt_matrix[i, jt_map[r["job_type"]]] = 1.0

y = np.array([float(r["salary_avg"]) for r in rows], dtype=float)
print("薪资范围: {0:.0f} - {1:.0f}, 平均薪资={2:.0f}".format(y.min(), y.max(), y.mean()))

X = np.column_stack([edu, exp, hot, jt_matrix])
feature_names = ["教育水平","经验年限","热门城市"] + ["岗位_" + jt for jt in job_types_list]
print("特征矩阵:", X.shape)

model = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=RANDOM_STATE)
model.fit(X, y)
scores = cross_val_score(model, X, y, cv=5, scoring="r2")
#print("\n5折 CV R^2:", scores)
print("训练 R^2: {0:.4f}".format(model.score(X, y)))
imp = model.feature_importances_
idx = np.argsort(imp)[::-1]
print("\n特征重要性:")
for i in idx:
    print("  {0:20s} {1:.4f}".format(feature_names[i], imp[i]))
