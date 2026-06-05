import os
import io
import time
import base64
import requests
import streamlit as st
from PIL import Image
from dotenv import load_dotenv

# Load local .env file if present
load_dotenv()

# ==========================================
# SESSION STATE 初始化
# ==========================================
_state_defaults = {
    "generation_trigger": False,
    "active_engine": None,
    "prompt_state": "",
    "style_desc_state": "",
    "style_choice_state": "",
    "dims_state": (1024, 1024),
    "seed_state": 42,
    "num_images_state": 1,
    "hf_token_state": None,
    "gemini_key_state": None,
    "is_random_seed_state": True,
    "negative_prompt_state": "",
}
for _k, _v in _state_defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ==========================================
# 頁面設定 (PAGE CONFIGURATION)
# ==========================================
st.set_page_config(
    page_title="墨韻生圖 · AI 丹青工作室",
    page_icon="🖌️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 中國水墨風 CSS 配色
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@300;400;500;600;700&family=Noto+Sans+TC:wght@300;400;500;600&display=swap');

/* ===== 全局字體與底色 ===== */
html, body, [class*="css"] {
    font-family: 'Noto Sans TC', 'Microsoft JhengHei', 'STKaiti', serif !important;
}

/* ===== Streamlit 背景 ===== */
.stApp {
    background-color: #f5f0e8 !important;
    background-image:
        radial-gradient(circle at 20% 20%, rgba(139,90,60,0.06) 0%, transparent 50%),
        radial-gradient(circle at 80% 80%, rgba(90,60,30,0.05) 0%, transparent 50%),
        url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%238b6914' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E") !important;
}

/* ===== 主標題區 ===== */
.ink-title-container {
    padding: 1.5rem 0 1.2rem;
    margin-bottom: 1.2rem;
    border-bottom: 2px solid #8b4513;
    position: relative;
}
.ink-title-container::after {
    content: '';
    position: absolute;
    bottom: -5px;
    left: 0;
    width: 60px;
    height: 3px;
    background: #c0392b;
    border-radius: 2px;
}
.main-title {
    font-family: 'Noto Serif TC', 'STKaiti', serif !important;
    font-size: 2.4rem;
    font-weight: 700;
    color: #2c1810 !important;
    margin: 0;
    letter-spacing: 0.05em;
    text-shadow: 1px 1px 0 rgba(139,69,19,0.15);
}
.main-title .ink-brush {
    background: linear-gradient(135deg, #8b1a1a 0%, #c0392b 50%, #5a1a1a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    font-size: 0.68rem;
    font-weight: 600;
    color: #8b1a1a;
    background-color: #fdf0e0;
    border: 1px solid #c9956a;
    border-radius: 2px;
    margin-left: 0.6rem;
    vertical-align: middle;
    letter-spacing: 0.08em;
}
.main-subtitle {
    color: #6b4c2a;
    margin-top: 0.3rem;
    font-size: 0.88rem;
    letter-spacing: 0.03em;
}

/* ===== 卡片容器 ===== */
.card {
    background-color: rgba(255, 250, 240, 0.85);
    border: 1px solid #c9a87a;
    border-top: 3px solid #8b4513;
    border-radius: 4px;
    padding: 1.3rem;
    margin-bottom: 1rem;
    box-shadow: 2px 2px 8px rgba(139,69,19,0.1), inset 0 1px 0 rgba(255,255,255,0.7);
    position: relative;
}
.card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #8b1a1a, #c0392b, #8b4513, #c0392b, #8b1a1a);
    border-radius: 4px 4px 0 0;
}

/* ===== 畫布容器 ===== */
.grid-bg-container {
    background-color: #fdf8f0;
    background-image:
        linear-gradient(to right, rgba(139,90,60,0.05) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(139,90,60,0.05) 1px, transparent 1px);
    background-size: 24px 24px;
    border: 2px solid #c9a87a;
    border-radius: 4px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 480px;
    box-shadow: inset 0 2px 12px rgba(139,90,60,0.08);
}

/* ===== Streamlit 元件覆寫 ===== */
/* 按鈕 */
.stButton > button {
    background: linear-gradient(135deg, #8b1a1a 0%, #a52a2a 100%) !important;
    color: #fdf8f0 !important;
    border: 1px solid #6b1010 !important;
    border-radius: 3px !important;
    font-family: 'Noto Sans TC', serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    box-shadow: 0 2px 6px rgba(139,26,26,0.25), inset 0 1px 0 rgba(255,255,255,0.1) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #a52a2a 0%, #c0392b 100%) !important;
    box-shadow: 0 4px 12px rgba(139,26,26,0.35) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: #fdf8f0 !important;
    color: #8b1a1a !important;
    border: 1px solid #c9a87a !important;
}

/* 下載按鈕 */
.stDownloadButton > button {
    background: rgba(253,248,240,0.9) !important;
    color: #5a3010 !important;
    border: 1px solid #c9a87a !important;
    border-radius: 3px !important;
}

/* Radio 按鈕 */
.stRadio > div {
    background: rgba(253,248,240,0.6);
    border: 1px solid #e8d5b5;
    border-radius: 4px;
    padding: 0.5rem 0.8rem;
}

/* SelectBox */
.stSelectbox > div > div {
    background-color: #fdf8f0 !important;
    border: 1px solid #c9a87a !important;
    border-radius: 3px !important;
    color: #2c1810 !important;
}

/* TextArea */
.stTextArea > div > div > textarea {
    background-color: #fdf8f0 !important;
    border: 1px solid #c9a87a !important;
    border-radius: 3px !important;
    color: #2c1810 !important;
    font-family: 'Noto Sans TC', sans-serif !important;
}
.stTextArea > div > div > textarea:focus {
    border-color: #8b4513 !important;
    box-shadow: 0 0 0 2px rgba(139,69,19,0.15) !important;
}

/* TextInput */
.stTextInput > div > div > input {
    background-color: #fdf8f0 !important;
    border: 1px solid #c9a87a !important;
    border-radius: 3px !important;
    color: #2c1810 !important;
}

/* Subheader */
.stApp h2, .stApp h3 {
    color: #2c1810 !important;
    font-family: 'Noto Serif TC', serif !important;
    border-left: 3px solid #c0392b;
    padding-left: 0.6rem;
}

/* Expander */
.stExpander {
    border: 1px solid #c9a87a !important;
    border-radius: 4px !important;
    background: rgba(253,248,240,0.7) !important;
}

/* Success / Info / Error */
.stSuccess {
    background-color: rgba(200,230,180,0.3) !important;
    border: 1px solid #6a9a50 !important;
    border-radius: 3px !important;
}
.stInfo {
    background-color: rgba(200,185,150,0.25) !important;
    border: 1px solid #c9a060 !important;
    border-radius: 3px !important;
}
.stError {
    background-color: rgba(220,130,130,0.15) !important;
    border: 1px solid #b05050 !important;
    border-radius: 3px !important;
}

/* Slider */
.stSlider > div > div > div {
    background-color: #8b4513 !important;
}

/* Checkbox */
.stCheckbox > label > div[data-testid="stMarkdownContainer"] p {
    color: #4a2c10 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #f0e8d8 !important;
    border-right: 2px solid #c9a87a !important;
}

/* Footer 分隔線 */
.ink-footer {
    text-align: center;
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid #c9a87a;
    color: #8b6a40;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
}

/* 畫布標題 */
.canvas-title {
    color: #2c1810 !important;
    font-family: 'Noto Serif TC', serif !important;
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    border-bottom: 1px solid #c9a87a;
    padding-bottom: 0.4rem;
    margin-bottom: 0.8rem;
}

/* 印章裝飾 */
.ink-seal {
    display: inline-block;
    padding: 0.15rem 0.4rem;
    background: #8b1a1a;
    color: #fdf8f0;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    border-radius: 2px;
    transform: rotate(-2deg);
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 輔助函數 (HELPER FUNCTIONS)
# ==========================================

def get_api_token(secret_key, env_key):
    """從 Streamlit secrets、環境變數或 session state 取得 API 金鑰。"""
    try:
        if secret_key in st.secrets:
            return st.secrets[secret_key]
    except Exception:
        pass
    token = os.getenv(env_key)
    if token:
        return token
    session_key = f"key_{env_key.lower()}"
    if session_key in st.session_state:
        return st.session_state[session_key]
    return None


def generate_huggingface_image(prompt, negative_prompt, style_desc, aspect_ratio_dims, seed, token,
                                model_id="nvidia/Cosmos3-Super-Text2Image"):
    """呼叫 Hugging Face Inference API。"""
    API_URL = f"https://router.huggingface.co/hf-inference/models/{model_id}"
    headers = {"Authorization": f"Bearer {token}"}
    final_prompt = f"{prompt}, {style_desc}" if style_desc else prompt
    width, height = aspect_ratio_dims
    payload = {
        "inputs": final_prompt,
        "parameters": {
            "negative_prompt": negative_prompt or "blurry, low quality, distorted",
            "width": width,
            "height": height
        }
    }
    if seed is not None:
        payload["parameters"]["seed"] = int(seed)
    response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
    if response.status_code == 200:
        try:
            return Image.open(io.BytesIO(response.content))
        except Exception as e:
            raise RuntimeError(f"Failed to decode image from Hugging Face: {e}")
    elif response.status_code == 503:
        try:
            estimated_time = response.json().get("estimated_time", 20.0)
            raise RuntimeError(f"模型載入中，請等待約 {estimated_time:.1f} 秒後重試。(HTTP 503)")
        except ValueError:
            raise RuntimeError("模型載入中，請稍後重試。(HTTP 503)")
    else:
        try:
            err_msg = response.json().get("error", f"未知錯誤: {response.text}")
        except Exception:
            err_msg = f"HTTP {response.status_code}: {response.text[:200]}"
        raise RuntimeError(f"Hugging Face API 錯誤：{err_msg}")


def generate_gemini_image(prompt, style_desc, token):
    """呼叫 Gemini 2.5 Flash Image Preview API。"""
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-2.5-flash-image-preview:generateContent?key={token}")
    final_prompt = f"{prompt}, {style_desc}" if style_desc else prompt
    payload = {
        "contents": [{"parts": [{"text": final_prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
    }
    response = requests.post(url, json=payload, timeout=60)
    if response.status_code == 200:
        try:
            data = response.json()
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            image_part = next((p for p in parts if "inlineData" in p), None)
            if not image_part:
                raise RuntimeError("API 回應成功，但未返回圖像資料。")
            image_bytes = base64.b64decode(image_part["inlineData"]["data"])
            return Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            raise RuntimeError(f"解析 Gemini 回應失敗：{e}")
    else:
        try:
            err_msg = response.json().get("error", {}).get("message", f"HTTP {response.status_code}")
        except Exception:
            err_msg = f"HTTP {response.status_code}: {response.text}"
        raise RuntimeError(f"Google Gemini API 錯誤：{err_msg}")


def generate_pollinations_image(prompt, style_desc, aspect_ratio_dims, seed):
    """使用 Pollinations AI（Flux - 完全免金鑰）生成圖像。"""
    import urllib.parse
    final_prompt = f"{prompt}, {style_desc}" if style_desc else prompt
    width, height = aspect_ratio_dims
    encoded = urllib.parse.quote(final_prompt)
    url = f"https://image.pollinations.ai/p/{encoded}?width={width}&height={height}&seed={seed}&model=flux&nologo=true"
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        try:
            return Image.open(io.BytesIO(response.content))
        except Exception as e:
            raise RuntimeError(f"解析 Pollinations 圖像失敗：{e}")
    else:
        raise RuntimeError(f"Pollinations AI 失敗 (HTTP {response.status_code})")


# ==========================================
# 快速範本 Prompt 對應表
# ==========================================
QUICK_PROMPT_MAP = {
    "西洋油畫": "A grand European oil painting of a noble knight on horseback at golden hour, dramatic chiaroscuro lighting, Baroque style, highly detailed",
    "中國水墨畫": "A traditional Chinese ink wash painting of misty mountain peaks with pine trees and a lone scholar, sumi-e style, subtle brushstrokes, minimal palette",
    "吉卜力":   "A peaceful countryside village with lush green hills and a windmill, whimsical Studio Ghibli animation style, hand-drawn, magical and warm",
    "日系水彩": "A beautiful Japanese garden with cherry blossoms, traditional temple in the background, delicate anime watercolor style, soft pastel tones",
    "可愛 3D":  "A cute chubby hamster wearing an astronaut helmet on the moon, holding cheese, 3D render, clay style, warm soft lighting",
    "科幻奇幻": "A futuristic floating city above the clouds with crystal towers, ancient rune portals glowing purple, epic fantasy meets sci-fi, cinematic lighting",
    "復古風":   "A 1960s retro diner scene with neon signs, classic cars outside, vintage warm tones, film grain texture, nostalgic Americana",
}

# ==========================================
# APP 介面 (UI LAYOUT)
# ==========================================

# 主標題
st.markdown("""
<div class="ink-title-container">
    <h1 class="main-title">
        <span class="ink-brush">墨韻生圖</span>
        <span class="badge">丹青多引擎</span>
    </h1>
    <p class="main-subtitle">
        整合 NVIDIA Cosmos 3.0 · Gemini · Flux · Puter.js，揮毫即見丹青，支援多模型一鍵切換
    </p>
</div>
""", unsafe_allow_html=True)

# 雙欄佈局（左 5：右 7）
col_left, col_right = st.columns([5, 7], gap="large")

# ─────────────────────────────────────────────
# 左側控制面板
# ─────────────────────────────────────────────
with col_left:

    # ── 1. 選擇引擎 ──
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔮 一、選擇生圖引擎 (Engine)")

    engine_choice = st.radio(
        label="選擇欲使用的後端 AI 模型：",
        options=[
            "nvidia/Cosmos3-Super-Text2Image (Hugging Face)",
            "black-forest-labs/FLUX.1-schnell (Hugging Face)",
            "Gemini 2.5 Flash Image (Google API)",
            "Puter.js (Stable Diffusion - 完全免金鑰)",
            "Pollinations AI (Flux - 完全免金鑰)",
        ],
        index=3,
        label_visibility="collapsed"
    )

    hf_token = None
    gemini_key = None

    if "Hugging Face" in engine_choice:
        hf_token = get_api_token("HF_TOKEN", "HF_TOKEN")
        if not hf_token:
            st.info("💡 未在 secrets 或 .env 中找到金鑰，請於下方手動輸入。")
            user_token = st.text_input(
                "Hugging Face API Token：", type="password", placeholder="hf_...",
                help="登入 Hugging Face → Settings → Access Tokens"
            )
            if user_token:
                st.session_state["key_hf_token"] = user_token.strip()
                hf_token = user_token.strip()
        else:
            st.success("✅ 已自動載入 Hugging Face API 金鑰")

    elif "Gemini" in engine_choice:
        gemini_key = get_api_token("GEMINI_API_KEY", "GEMINI_API_KEY")
        if not gemini_key:
            st.info("💡 未在 secrets 或 .env 中找到金鑰，請於下方手動輸入。")
            user_key = st.text_input(
                "Gemini API Key：", type="password", placeholder="AIzaSy...",
                help="前往 Google AI Studio 申請免費金鑰"
            )
            if user_key:
                st.session_state["key_gemini_api_key"] = user_key.strip()
                gemini_key = user_key.strip()
        else:
            st.success("✅ 已自動載入 Gemini API 金鑰")

    elif "Puter.js" in engine_choice:
        st.success("🎋 Puter.js 為瀏覽器端免金鑰引擎，由瀏覽器直接生圖，穩定且無需任何金鑰！")
    else:
        st.success("🎋 Pollinations AI 為免金鑰引擎，可直接點擊生圖！")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── 2. 提示詞輸入 ──
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📝 二、輸入創意提示詞 (Prompt)")

    quick_prompt = st.selectbox(
        "快速套用範本：",
        options=["自行輸入..."] + list(QUICK_PROMPT_MAP.keys())
    )

    # 依選擇填入對應英文 prompt
    default_prompt_val = QUICK_PROMPT_MAP.get(quick_prompt, "")

    prompt = st.text_area(
        "輸入您的創意提示詞（英文效果尤佳）：",
        value=default_prompt_val,
        height=110,
        placeholder="例如: A misty mountain landscape with ancient pine trees, traditional Chinese ink wash style, serene and poetic..."
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 3. 進階設定 ──
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.expander("🛠️ 三、高級自訂設置 (Advanced Options)", expanded=False):

        ratio_choice = st.selectbox(
            "圖片尺寸比例 (Aspect Ratio)：",
            options=["1:1 (正方形 - 1024x1024)", "16:9 (橫向寬螢幕 - 1024x576)", "9:16 (直式手機 - 576x1024)"]
        )
        if "1:1" in ratio_choice:
            dims = (1024, 1024)
        elif "16:9" in ratio_choice:
            dims = (1024, 576)
        else:
            dims = (576, 1024)

        style_choice = st.selectbox(
            "藝術風格 (Image Style)：",
            options=["無特定風格", "寫實攝影", "日系動漫", "賽博朋克", "電影質感", "3D 黏土", "水墨丹青"]
        )
        style_mappings = {
            "無特定風格":  "",
            "寫實攝影":    "photorealistic, hyperrealistic, 8k resolution, highly detailed, raw photo",
            "日系動漫":    "anime key visual, beautiful anime watercolor illustration, vivid colors",
            "賽博朋克":    "cyberpunk style, neon lights, rainy street reflecting lights, high contrast",
            "電影質感":    "cinematic shot, warm dramatic volumetric lighting, highly detailed movie still",
            "3D 黏土":    "cute 3d clay illustration, smooth textures, warm lighting, miniature model",
            "水墨丹青":    "traditional Chinese ink wash painting, sumi-e brushstrokes, minimal color, misty atmosphere, poetic",
        }
        style_desc = style_mappings[style_choice]

        negative_prompt = st.text_input(
            "排除提示詞 (Negative Prompt)：",
            value="blurry, low quality, ugly, distorted, lowres, text, signature",
            help="這些元素將盡量避免出現在生成的圖片中"
        )

        is_random_seed = st.checkbox("自動隨機種子 (Random Seed)", value=True)
        if is_random_seed:
            seed = int(time.time()) % 1000000
            st.number_input("種子數值 (Seed)：", value=seed, disabled=True)
        else:
            seed = st.number_input("種子數值 (Seed)：", min_value=0, max_value=99999999, value=42)

        num_images = st.slider("生成張數 (Number of Images)：", min_value=1, max_value=4, value=1,
                               help="多張生成時將循序進行")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── 生成按鈕 ──
    generate_btn = st.button("🖌️ 揮毫落紙・開始生圖", use_container_width=True, type="primary")

    if generate_btn:
        st.session_state["generation_trigger"] = True
        st.session_state["active_engine"]       = engine_choice
        st.session_state["prompt_state"]        = prompt
        st.session_state["style_desc_state"]    = style_desc
        st.session_state["style_choice_state"]  = style_choice
        st.session_state["dims_state"]          = dims
        st.session_state["seed_state"]          = seed
        st.session_state["num_images_state"]    = num_images
        st.session_state["hf_token_state"]      = hf_token
        st.session_state["gemini_key_state"]    = gemini_key
        st.session_state["is_random_seed_state"]= is_random_seed
        st.session_state["negative_prompt_state"] = negative_prompt

# ─────────────────────────────────────────────
# 右側畫布
# ─────────────────────────────────────────────
with col_right:
    st.markdown('<p class="canvas-title">🖼️ 即時渲染畫布（丹青成品）</p>', unsafe_allow_html=True)
    canvas_container = st.container()

    if st.session_state["generation_trigger"]:
        prompt_val          = st.session_state["prompt_state"]
        active_engine       = st.session_state["active_engine"]
        style_desc_val      = st.session_state["style_desc_state"]
        style_choice_val    = st.session_state["style_choice_state"]
        dims_val            = st.session_state["dims_state"]
        seed_val            = st.session_state["seed_state"]
        num_images_val      = st.session_state["num_images_state"]
        hf_token_val        = st.session_state["hf_token_state"]
        gemini_key_val      = st.session_state["gemini_key_state"]
        is_random_seed_val  = st.session_state["is_random_seed_state"]
        negative_prompt_val = st.session_state["negative_prompt_state"]

        if not prompt_val.strip():
            st.error("⚠️ 請先在左側輸入提示詞，再點擊生圖！")
            st.session_state["generation_trigger"] = False
        else:
            can_proceed = True
            if "Hugging Face" in active_engine and not hf_token_val:
                st.error("❌ 使用 Hugging Face 需填入 API Token！")
                can_proceed = False
            elif "Gemini" in active_engine and not gemini_key_val:
                st.error("❌ 使用 Gemini 需填入 API Key！")
                can_proceed = False

            if can_proceed:
                if "Puter" in active_engine:
                    import json
                    final_prompt_str = f"{prompt_val}, {style_desc_val}" if style_desc_val else prompt_val
                    prompt_json = json.dumps(final_prompt_str)
                    num_images_json = int(num_images_val)

                    puter_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <script src="https://js.puter.com/v2/"></script>
                        <script src="https://cdn.tailwindcss.com"></script>
                        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
                        <style>
                            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;600&display=swap');
                            body {{
                                background: linear-gradient(135deg,#fdf8f0 0%,#f5ede0 100%);
                                font-family:'Noto Sans TC',sans-serif;
                            }}
                            .ink-grid {{
                                background-image:
                                    linear-gradient(to right,rgba(139,90,60,.05) 1px,transparent 1px),
                                    linear-gradient(to bottom,rgba(139,90,60,.05) 1px,transparent 1px);
                                background-size:24px 24px;
                            }}
                        </style>
                    </head>
                    <body class="p-4 ink-grid min-h-screen text-stone-800 flex flex-col items-center justify-center">
                        <div id="loading" class="text-center space-y-6 w-full max-w-md px-6 py-12">
                            <div class="relative w-20 h-20 mx-auto">
                                <div class="absolute inset-0 rounded-full border-4 border-amber-100"></div>
                                <div class="absolute inset-0 rounded-full border-4 border-t-red-700 border-r-amber-700 animate-spin"></div>
                                <div class="absolute inset-0 flex items-center justify-center text-red-800 text-2xl">🖌️</div>
                            </div>
                            <div class="space-y-2">
                                <h4 class="text-sm font-semibold text-stone-700">Puter.js 丹青師揮毫中...</h4>
                                <div class="inline-block px-3 py-1 bg-amber-50 text-amber-800 border border-amber-300 rounded text-xs font-semibold">
                                    引擎：Puter.js · Stable Diffusion XL
                                </div>
                            </div>
                        </div>
                        <div id="result" class="hidden w-full flex flex-col items-center space-y-6">
                            <div id="image-container"></div>
                            <div class="text-red-700 text-xs font-bold" id="time-badge"></div>
                        </div>
                        <script>
                            async function runGeneration() {{
                                const promptText = {prompt_json};
                                const numImages = {num_images_json};
                                const startTime = Date.now();
                                try {{
                                    const promises = [];
                                    for (let i = 0; i < numImages; i++) {{
                                        promises.push(puter.ai.txt2img(promptText, {{
                                            model: "stabilityai/stable-diffusion-xl-base-1.0"
                                        }}));
                                    }}
                                    const results = await Promise.all(promises);
                                    const container = document.getElementById('image-container');
                                    container.innerHTML = '';
                                    container.className = numImages > 1
                                        ? "grid grid-cols-2 gap-4 w-full max-w-2xl"
                                        : "grid grid-cols-1 gap-4 w-full max-w-md";
                                    results.forEach((res, idx) => {{
                                        if (res && res.src) {{
                                            const wrapper = document.createElement('div');
                                            wrapper.className = "flex flex-col items-center space-y-2 bg-amber-50 p-3 rounded border border-amber-300 shadow-sm";
                                            const img = document.createElement('img');
                                            img.src = res.src;
                                            img.className = "max-h-80 w-full object-contain rounded border border-amber-200";
                                            img.alt = `Generated Image ${{idx+1}}`;
                                            const btn = document.createElement('button');
                                            btn.className = "flex items-center justify-center gap-2 py-2 px-4 bg-red-800 hover:bg-red-700 text-amber-50 font-semibold text-xs rounded shadow transition-colors w-full";
                                            btn.innerHTML = '<i class="fa-solid fa-file-arrow-down"></i><span>下載圖片</span>';
                                            btn.onclick = () => {{
                                                const link = document.createElement('a');
                                                link.href = res.src;
                                                link.download = `ink_image_${{idx+1}}_${{Date.now()}}.png`;
                                                document.body.appendChild(link);
                                                link.click();
                                                document.body.removeChild(link);
                                            }};
                                            wrapper.appendChild(img);
                                            wrapper.appendChild(btn);
                                            container.appendChild(wrapper);
                                        }} else {{
                                            throw new Error("Puter returned empty response.");
                                        }}
                                    }});
                                    const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
                                    document.getElementById('time-badge').innerText = `🎉 丹青成功！費時：${{elapsed}} 秒`;
                                    document.getElementById('loading').classList.add('hidden');
                                    document.getElementById('result').classList.remove('hidden');
                                }} catch (err) {{
                                    console.error(err);
                                    document.getElementById('loading').innerHTML = `
                                        <span style="font-size:3rem">⚠️</span>
                                        <p style="color:#b91c1c;font-weight:600;margin-top:.5rem">Puter.js 生成失敗</p>
                                        <p style="color:#78716c;font-size:.8rem;margin-top:.25rem">${{err.message || '連線逾時'}}</p>
                                        <p style="color:#78716c;font-size:.8rem;margin-top:1rem">請確認網路連線或重試。</p>
                                    `;
                                }}
                            }}
                            if (typeof puter !== 'undefined') {{ runGeneration(); }}
                            else {{ window.onload = runGeneration; }}
                        </script>
                    </body>
                    </html>
                    """
                    with canvas_container:
                        import streamlit.components.v1 as components
                        components.html(puter_html, height=520, scrolling=True)

                else:
                    st.toast("🖌️ 正在向繪圖伺服器傳送請求...", icon="📡")
                    spinner_msg = "✨ 丹青師揮毫中，請稍候..."
                    if "Cosmos3" in active_engine:
                        spinner_msg += "（Cosmos3 首次載入可能需 1~2 分鐘）"
                    elif "FLUX" in active_engine:
                        spinner_msg += "（Flux 首次載入可能需 1~2 分鐘）"

                    with st.spinner(spinner_msg):
                        try:
                            images_result = []
                            start_time = time.time()

                            for i in range(num_images_val):
                                cur_seed = seed_val + i if not is_random_seed_val else (seed_val + i * 137) % 1000000
                                if "Hugging Face" in active_engine:
                                    model_id = active_engine.split(" (")[0]
                                    img = generate_huggingface_image(
                                        prompt_val, negative_prompt_val, style_desc_val,
                                        dims_val, cur_seed, hf_token_val, model_id=model_id
                                    )
                                elif "Gemini" in active_engine:
                                    img = generate_gemini_image(prompt_val, style_desc_val, gemini_key_val)
                                else:
                                    img = generate_pollinations_image(prompt_val, style_desc_val, dims_val, cur_seed)
                                images_result.append(img)

                            elapsed_time = time.time() - start_time

                            with canvas_container:
                                st.markdown('<div class="grid-bg-container">', unsafe_allow_html=True)
                                if len(images_result) == 1:
                                    st.image(images_result[0],
                                             caption=f"提示詞：{prompt_val} | 風格：{style_choice_val}",
                                             use_container_width=True)
                                    buf = io.BytesIO()
                                    images_result[0].save(buf, format="PNG")
                                    st.download_button(
                                        label="💾 下載高畫質圖片",
                                        data=buf.getvalue(),
                                        file_name=f"ink_image_{int(time.time())}.png",
                                        mime="image/png",
                                        type="secondary"
                                    )
                                else:
                                    cols = st.columns(min(2, len(images_result)))
                                    for idx, img in enumerate(images_result):
                                        with cols[idx % 2]:
                                            st.image(img, caption=f"#{idx+1} (Seed: {seed_val+idx})",
                                                     use_container_width=True)
                                            buf = io.BytesIO()
                                            img.save(buf, format="PNG")
                                            st.download_button(
                                                label=f"💾 下載 #{idx+1}",
                                                data=buf.getvalue(),
                                                file_name=f"ink_{idx+1}_{int(time.time())}.png",
                                                mime="image/png"
                                            )
                                st.markdown(
                                    f'<p style="color:#8b4513;font-size:.85rem;font-weight:bold;margin-top:1rem;">'
                                    f'🎉 丹青成功！費時：{elapsed_time:.2f} 秒</p>',
                                    unsafe_allow_html=True
                                )
                                st.markdown('</div>', unsafe_allow_html=True)
                                st.success("生圖大成功！可點下載按鈕保存您的丹青作品。")

                        except Exception as e:
                            st.error(f"❌ 生圖失敗：{e}")
                            st.markdown("""
> [!WARNING]
> **故障排除**：若使用 Cosmos3，模型體積巨大，伺服器可能偶發 503/403。
> 建議切換至 **Puter.js（完全免金鑰）** 作為備用引擎即可順利出圖。
                            """)
                            with canvas_container:
                                st.markdown("""
                                <div class="grid-bg-container">
                                    <span style="font-size:3rem">⚠️</span>
                                    <p style="color:#b91c1c;font-weight:600;margin-top:.5rem">連線異常或模型未啟動</p>
                                    <p style="color:#78716c;font-size:.8rem;text-align:center;max-width:320px;">
                                        伺服器目前無法處理此請求，建議切換至「Puter.js」引擎。
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
    else:
        with canvas_container:
            st.markdown("""
            <div class="grid-bg-container">
                <span style="font-size:3.5rem">🖌️</span>
                <p style="font-weight:bold;color:#5a3010;margin-top:.75rem;font-family:'Noto Serif TC',serif;font-size:1.1rem;letter-spacing:.05em;">
                    筆墨已備，靜候揮毫
                </p>
                <p style="color:#8b6a40;font-size:.85rem;text-align:center;max-width:380px;line-height:1.7;">
                    請於左側輸入創意靈感，調整風格與引擎，<br>點擊「揮毫落紙」後，您的丹青作品將在此呈現。
                </p>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# 頁尾
# ==========================================
st.markdown("""
<div class="ink-footer">
    🖌️ 墨韻生圖 · AI 丹青工作室 · 旗艦多引擎版
    &nbsp;|&nbsp; Powered by Hugging Face · Google AI · Puter.js · Pollinations
    &nbsp;|&nbsp; <span class="ink-seal">學生作業</span>
</div>
""", unsafe_allow_html=True)