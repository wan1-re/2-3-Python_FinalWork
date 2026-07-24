# -*- coding: utf-8 -*-
"""
作业二：B站全站排行榜数据分析
"""
import requests, pandas as pd, time, random, os,warnings
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']; plt.rcParams['axes.unicode_minus'] = False

BASE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(BASE, "output")
os.makedirs(OUT, exist_ok=True)
VD = os.path.join(BASE, "videos_top50.csv"); CD = os.path.join(BASE, "hot_comments.csv")


#一、数据爬取
def crawl():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    })
    r = s.get('https://www.bilibili.com/', timeout=10)
    print(f'  获取cookies: {dict(s.cookies)}')
    s.headers.update({'Referer': 'https://www.bilibili.com/', 'Origin': 'https://www.bilibili.com'})

    def api(url, retry=3):
        for i in range(retry):
            try:
                d = s.get(url, timeout=15).json()
                if d.get('code') == 0: return d
                code = d.get('code')
                if code in (-352, 352, -412, 412):
                    time.sleep(2 * (i + 1) + random.random()); continue
                print(f'  API code={code} {d.get("message","")}')
                if i < retry - 1: time.sleep(2)
                else: return d
            except Exception as e:
                print(f'  异常: {e}'); time.sleep(2)
        return None

    print("爬取排行榜...")
    r = api('https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all')
    if not r or r.get('code') != 0:
        raise Exception(f'排行榜失败 code={r.get("code") if r else "网络错误"}')

    vids = []
    for idx, it in enumerate(r['data']['list'][:50], 1):
        st = it['stat']
        vids.append({
            'rank': idx, 'title': it['title'], 'bvid': it['bvid'], 'aid': it['aid'],
            'up_name': it['owner']['name'], 'up_mid': it['owner']['mid'],
            'partition': it['tname'], 'tid': it['tid'],
            'view': st['view'], 'like': st['like'], 'danmaku': st['danmaku'],
            'reply': st['reply'], 'coin': st['coin'], 'favorite': st['favorite'],
            'share': st['share'], 'duration': it['duration'], 'score': it['score'],
        })
        print(f"  [{idx}/50] {it['title'][:30]}...")
        time.sleep(0.3 + random.random() * 0.2)
    vdf = pd.DataFrame(vids)

    print("爬取评论...")
    cmts = []
    for i, row in vdf.iterrows():
        d = api(f"https://api.bilibili.com/x/v2/reply/main?type=1&oid={row['aid']}&sort=2&ps=10", retry=2)
        if d and d.get('data') and d['data'].get('replies'):
            for rp in d['data']['replies'][:10]:
                cmts.append({
                    'aid': row['aid'], 'bvid': row['bvid'], 'video_title': row['title'],
                    'partition': row['partition'], 'username': rp['member']['uname'],
                    'content': rp['content']['message'], 'like': rp['like'],
                    'reply_count': rp['rcount'], 'level': rp['member']['level_info']['current_level'],
                })
        time.sleep(0.5 + random.random() * 0.3)

    print("爬取标签...")
    tags = []
    for _, row in vdf.iterrows():
        d = api(f"https://api.bilibili.com/x/tag/archive/tags?bvid={row['bvid']}", retry=2)
        tags.append(','.join([t['tag_name'] for t in d['data']]) if d and d.get('code') == 0 and d.get('data') else '')
        time.sleep(0.2)
    vdf['tags'] = tags

    return vdf, pd.DataFrame(cmts), s


#二、分区分析
def partition_analysis(vdf):
    vdf['interaction'] = (vdf['like'] + vdf['coin'] + vdf['favorite'] + vdf['share']) / vdf['view']

    pc = vdf['partition'].value_counts()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].pie(pc.values, labels=pc.index, autopct='%1.1f%%', startangle=90)
    axes[0].set_title('各分区视频数量占比', fontsize=13, fontweight='bold')

    grp = vdf.groupby('partition').agg(avg_view=('view', 'mean'), avg_like=('like', 'mean'),
        avg_interaction=('interaction', 'mean'), count=('rank', 'count')).sort_values('count', ascending=False)
    print('\n各分区统计:')
    for name, row in grp.iterrows():
        print(f'  {name}: 视频数={int(row["count"])}, 均播放={row["avg_view"]/10000:.1f}万, 均互动率={row["avg_interaction"]*100:.2f}%')
    grp_interaction = grp.sort_values('avg_interaction',ascending = True)
    axes[1].barh(grp_interaction.index, grp_interaction['avg_interaction'] * 100, color='steelblue')
    axes[1].set_xlabel('平均互动率（%）')
    axes[1].set_title('各分区平均互动率', fontsize=13, fontweight='bold')
    for i, (_, row) in enumerate(grp_interaction.iterrows()):
        axes[1].text(row['avg_interaction'] * 100 + 0.1, i, f'{row["avg_interaction"]*100:.2f}%', va='center')
    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'fig_partition.png'), dpi=150); plt.close()
    print('→ fig_partition.png')


