from playwright.sync_api import sync_playwright
import re, csv, os, time, random, collections

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"}
BASE = os.path.dirname(os.path.abspath(__file__))

def parse_jobs(html):
    jobs = []
    cards = re.findall(r'<div class="joblist-box__item[^"]*"(.*?)<span class="joblist-box__item__icon-job', html, re.DOTALL)
    for card in cards:
        job = {}
        m = re.search(r'jobinfo__name">([^<]+)</a>', card); job["title"] = m.group(1).strip() if m else ""
        m = re.search(r'jobinfo__salary[^>]*>(.+?)</p>', card, re.DOTALL); job["salary"] = m.group(1).strip() if m else ""
        m = re.search(r'location[^>]+>.*?<span>([^<]+)</span>', card); job["city"] = m.group(1).strip() if m else ""
        items = re.findall(r'other-info-item">\s*([^<]{2,30})\s*</div>', card)
        job["experience"] = items[0].strip() if len(items) > 0 else ""
        job["education"] = items[1].strip() if len(items) > 1 else ""
        m = re.search(r'companyinfo__name">\s*([^<]+)\s*</a>', card); job["company"] = m.group(1).strip() if m else ""
        job["skills"] = ""
        ss = re.search(r'jobinfo__tag">(.*?)</div>\s*</div>\s*<!---->\s*<div class="jobinfo__other-info', card, re.DOTALL)
        if ss:
            st = re.findall(r'joblist-box__item-tag">\s*([^<]+)\s*</div>', ss.group(1))
            if st: job["skills"] = ", ".join(s.strip() for s in st)
        m = re.search(r'href="([^"]*jobdetail[^"]*)"', card); job["detail_url"] = m.group(1) if m else ""
        jobs.append(job)
    return jobs

