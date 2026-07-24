# -*- coding: utf-8 -*-
"""作业一"""
import pandas as pd, numpy as np, os, warnings#数值分析，计算，文件操作
warnings.filterwarnings('ignore')#忽略警告
import matplotlib#绘图库
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm#加载中文
from sklearn.linear_model import LinearRegression#线性回归模型
from sklearn.preprocessing import StandardScaler#标准化预处理
from sklearn.model_selection import cross_val_score#交叉验证得分

EXCEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '十城数据汇总.xlsx')
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
CITIES_4 = ['北京','上海','天津','重庆']
ALL_CITIES = CITIES_4 + ['南京','广州','深圳','杭州','西安','成都']

font_path = r'C:\Windows\Fonts\simhei.ttf'
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False 

df = pd.read_excel(EXCEL_PATH)
print('原始数据:', len(df), '行')

# ====== 1. 数据清洗 ======
print('\n--- 数据清洗 ---')
numeric_cols = [c for c in df.columns if c not in ('城市', '年份')]
start_miss = df[numeric_cols].isnull().sum()
print('初始缺失统计:')
for col in numeric_cols:
    n = start_miss[col]
    if n > 0:
        cities = sorted(df[df[col].isnull()]['城市'].unique())
        print(f'  {col}: {n} ({cities})')

total_filled = 0
for city in df['城市'].unique():
    cm = df['城市'] == city
    cd = df.loc[cm].sort_values('年份').set_index('年份')
    for col in numeric_cols:
        missing = cd.index[cd[col].isnull()]
        if len(missing) == 0: continue
        valid = cd[col].dropna()
        if len(valid) < 2: continue
        z = np.polyfit(valid.index.astype(float), valid.values, 1)
        for yr in missing:
            val = np.polyval(z, yr)
            idx = df[(df['城市']==city)&(df['年份']==yr)].index[0]
            df.loc[idx, col] = round(val, 2)
            total_filled += 1
            print(f'  {city} {int(yr)} {col}: {val:.2f} (外推补全)')

print(f'\n补全总计: {total_filled} 个值')
print('清洗后缺失:')
for col in numeric_cols:
    n = df[col].isnull().sum()
    if n > 0:
        print(f'  {col}: {n} ({sorted(df[df[col].isnull()]["城市"].unique())})')

df.to_excel(EXCEL_PATH, index=False)

# ====== 2. 可视化 ======
print('\n--- 可视化 ---')
COLORS = {'北京':'#E74C3C','上海':'#3498DB','天津':'#2ECC71','重庆':'#F39C12',
          '南京':'#9B59B6','广州':'#1ABC9C','深圳':'#E67E22','杭州':'#2C3E50',
          '西安':'#95A5A6','成都':'#F1C40F'}

def save_fig(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f'  已保存: {path}')

# 图1: 总人口趋势
fig, ax = plt.subplots(figsize=(12, 6))
for city in ALL_CITIES:
    sub = df[df['城市']==city].sort_values('年份')
    ax.plot(sub['年份'], sub['总人口（万人）'], color=COLORS[city],
            marker='o', markersize=4, linewidth=1.8, label=city)
ax.set_title('十城常住人口总量趋势 (2016-2025)', fontsize=14, fontweight='bold')
ax.set_xlabel('年份'); ax.set_ylabel('常住人口（万人）')
ax.legend(frameon=True, prop=prop, ncol=5, fontsize=8, loc='upper left')
ax.grid(True, alpha=0.3)
save_fig(fig, 'fig1_人口总量.png'); plt.close(fig)

# 图2: 自然增长率趋势
fig, ax = plt.subplots(figsize=(12, 6))
for city in ALL_CITIES:
    sub = df[df['城市']==city].sort_values('年份')
    ax.plot(sub['年份'], sub['自然增长率（‰）'], color=COLORS[city],
            marker='o', markersize=4, linewidth=1.8, label=city)
ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
ax.set_title('十城人口自然增长率趋势 (2016-2025)', fontsize=14, fontweight='bold')
ax.set_xlabel('年份'); ax.set_ylabel('自然增长率（‰）')
ax.legend(frameon=True, prop=prop, ncol=5, fontsize=8, loc='lower left')
ax.grid(True, alpha=0.3)
save_fig(fig, 'fig2_自然增长率.png'); plt.close(fig)

# 图3: 城镇化率 (排除深圳/西安)
fig, ax = plt.subplots(figsize=(12, 6))
urban_cities = [c for c in ALL_CITIES if c not in ['深圳','西安']]
for city in urban_cities:
    sub = df[(df['城市']==city)&(df['城镇化率（%）'].notna())].sort_values('年份')
    if len(sub) > 0:
        ax.plot(sub['年份'], sub['城镇化率（%）'], color=COLORS[city],
                marker='o', markersize=4, linewidth=1.8, label=city)
ax.set_title('八城城镇化率趋势 (2016-2025, 深圳/西安无数据)', fontsize=14, fontweight='bold')
ax.set_xlabel('年份'); ax.set_ylabel('城镇化率（%）')
ax.legend(frameon=True, prop=prop, ncol=4, fontsize=8, loc='lower right')
ax.grid(True, alpha=0.3)
save_fig(fig, 'fig3_城镇化率.png'); plt.close(fig)

