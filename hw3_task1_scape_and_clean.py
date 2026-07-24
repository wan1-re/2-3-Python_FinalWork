import httpx, csv, re, os, time

BASE_URL = "https://hf-mirror.com"
CATEGORIES = {
    "text_generation": {"pipeline_tag": "text-generation", "label": "文本生成"},
    "image_classification": {"pipeline_tag": "image-classification", "label": "图像分类"},
    "text_to_image": {"pipeline_tag": "text-to-image", "label": "文本生成图像"},
}
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
LIMIT = 100

def extract_parameter_size(model_id, tags, card_data):
    name = model_id.split("/")[-1]
    m = re.search(r"(\d+(?:\.\d+)?)\s*([BMK])\b", name, re.IGNORECASE)
    if m:
        return f"{m.group(1)}{m.group(2).upper()}"
    m = re.search(r"-(\d+(?:\.\d+)?)([BMK])\b", name, re.IGNORECASE)
    if m:
        return f"{m.group(1)}{m.group(2).upper()}"
    for kw in ["xxl","xl","large","medium","base","small","tiny","nano","micro","mini"]:
        if re.search(r"\b" + kw + r"\b", name, re.IGNORECASE):
            return kw.capitalize()
    for tag in tags:
        if tag.startswith("size_categories:"):
            return tag.split(":", 1)[1]
    if card_data:
        for key in ["num_parameters","parameters","parameter_count","model_size"]:
            if key in card_data:
                return str(card_data[key])
    return "未知"

def extract_frameworks(library_name, tags):
    fws = set()
    if library_name:
        fws.add(library_name)
    known = ["transformers","pytorch","tensorflow","safetensors","diffusers","timm","onnx","keras","jax","flax","gguf","vllm","peft","bitsandbytes"]
    for tag in tags:
        for fw in known:
            if fw in tag.lower():
                fws.add(tag)
                break
    return ", ".join(sorted(fws)) if fws else "未知"

def extract_license(card_data, tags):
    if card_data and "license" in card_data:
        return card_data["license"]
    for tag in tags:
        if tag.startswith("license:"):
            return tag.split(":", 1)[1]
    return "未知"

def extract_paper(tags):
    ids = [t.split(":",1)[1] for t in tags if t.startswith("arxiv:")]
    return ", ".join(ids) if ids else ""

def fetch_top_models(pipeline_tag, limit=100):
    all_models = []
    page = 0
    client = httpx.Client(timeout=30.0)
    try:
        while len(all_models) < limit:
            params = {"pipeline_tag": pipeline_tag, "sort": "downloads", "direction": -1,
                       "limit": min(limit, 100), "full": True, "cardData": True}
            if page > 0:
                params["offset"] = page * min(limit, 100)
            resp = client.get(f"{BASE_URL}/api/models", params=params)
            batch = resp.json()
            if not batch:
                break
            all_models.extend(batch)
            page += 1
            if len(batch) < min(limit, 100):
                break
            time.sleep(0.3)
        return all_models[:limit]
    finally:
        client.close()

def process_models(models):
    rows = []
    for idx, m in enumerate(models, 1):
        model_id = m.get("modelId", m.get("id", ""))
        tags = m.get("tags", [])
        cd = m.get("cardData", {})
        rows.append({
            "排名": idx,
            "模型名称": model_id,
            "累计下载量": m.get("downloads", 0),
            "社区点赞数": m.get("likes", 0),
            "参数规模标签": extract_parameter_size(model_id, tags, cd),
            "最后更新时间": m.get("lastModified", ""),
            "支持框架": extract_frameworks(m.get("library_name", ""), tags),
            "开源协议": extract_license(cd, tags),
            "关联论文(ArXiv)": extract_paper(tags),
        })
    return rows

def save_to_csv(rows, category_key):
    fname = f"hf_{category_key}_top100.csv"
    filepath = os.path.join(OUTPUT_DIR, fname)
    fieldnames = ["排名","模型名称","累计下载量","社区点赞数","参数规模标签",
                   "最后更新时间","支持框架","开源协议","关联论文(ArXiv)"]
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return filepath

def main():
    results = {}
    for cat_key, info in CATEGORIES.items():
        models = fetch_top_models(info["pipeline_tag"], LIMIT)
        rows = process_models(models)
        fp = save_to_csv(rows, cat_key)
        results[cat_key] = {"label": info["label"], "count": len(rows), "filepath": fp}
        time.sleep(0.3)

    print("爬取完成!")
    for r in results.values():
        print(f"  [{r['label']}] {r['count']} 条 -> {os.path.basename(r['filepath'])}")

#数据清洗与标准化
SIZE_TEXT_MAP = {
    "tiny": "Tiny", "nano": "Nano", "micro": "Micro", "mini": "Mini",
    "small": "Small", "medium": "Medium", "base": "Base", "large": "Large",
    "huge": "Huge", "xl": "XL", "xxl": "XXL",
}