#三、评论多维度分析
POS = ['好', '赞', '牛', '爱', '喜欢', '厉害', '支持', '棒', '不错', '绝', '神', '帅', '强', '美', '优秀',
       'nb', '666', '哈哈', '笑', '有意思', '有趣', '妙', '燃', '感动', '泪目', 'respect', '真的',
       '太', 'yyds', '吹爆', '经典']
NEG = ['差', '烂', '失望', '垃圾', '恶心', '无聊', '难看', '无语', '坑', '水', '烦', '吐', '尬',
       '迷惑', '阴间', '不', '别', '没有']
QUES = ['?', '？', '吗', '什么', '怎么', '为什么', '如何', '哪里', '谁', '哪', '请问']

def analyze_comment(text):
    t = str(text).lower()
    pos_s = sum(1 for w in POS if w in t)
    neg_s = sum(1 for w in NEG if w in t)
    que_s = sum(1 for w in QUES if w in t)
    if pos_s > neg_s: sent = '正面'
    elif neg_s > pos_s: sent = '负面'
    else: sent = '中性'

    if pos_s >= 3: intent = '强烈赞美'
    elif neg_s >= 3: intent = '强烈吐槽'
    elif que_s >= 1: intent = '提问/讨论'
    elif len(t) > 50: intent = '深度讨论'
    elif len(t) < 5: intent = '简短表态'
    else: intent = '一般评论'

    l = len(t)
    if l > 80: qual = '高'
    elif l > 20: qual = '中'
    else: qual = '低'
    return sent, intent, qual

def comment_analysis(cdf):
    cdf['sentiment'], cdf['intent'], cdf['quality'] = zip(*cdf['content'].apply(analyze_comment))

    print(f'共 {len(cdf)} 条评论')
    print('\n情感分布:')
    for k, v in cdf['sentiment'].value_counts().items():
        print(f'  {k}: {v} ({v/len(cdf)*100:.1f}%)')
    print('\n意图分布:')
    for k, v in cdf['intent'].value_counts().items():
        print(f'  {k}: {v} ({v/len(cdf)*100:.1f}%)')
    print('\n质量分布:')
    for k, v in cdf['quality'].value_counts().items():
        print(f'  {k}: {v} ({v/len(cdf)*100:.1f}%)')




#四、扩展分析
def extended_analysis(vdf, cdf):
    if 'tags' in vdf.columns and vdf['tags'].notna().any():
        all_tags = [t.strip() for ts in vdf['tags'].dropna() for t in str(ts).split(',') if t.strip()]
        if all_tags:
            tc = pd.Series(all_tags).value_counts().head(15)
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.barh(tc.index, tc.values, color='coral')
            ax.set_xlabel('频次'); ax.set_title('视频标签词频 Top15', fontsize=13, fontweight='bold')
            ax.invert_yaxis()
            plt.tight_layout(); plt.savefig(os.path.join(OUT, 'fig_tags.png'), dpi=150); plt.close()
            print('→ fig_tags.png')

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(vdf['duration'] / 60, vdf['view'] / 10000, alpha=0.7, c='steelblue')
    ax.set_xlabel('视频时长（分钟）'); ax.set_ylabel('播放量（万）')
    ax.set_title('视频时长 vs 播放量', fontsize=13, fontweight='bold')
    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'fig_duration.png'), dpi=150); plt.close()
    print('→ fig_duration.png')

#主程序
def main():
    print('=' * 60)
    print('【作业二】B站全站排行榜数据分析')
    print('=' * 60)

    #if os.path.exists(VD) and os.path.exists(CD):
        #print("加载已有数据")
        #vdf = pd.read_csv(VD, encoding='utf-8-sig')
        #cdf = pd.read_csv(CD, encoding='utf-8-sig')
    #else:
    #注释部分实现的是当文件夹中存在可供分析的数据时，跳过爬取阶段直接分析已有数据；注释掉这部分之后，每次运行都会重新爬取数据
    vdf, cdf, _ = crawl()
    vdf.to_csv(VD, index=False, encoding='utf-8-sig')
    cdf.to_csv(CD, index=False, encoding='utf-8-sig')
    print(f'视频: {len(vdf)} 条 → {VD}')
    print(f'评论: {len(cdf)} 条 → {CD}')

    print('\n' + '=' * 60); print('二、分区分析'); print('=' * 60)
    partition_analysis(vdf)

    print('\n' + '=' * 60); print('三、评论多维度分析'); print('=' * 60)
    comment_analysis(cdf)

    print('\n' + '=' * 60); print('四、扩展分析'); print('=' * 60)
    extended_analysis(vdf, cdf)

    print('\n分析完成，图表已保存至 output/')

if __name__ == '__main__':
    main()