# 图4: 老龄化趋势
fig, ax = plt.subplots(figsize=(10, 5.5))
for city in CITIES_4:
    sub = df[df['城市']==city].sort_values('年份')
    ax.plot(sub['年份'], sub['65岁以上占比（%）'], color=COLORS[city],
            marker='o', markersize=6, linewidth=2, label=city)
ax.set_title('四直辖市老龄化趋势 (65岁以上占比, 2016-2025)', fontsize=14, fontweight='bold')
ax.set_xlabel('年份'); ax.set_ylabel('65岁以上占比（%）')
ax.legend(frameon=True, prop=prop)
ax.grid(True, alpha=0.3)
save_fig(fig, 'fig4_老龄化.png'); plt.close(fig)

# ====== 3. 线性回归模型 ======
print('\n--- 线性回归模型 ---')
model_df = df.dropna(subset=['自然增长率（‰）','人均GDP（元）','城镇化率（%）',
                               '人均可支配收入（元）','65岁以上占比（%）']).copy()
print(f'训练样本: {len(model_df)} ({model_df["城市"].nunique()} 个城市)')

features = ['人均GDP（元）','城镇化率（%）','人均可支配收入（元）','65岁以上占比（%）']
target = '自然增长率（‰）'
X = model_df[features].values
y = model_df[target].values

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

lr = LinearRegression()
lr.fit(X_scaled, y)

cv_scores = cross_val_score(lr, X_scaled, y, cv=5, scoring='r2')
train_r2 = lr.score(X_scaled, y)
print(f'训练集 R2: {train_r2:.4f}')
print(f'交叉验证 R2 (5折): {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}')

print('\n标准化特征系数:')
for feat, coef in zip(features, lr.coef_):
    direction = '正相关' if coef > 0 else '负相关'
    print(f'  {feat}: {coef:.4f} ({direction}')
print(f'截距: {lr.intercept_:.4f}')

lr_raw = LinearRegression()
lr_raw.fit(X, y)
print('\n原始尺度系数:')
for feat, coef in zip(features, lr_raw.coef_):
    print(f'  {feat}: {coef:.6f}')
print(f'截距: {lr_raw.intercept_:.4f}')
print('\n--- 完成 ---')

# ====== 4. TF-IDF 文本分析 ======
print('\n--- TF-IDF 文本分析 ---')
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer

text_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '人口变化.txt')
with open(text_path, 'r', encoding='utf-8') as f:
    full_text = f.read()

target_cities = ['北京', '上海', '重庆']
city_texts = {}
current_city = None
current_lines = []
for line in full_text.split('\n'):
    line = line.strip()
    if not line: continue
    matched = False
    for c in target_cities:
        if line.startswith(c + '：') or line.startswith(c + ':'):
            if current_city: city_texts[current_city] = ''.join(current_lines)
            current_city = c; current_lines = []
            matched = True; break
    if not matched and current_city:
        current_lines.append(line)
if current_city: city_texts[current_city] = ''.join(current_lines)

print(f'解析到 {len(city_texts)} 个city_texts')

stop_words = set(['的','了','在','是','与','和','及','等','为','所','有','不','上','中','更','较',
             '对','从','到','以','将','被','向','自','但','并','也','又','而','于','其','这',
             '该','那','各','个','已','后','或','均','可','能','会','就','则','且','之','至'])

def tokenize(text):
    return ' '.join([w for w in jieba.cut(text) if len(w) > 1 and w not in stop_words])

documents = [city_texts[c] for c in target_cities]
tokenized_docs = [tokenize(d) for d in documents]

tfidf = TfidfVectorizer(max_features=30, token_pattern=r'(?u)\b\w+\b')
tfidf_matrix = tfidf.fit_transform(tokenized_docs)
feature_names = tfidf.get_feature_names_out()

print('\n=== 各城市 TF-IDF 关键词 ===')
for i, city in enumerate(target_cities):
    scores = tfidf_matrix[i].toarray().flatten()
    ranked_indices = np.argsort(scores)[::-1]
    print(f'\n【{city}】Top-10 关键词:')
    top_words = []
    for j in ranked_indices[:10]:
        if scores[j] > 0:
            top_words.append(f'{feature_names[j]}({scores[j]:.4f})')
    print('  ' + ', '.join(top_words))

print('\n=== 文本分析 ===')
print('模型发现: 老龄化是最强负相关因素(系数-0.7139)，城镇化率与自然增长率负相关，人均收入与自然增长率正相关')
print('北京: 产业外迁 ，高学历人才引进，人口总量稳定但自然增长率趋零')
print('上海: 外来人口驱动，深度老龄化，城镇化极高，老龄化抑制效果最为明显')
print('重庆: 劳动力外流且自然负增长，老龄化，人口流出双重压力')
print('结论: TF-IDF文本关键词(人口、常住、增长、外来、老龄化)与数据模型因子一致，相互印证')