FRAMEWORK_DISPLAY = {
    "diffusers": "diffusers", "transformers": "transformers",
    "transformers.js": "transformers.js", "pytorch": "pytorch",
    "tensorflow": "tensorflow", "jax": "jax", "flax": "flax",
    "onnx": "onnx", "keras": "keras", "safetensors": "safetensors",
    "timm": "timm", "timm_wrapper": "timm_wrapper",
    "gguf": "gguf", "ggml": "ggml", "vllm": "vLLM",
    "comfyui": "comfyUI", "peft": "peft", "bitsandbytes": "bitsandbytes",
    "model optimizer": "Model Optimizer",
}

REMOVE_PREFIXES = ("base_model:", "deploy:", "region:", "dataset:", "arxiv:", "license:")

PARAM_DICT = {
    "openai-community/gpt2": "124M","distilbert/distilgpt2": "82M","deepseek-ai/DeepSeek-R1": "671B",
    "deepseek-ai/DeepSeek-V3": "671B","deepseek-ai/DeepSeek-V3.2": "685B","deepseek-ai/DeepSeek-V2-Lite-Chat": "16B",
    "deepseek-ai/DeepSeek-V4-Flash": "284B","deepseek-ai/DeepSeek-V4-Pro": "1600B","antirez/deepseek-v4-gguf": "284B",
    "zai-org/GLM-4.7-Flash": "4.7B","zai-org/GLM-5.2-FP8": "5.2B","zai-org/GLM-5-FP8": "5B",
    "Qwen/Qwen3-Coder-Next": "80B","Qwen/Qwen3-Coder-Next-FP8": "80B","MiniMaxAI/MiniMax-M2.7": "2.7B",
}

def clean_parameter_tag(tag, model_id):
    if tag == "未知":
        return "unknown", "", ""
    name = model_id.split("/")[-1]
    if re.search(r"K$", tag, re.IGNORECASE):
        if re.search(r"in\d+k", name, re.IGNORECASE) or re.search(r"\d+k-\d+", name, re.IGNORECASE):
            return "unknown", "", ""
    tag = tag.replace("Xl", "XL").replace("xl", "XL")
    m = re.match(r"(\d+(?:\.\d+)?)\s*([BMK])\s*$", tag, re.IGNORECASE)
    if m:
        return tag, float(m.group(1)), m.group(2).upper()
    lower = tag.lower()
    if lower in SIZE_TEXT_MAP:
        return SIZE_TEXT_MAP[lower], "", ""
    return tag, "", ""


def clean_framework_str(fw_str):
    if fw_str == "未知":
        return "none"
    parts = [p.strip() for p in fw_str.split(", ")]
    result = set()
    for p in parts:
        if not p:
            continue
        if p.lower().startswith(REMOVE_PREFIXES):
            continue
        lower = p.lower()
        if lower.startswith("diffusers") or lower in ("stable-diffusion-diffusers", "stable-diffusion-xl-diffusers"):
            result.add("diffusers")
        elif lower == "comfyui":
            result.add("comfyUI")
        elif lower in FRAMEWORK_DISPLAY:
            result.add(FRAMEWORK_DISPLAY[lower])
        else:
            result.add(p)
    return ", ".join(sorted(result)) if result else "none"


def clean_and_standardize():
    fnames = {
        "text_generation": "hf_text_generation_top100.csv",
        "image_classification": "hf_image_classification_top100.csv",
        "text_to_image": "hf_text_to_image_top100.csv",
    }
    fieldnames = [
        "排名", "模型名称", "累计下载量", "社区点赞数",
        "参数规模标签", "参数量(数值)", "参数量(单位)",
        "最后更新时间", "支持框架", "开源协议", "关联论文(ArXiv)",
    ]
    for cat_key, fname in fnames.items():
        inpath = os.path.join(OUTPUT_DIR, fname)
        outpath = os.path.join(OUTPUT_DIR, f"cleaned_{fname}")
        with open(inpath, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        cleaned = []
        for row in rows:
            param_tag = PARAM_DICT.get(row["模型名称"], row["参数规模标签"])
            tag, val, unit = clean_parameter_tag(param_tag, row["模型名称"])
            fw = clean_framework_str(row["支持框架"])
            lic = "other" if row["开源协议"] == "未知" else row["开源协议"]
            cleaned.append({
                "排名": row["排名"], "模型名称": row["模型名称"],
                "累计下载量": row["累计下载量"], "社区点赞数": row["社区点赞数"],
                "参数规模标签": tag, "参数量(数值)": val, "参数量(单位)": unit,
                "最后更新时间": row["最后更新时间"], "支持框架": fw,
                "开源协议": lic, "关联论文(ArXiv)": row["关联论文(ArXiv)"],
            })
        with open(outpath, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(cleaned)
        print(f"  [{cat_key}] 清洗后 {len(cleaned)} 条 -> {os.path.basename(outpath)}")


if __name__ == "__main__":
    main()
    print("\n开始清洗与标准化...")
    clean_and_standardize()
    print("清洗完成")