def scrape_one(page, name, code):
    print("=== " + name + " ===")
    page.goto("https://www.zhaopin.com/sou/" + code + "/p1", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    html = page.content()
    pages = sorted(set(int(p) for p in re.findall(r"/p(\d+)", html)))
    mp = min(max(pages) if pages else 1, 4)
    res = []
    for p in range(1, mp + 1):
        print("  page " + str(p) + "/" + str(mp) + "...", end=" ")
        page.goto("https://www.zhaopin.com/sou/" + code + "/p" + str(p), wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        jobs = parse_jobs(page.content())
        for j in jobs: j["search_keyword"] = name
        res.extend(jobs)
        print(str(len(jobs)) + " jobs")
        if p < mp: time.sleep(random.uniform(0.5, 1.0))
    return res

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, channel="msedge")
    kws = {"人工智能": "kw9QT5RPB6FA0FQ", "机器学习": "kwCST5CQ2RCP760", "深度学习": "kwDNOLT9IRCP760", "大模型": "kwB4JMK8ANHC", "计算机视觉": "kwHEGNN5R77A4SD2E9"}
    all_jobs = []
    for n, c in kws.items():
        ctx = browser.new_context(user_agent=H["User-Agent"])
        page = ctx.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        all_jobs.extend(scrape_one(page, n, c))
        ctx.close()
    browser.close()
    
    unique = []
    seen = set()
    for j in all_jobs:
        url = j["detail_url"]
        if url and url not in seen:
            seen.add(url)
            unique.append(j)
    raw_path = os.path.join(BASE, "zhaopin_ai_jobs.csv")
    with open(raw_path, "w", newline="", encoding="utf-8-sig") as f:
        if unique:
            w = csv.DictWriter(f, fieldnames=list(unique[0].keys())); w.writeheader(); w.writerows(unique)
    print("\n爬取" + str(len(unique)) + "个岗位 zhaopin_ai_jobs.csv")

def parse_salary(s):
    s = s.strip()
    if s == "面议": return None
    mul = 1
    if "/天" in s: mul = 22; s = s.replace("/天", "")
    elif "/月" in s: s = s.replace("/月", "")
    if "·" in s: s = s.split("·")[0]
    s = s.replace("元", "").replace(" ", "").strip()
    if "万" in s: mul *= 10000; s = s.replace("万", "")
    try:
        if "-" in s or "~" in s or "–" in s:
            sep = "-" if "-" in s else ("~" if "~" in s else "–")
            parts = s.split(sep); lo = float(parts[0].strip()); hi = float(parts[1].strip())
        else:
            lo = float(s); hi = lo
    except: return None
    avg = (lo + hi) / 2 * mul
    return {"min": round(lo * mul), "max": round(hi * mul), "avg": round(avg)}

JOB_TYPES = [
    ("算法工程师", ["算法工程师", "算法研究员", "算法专家", "算法", "人工神经网络"]),
    ("NLP/CV/多模态", ["NLP", "自然语言处理", "计算机视觉", "CV", "多模态", "图像识别", "图像算法", "机器视觉", "语音识别", "视觉算法", "SLAM"]),
    ("AI产品经理", ["产品经理", "产品总监"]),
    ("AI开发/工程", ["开发工程师", "后端", "全栈", "系统架构", "AI应用", "应用开发", "软件工程"]),
    ("AI运维/实施", ["运维", "实施", "部署", "技术支持", "售后", "维护", "IT"]),
    ("AI销售/商务", ["销售", "商务", "市场", "客户经理", "营销", "业务"]),
    ("数据标注/处理", ["数据标注", "数据训练", "数据清洗", "数据采集", "标注员", "训练师"]),
    ("教育培训", ["教育", "培训", "讲师", "教师", "教学", "教授", "辅导"]),
    ("AI管培生/实习", ["管培生", "实习生", "助理"]),
]

def classify_job_type(title):
    for cls_name, keywords in JOB_TYPES:
        for kw in keywords:
            if kw in title: return cls_name
    return "AI开发/工程" if "工程师" in title else "其他"

print("\n========== 数据清洗 ==========")
rows = []
with open(raw_path, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f): rows.append(r)
print("原始数据:", len(rows))
    
cleaned = []; removed = 0
for r in rows:
    sd = parse_salary(r["salary"])
    if sd is None and "面议" in r["salary"]: removed += 1; continue
    elif sd is None: continue
    city = r["city"].split("·")[0].strip() if r["city"] else ""
    exp_map = {"经验不限": 0, "1年以下": 0, "1-3年": 2, "3-5年": 4, "5-10年": 7, "10年以上": 12}
    edu_map = {"学历不限": 0, "大专": 1, "本科": 2, "硕士": 3, "博士": 4}
    cleaned.append({
        "title": r["title"], "salary_min": sd["min"], "salary_max": sd["max"], "salary_avg": sd["avg"],
        "city_raw": r["city"], "city": city, "experience_years": exp_map.get(r["experience"].strip(), 0),
        "education_code": edu_map.get(r["education"].strip(), 0), "company": r["company"],
        "skills": r["skills"], "job_type": classify_job_type(r["title"]), "search_keyword": r["search_keyword"],
    })
    
city_counts = collections.Counter(r["city"] for r in cleaned if r["city"])
hot_cities = set(c for c, _ in city_counts.most_common(10))
for r in cleaned: r["is_hot_city"] = 1 if r["city"] in hot_cities else 0
    
print("移除了(面议):", removed, "清洗了:", len(cleaned))
for jt, n in collections.Counter(r["job_type"] for r in cleaned).most_common():
    print(" ", jt + ":", n)
    
clean_path = os.path.join(BASE, "cleaned_ai_jobs.csv")
with open(clean_path, "w", newline="", encoding="utf-8-sig") as f:
    fields = ["title","salary_min","salary_max","salary_avg","city_raw","city","experience_years",
                "education_code","company","skills","job_type","is_hot_city","search_keyword"]
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(cleaned)
print("保存", len(cleaned), "条数据 cleaned_ai_jobs.csv")
