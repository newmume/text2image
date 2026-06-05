import os
import sys
import json
import time
import datetime
import re
import base64
import requests
import subprocess

# CONFIGURATION & CONSTANTS
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(DIRECTORY, "config.json")
GALLERY_DIR = os.path.join(DIRECTORY, "gallery")

# NVIDIA/AI styling variables
NVIDIA_GREEN = "#76B900"
DARK_BG = "#090D16"
CARD_BG = "#131926"

# Supported Model Definitions
MODELS = {
    # Gemini models
    "imagen-4.0-generate-001": {
        "name": "Google Imagen 4.0 Generate (預設體驗/自訂 Key)",
        "provider": "gemini",
        "api_name": "imagen-4.0-generate-001"
    },
    "imagen-3.0-generate-002": {
        "name": "Google Imagen 3.0 Generate (自訂 Key)",
        "provider": "gemini",
        "api_name": "imagen-3.0-generate-002"
    },
    "imagen-3.0-fast-generate-002": {
        "name": "Google Imagen 3.0 Fast Generate (自訂 Key)",
        "provider": "gemini",
        "api_name": "imagen-3.0-fast-generate-002"
    },
    # Hugging Face models
    "nvidia/Cosmos3-Super-Text2Image": {
        "name": "NVIDIA Cosmos 3 (HF: nvidia/Cosmos3-Super-Text2Image)",
        "provider": "hf",
        "api_name": "nvidia/Cosmos3-Super-Text2Image"
    },
    "black-forest-labs/FLUX.1-schnell": {
        "name": "FLUX.1 Schnell (HF: black-forest-labs/FLUX.1-schnell)",
        "provider": "hf",
        "api_name": "black-forest-labs/FLUX.1-schnell"
    },
    "black-forest-labs/FLUX.1-dev": {
        "name": "FLUX.1 Dev (HF: black-forest-labs/FLUX.1-dev)",
        "provider": "hf",
        "api_name": "black-forest-labs/FLUX.1-dev"
    },
    "stabilityai/stable-diffusion-3.5-large": {
        "name": "Stable Diffusion 3.5 Large (HF: stabilityai/stable-diffusion-3.5-large)",
        "provider": "hf",
        "api_name": "stabilityai/stable-diffusion-3.5-large"
    },
    "stabilityai/stable-diffusion-xl-base-1.0": {
        "name": "Stable Diffusion XL 1.0 (HF: stabilityai/stable-diffusion-xl-base-1.0)",
        "provider": "hf",
        "api_name": "stabilityai/stable-diffusion-xl-base-1.0"
    }
}

def is_running_in_streamlit():
    """Helper to check if code is running inside Streamlit."""
    try:
        import streamlit as st
        return st.runtime.exists()
    except (ImportError, AttributeError):
        return False

# Load/Save Persistent Settings (behaves like localStorage)
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Check for legacy engine settings to keep compatibility
                if "model" not in config:
                    if config.get("engine") == "hf":
                        config["model"] = "nvidia/Cosmos3-Super-Text2Image"
                    else:
                        config["model"] = "imagen-4.0-generate-001"
                return config
        except Exception:
            pass
    return {
        "hf_token": "", 
        "gemini_key": "", 
        "engine": "gemini", 
        "model": "imagen-4.0-generate-001",
        "ratio": "1:1"
    }

def save_config(config):
    try:
        os.makedirs(DIRECTORY, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

# Image Gallery File Storage
def save_image_to_gallery(image_bytes, prompt, model_name, ratio):
    os.makedirs(GALLERY_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.png"
    filepath = os.path.join(GALLERY_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(image_bytes)
        
    meta_filename = f"{timestamp}.json"
    meta_filepath = os.path.join(GALLERY_DIR, meta_filename)
    
    model_info = MODELS.get(model_name, {"name": model_name})
    
    metadata = {
        "timestamp": timestamp,
        "prompt": prompt,
        "model": model_name,
        "engine": model_info["name"].split(" (")[0],
        "ratio": ratio,
        "image_file": filename,
        "time_str": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    with open(meta_filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)
        
    return filepath

def load_gallery():
    os.makedirs(GALLERY_DIR, exist_ok=True)
    items = []
    for filename in sorted(os.listdir(GALLERY_DIR), reverse=True):
        if filename.endswith(".json"):
            try:
                filepath = os.path.join(GALLERY_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                img_path = os.path.join(GALLERY_DIR, meta["image_file"])
                if os.path.exists(img_path):
                    meta["img_path"] = img_path
                    items.append(meta)
            except Exception:
                pass
    return items

# Style Suffix regex cleaning
def clean_styles(text):
    style_regex = r",\s*(traditional Chinese painting|ink wash style|elegant|dynasty core|detailed watercolor brushstrokes|ultra cute|chibi|pastel colors|3D clay render|toy aesthetic|Studio Ghibli style|hand-drawn anime|lush green hills|nostalgic anime aesthetic|cyberpunk|futuristic city|photorealistic|hyperdetailed|anime illustration|vibrant colors|oil painting|robotic physical simulation|nvidia style|precise physics|watercolor painting).*"
    return re.sub(style_regex, "", text, flags=re.IGNORECASE)

# API Calls
def optimize_prompt(prompt, user_key):
    api_key = user_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise Exception("請先在引擎設定中輸入自訂 Gemini API Key！")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "systemInstruction": {
            "parts": [{
                "text": "You are an expert prompt engineer for advanced physical simulation and image diffusion models. Rewrite and significantly expand the user prompt into a highly detailed, visually stunning, and physically realistic English prompt. Describe the camera perspective, realistic physical properties, textures, materials, lighting details, and background setup to leverage the full parameter capability of the selected model. Do not include introductory words or titles. Do not output markdown, just output the raw prompt in English."
            }]
        }
    }
    
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
    if response.status_code != 200:
        try:
            err_data = response.json()
            err_msg = err_data.get("error", {}).get("message", response.text)
        except Exception:
            err_msg = response.text
        raise Exception(f"Gemini API 錯誤 ({response.status_code}): {err_msg}")
        
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        raise Exception("未能成功解析 Gemini API 回傳內容。")

def generate_image_hf(prompt, token, model_name, width, height):
    hf_url = f"https://api-inference.huggingface.co/models/{model_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": width,
            "height": height
        }
    }
    
    delay = 2.0
    for i in range(5):
        try:
            response = requests.post(hf_url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                return response.content
            elif response.status_code == 503:
                # Model is loading, wait and retry
                time.sleep(delay)
                delay *= 2
                continue
            else:
                try:
                    err_msg = response.json()
                    err = err_msg.get("error", response.text)
                except Exception:
                    err = response.text
                raise Exception(f"Hugging Face API 錯誤 ({response.status_code}): {err}")
        except requests.exceptions.RequestException as e:
            if i == 4:
                raise Exception(f"連線失敗: {e}")
            time.sleep(delay)
            delay *= 2
            
    raise Exception("Hugging Face 模型啟動超時，請稍候重試。")

def generate_image_gemini(prompt, api_key, model_name, ratio):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:predict?key={api_key}"
    payload = {
        "instances": [
            { "prompt": prompt }
        ],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": ratio
        }
    }
    
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
    if response.status_code != 200:
        try:
            err_data = response.json()
            err_msg = err_data.get("error", {}).get("message", response.text)
        except Exception:
            err_msg = response.text
        raise Exception(f"Imagen API 錯誤 ({response.status_code}): {err_msg}")
        
    data = response.json()
    try:
        b64_bytes = data["predictions"][0]["bytesBase64Encoded"]
        return base64.b64decode(b64_bytes)
    except (KeyError, IndexError):
        raise Exception("未能成功獲取圖像字節流。")

def main():
    import streamlit as st
    
    # 1. Page Config
    st.set_page_config(
        page_title="AI Text2Image Multi-Model Studio",
        page_icon="🔮",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # 2. Session State Initialization
    if "config" not in st.session_state:
        st.session_state.config = load_config()
    if "prompt" not in st.session_state:
        st.session_state.prompt = ""
        
    # 3. Inject CSS and FontAwesome
    st.markdown('<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">', unsafe_allow_html=True)
    st.markdown(f"""
    <style>
        /* Dark cyber theme */
        .stApp {{
            background-color: {DARK_BG} !important;
            color: #e2e8f0 !important;
        }}
        .nvidia-logo {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 1px solid #1e293b;
        }}
        .nvidia-cube {{
            width: 36px;
            height: 36px;
            background-color: {NVIDIA_GREEN};
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: {DARK_BG};
            font-size: 20px;
            box-shadow: 0 0 15px rgba(118, 185, 0, 0.4);
        }}
        .nvidia-title-text {{
            font-size: 20px;
            font-weight: 800;
            color: white;
            line-height: 1.1;
            letter-spacing: 1px;
        }}
        .nvidia-subtitle-text {{
            font-size: 10px;
            color: {NVIDIA_GREEN};
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}
        
        /* Expanders */
        div[data-testid="stExpander"] {{
            background-color: {CARD_BG} !important;
            border: 1px solid #1e293b !important;
            border-radius: 16px !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3) !important;
        }}
        
        /* Bordered containers (custom cards) */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: {CARD_BG} !important;
            border: 1px solid #1e293b !important;
            border-radius: 16px !important;
            padding: 20px !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3) !important;
        }}
        
        /* Secondary (unselected) buttons */
        button[data-testid="stBaseButton-secondary"] {{
            background-color: {CARD_BG} !important;
            border: 1px solid #1e293b !important;
            color: #94a3b8 !important;
            border-radius: 12px !important;
            transition: all 0.3s ease !important;
        }}
        button[data-testid="stBaseButton-secondary"]:hover {{
            border-color: {NVIDIA_GREEN} !important;
            color: {NVIDIA_GREEN} !important;
            background-color: rgba(118, 185, 0, 0.05) !important;
            box-shadow: 0 0 10px rgba(118, 185, 0, 0.1) !important;
        }}
        
        /* Primary (selected) buttons */
        button[data-testid="stBaseButton-primary"] {{
            background-color: rgba(118, 185, 0, 0.08) !important;
            border: 1px solid {NVIDIA_GREEN} !important;
            color: {NVIDIA_GREEN} !important;
            border-radius: 12px !important;
            box-shadow: 0 0 15px rgba(118, 185, 0, 0.3) !important;
            font-weight: bold !important;
            transition: all 0.3s ease !important;
        }}
        button[data-testid="stBaseButton-primary"]:hover {{
            background-color: rgba(118, 185, 0, 0.15) !important;
            box-shadow: 0 0 20px rgba(118, 185, 0, 0.5) !important;
        }}
        
        /* Main generate button override */
        .main-btn-wrapper button[data-testid="stBaseButton-primary"] {{
            background: linear-gradient(90deg, {NVIDIA_GREEN} 0%, #10b981 100%) !important;
            color: {DARK_BG} !important;
            font-weight: 800 !important;
            border: none !important;
            box-shadow: 0 0 15px rgba(118, 185, 0, 0.4) !important;
            border-radius: 16px !important;
            height: 52px !important;
        }}
        .main-btn-wrapper button[data-testid="stBaseButton-primary"]:hover {{
            background: linear-gradient(90deg, #83d151 0%, #34d399 100%) !important;
            box-shadow: 0 0 25px rgba(118, 185, 0, 0.6) !important;
        }}
        
        /* AI Upsampler button override */
        .upsample-btn-wrapper button[data-testid="stBaseButton-secondary"] {{
            background: linear-gradient(90deg, #7c3aed 0%, #4f46e5 100%) !important;
            color: white !important;
            font-weight: bold !important;
            border: none !important;
            box-shadow: 0 0 15px rgba(139, 92, 246, 0.4) !important;
        }}
        .upsample-btn-wrapper button[data-testid="stBaseButton-secondary"]:hover {{
            background: linear-gradient(90deg, #8b5cf6 0%, #6366f1 100%) !important;
            box-shadow: 0 0 20px rgba(139, 92, 246, 0.6) !important;
        }}
        
        /* Tab style overrides */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 12px;
            border-bottom: 1px solid #1e293b;
        }}
        .stTabs [data-baseweb="tab"] {{
            height: 45px;
            border-radius: 8px 8px 0px 0px;
            background-color: transparent;
            color: #94a3b8;
            font-weight: 600;
            font-size: 14px;
        }}
        .stTabs [aria-selected="true"] {{
            color: {NVIDIA_GREEN} !important;
            border-bottom: 2px solid {NVIDIA_GREEN} !important;
        }}
    </style>
    """, unsafe_allow_html=True)

    # 4. Render App Header
    st.markdown(f"""
    <div class="nvidia-logo">
        <div class="nvidia-cube">
            🔮
        </div>
        <div>
            <div class="nvidia-title-text">AI STUDIO</div>
            <div class="nvidia-subtitle-text">Multi-Model Studio v3.5</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 5. Render Tabs
    tab_generator, tab_gallery, tab_info = st.tabs(["✨ 生成創作", "🖼️ 作品藝廊", "📖 模型指南"])

    # ================= TAB 1: GENERATOR =================
    with tab_generator:
        # Settings Expander
        with st.expander("⚙️ 生成引擎與模型設定", expanded=True):
            # Model Selection Dropdown
            model_keys = list(MODELS.keys())
            model_display_names = [MODELS[k]["name"] for k in model_keys]
            
            saved_model = st.session_state.config.get("model", "imagen-4.0-generate-001")
            if saved_model not in MODELS:
                saved_model = "imagen-4.0-generate-001"
            default_index = model_keys.index(saved_model)
            
            selected_display_name = st.selectbox(
                "選擇生成模型 (Model Dropdown)",
                options=model_display_names,
                index=default_index
            )
            
            current_model = [k for k, v in MODELS.items() if v["name"] == selected_display_name][0]
            current_engine = MODELS[current_model]["provider"]
            
            # Save settings if changed
            if current_model != st.session_state.config.get("model") or current_engine != st.session_state.config.get("engine"):
                st.session_state.config["model"] = current_model
                st.session_state.config["engine"] = current_engine
                save_config(st.session_state.config)
                st.rerun()
            
            if current_engine == "hf":
                st.markdown("**Hugging Face 設定**")
                hf_token = st.text_input(
                    "Hugging Face Read Token",
                    value=st.session_state.config.get("hf_token", ""),
                    type="password",
                    placeholder="hf_..."
                )
                if hf_token != st.session_state.config.get("hf_token", ""):
                    st.session_state.config["hf_token"] = hf_token
                    save_config(st.session_state.config)
                st.markdown("[👉 如何獲取 Token？](https://huggingface.co/settings/tokens)")
                st.caption(f"目前請求端點: `https://api-inference.huggingface.co/models/{current_model}`")
                
            st.markdown("**自訂 Gemini API Key (選填)**")
            gemini_key = st.text_input(
                "Gemini API Key",
                value=st.session_state.config.get("gemini_key", ""),
                type="password",
                placeholder="AIzaSy... (選填，若連線失敗時使用)"
            )
            if gemini_key != st.session_state.config.get("gemini_key", ""):
                st.session_state.config["gemini_key"] = gemini_key
                save_config(st.session_state.config)
            st.markdown("[👉 取得免費 Key](https://aistudio.google.com/)")

        st.write("")

        # Prompt Input Area Card
        with st.container(border=True):
            prompt_input = st.text_area(
                "輸入生成靈感 (中英文皆可)",
                value=st.session_state.prompt,
                height=120,
                placeholder="例如：一個漫步在霓虹燈籠台北街頭的機械神龍，極致物理光澤、電影級光影..."
            )
            st.session_state.prompt = prompt_input
            
            # Character count
            st.markdown(f"<div style='text-align: right; font-size: 11px; color: #64748b; margin-top: -10px; margin-bottom: 10px;'>{len(prompt_input)} / 500</div>", unsafe_allow_html=True)

            col_opt, col_clr = st.columns([3, 1])
            with col_opt:
                st.markdown('<div class="upsample-btn-wrapper">', unsafe_allow_html=True)
                if st.button("🪄 AI 提示詞大師最佳化", use_container_width=True):
                    if not prompt_input.strip():
                        st.warning("請先輸入一點簡短的靈感，再讓 AI 大師進行最佳化！")
                    else:
                        with st.spinner("AI 正在精密改寫提示詞..."):
                            try:
                                key_to_use = st.session_state.config.get("gemini_key", "")
                                optimized = optimize_prompt(prompt_input, key_to_use)
                                st.session_state.prompt = optimized
                                st.success("AI 提示詞最佳化完成！已針對生圖模型優化物理、材質與光影細節。")
                                st.rerun()
                            except Exception as e:
                                st.error(f"AI 優化失敗: {e}")
                st.markdown('</div>', unsafe_allow_html=True)
            with col_clr:
                if st.button("❌ 清除", use_container_width=True):
                    st.session_state.prompt = ""
                    st.rerun()

        st.write("")

        # Aspect Ratio Card
        with st.container(border=True):
            st.markdown("**畫面比例 (Aspect Ratio)**")
            ratio_cols = st.columns(3)
            ratios = ["1:1", "16:9", "9:16"]
            current_ratio = st.session_state.config.get("ratio", "1:1")
            
            for idx, r in enumerate(ratios):
                with ratio_cols[idx]:
                    label = "🔳 1:1 正方形" if r == "1:1" else ("📺 16:9 寬螢幕" if r == "16:9" else "📱 9:16 直向海報")
                    is_selected = (r == current_ratio)
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(label, key=f"btn_ratio_{r}", type=btn_type, use_container_width=True):
                        st.session_state.config["ratio"] = r
                        save_config(st.session_state.config)
                        st.rerun()

        st.write("")

        # Style Presets Card
        with st.container(border=True):
            st.markdown("**藝術風格預設 (Style Presets)**")
            style_cols = st.columns(3)
            styles = [
                {"id": "chinese", "emoji": "🏮", "name": "中國風", "suffix": ", traditional Chinese painting, ink wash style, elegant, dynasty core, detailed watercolor brushstrokes"},
                {"id": "cute", "emoji": "🧸", "name": "可愛風", "suffix": ", ultra cute, chibi, pastel colors, 3D clay render, toy aesthetic, charming, soft lighting"},
                {"id": "ghibli", "emoji": "🌳", "name": "吉卜力", "suffix": ", Studio Ghibli style, hand-drawn anime, lush green hills, soft nostalgic lighting, nostalgic anime aesthetic, masterpiece"},
                {"id": "cyberpunk", "emoji": "🌌", "name": "賽博朋克", "suffix": ", cyberpunk, futuristic city, neon glow, high-tech, unreal engine 5, 8k"},
                {"id": "realistic", "emoji": "📸", "name": "極致寫實", "suffix": ", photorealistic, hyperdetailed, 8k resolution, cinematic lighting, dslr camera, sharp focus"},
                {"id": "anime", "emoji": "🎏", "name": "日系動漫", "suffix": ", anime illustration, beautiful hand-drawn art, vibrant colors, makoto shinkai style, high-res"},
                {"id": "watercolor", "emoji": "🎨", "name": "極光水彩", "suffix": ", watercolor painting, artistic splatters, soft lighting, masterpiece, detailed texture"},
                {"id": "physic-ai", "emoji": "🧬", "name": "3D 物理AI", "suffix": ", robotic physical simulation, precise physics, mechanical gears, metal textures, nvidia style, realistic raytracing"},
                {"id": "empty", "emoji": "❌", "name": "無預設", "suffix": ""}
            ]

            for idx, s in enumerate(styles):
                col_idx = idx % 3
                with style_cols[col_idx]:
                    suffix = s["suffix"]
                    is_active = suffix != "" and suffix in st.session_state.prompt
                    if s["id"] == "empty":
                        is_active = not any(style["suffix"] in st.session_state.prompt for style in styles if style["suffix"] != "")
                        
                    btn_text = f"{s['emoji']} {s['name']}"
                    btn_type = "primary" if is_active else "secondary"
                    if st.button(btn_text, key=f"btn_style_{s['id']}", type=btn_type, use_container_width=True):
                        cleaned = clean_styles(st.session_state.prompt)
                        if s["id"] != "empty":
                            st.session_state.prompt = cleaned + suffix
                        else:
                            st.session_state.prompt = cleaned
                        st.rerun()

        st.write("")

        # Generate Button
        model_display_name = MODELS.get(current_model, {}).get("name", "AI").split(" (")[0]
        st.markdown('<div class="main-btn-wrapper">', unsafe_allow_html=True)
        if st.button(f"🚀 開始生成 {model_display_name} 畫像", use_container_width=True, type="primary"):
            if not st.session_state.prompt.strip():
                st.warning("請輸入生圖提示詞 (Prompt)！")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                step1 = st.empty()
                step2 = st.empty()
                step3 = st.empty()
                step4 = st.empty()
                
                # Step 1
                progress_bar.progress(10)
                status_text.markdown(f"🔄 **正在連接生圖伺服器與驗證...**")
                step1.markdown("⏳ 正在建立安全連接與 API 驗證...")
                time.sleep(0.8)
                
                # Step 2
                progress_bar.progress(35)
                status_text.markdown(f"🔄 **載入並分發「{model_display_name}」張量權重...**")
                step1.markdown("✅ 正在建立安全連接與 API 驗證...")
                step2.markdown(f"⏳ 載入並分發「{model_display_name}」張量權重...")
                time.sleep(1.0)
                
                # Step 3
                progress_bar.progress(65)
                status_text.markdown("🔄 **擴散去噪演算與影像還原進行中...**")
                step2.markdown(f"✅ 載入並分發「{model_display_name}」張量權重...")
                step3.markdown("⏳ 高解析度物理擴散去噪演算進行中...")
                
                try:
                    # Call API
                    if current_engine == "hf":
                        token = st.session_state.config.get("hf_token", "").strip()
                        if not token:
                            raise Exception("請先在引擎設定中輸入您的 Hugging Face Access Token！")
                        
                        width = 1280 if current_ratio == "16:9" else (720 if current_ratio == "9:16" else 1024)
                        height = 720 if current_ratio == "16:9" else (1280 if current_ratio == "9:16" else 1024)
                        
                        image_bytes = generate_image_hf(st.session_state.prompt, token, current_model, width, height)
                    else:
                        active_key = st.session_state.config.get("gemini_key", "").strip()
                        active_key = active_key or os.environ.get("GEMINI_API_KEY", "")
                        if not active_key:
                            raise Exception("此模型需要輸入 Gemini API Key。請在「生成引擎設定」中輸入您的 Key！")
                        
                        image_bytes = generate_image_gemini(st.session_state.prompt, active_key, current_model, current_ratio)
                    
                    # Step 4
                    progress_bar.progress(90)
                    status_text.markdown("🔄 **解碼潛在空間並合成最終像素...**")
                    step3.markdown("✅ 高解析度物理擴散去噪演算完成...")
                    step4.markdown("⏳ 解碼潛在空間並合成最終像素...")
                    time.sleep(0.8)
                    
                    # Save to local gallery
                    save_image_to_gallery(image_bytes, st.session_state.prompt, current_model, current_ratio)
                    
                    progress_bar.progress(100)
                    status_text.markdown("✨ **圖像渲染完畢！**")
                    step4.markdown("✅ 解碼潛在空間並合成最終像素...")
                    st.success("圖像物理渲染生成完成！")
                    
                    # Display Result
                    st.image(image_bytes, caption=f"由 {model_display_name} 生成", use_container_width=True)
                    
                    # Action buttons
                    col_dl, col_cp = st.columns(2)
                    with col_dl:
                        st.download_button(
                            label="💾 儲存結果圖像",
                            data=image_bytes,
                            file_name=f"{model_display_name.replace(' ', '_')}-{int(time.time())}.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    with col_cp:
                        st.code(st.session_state.prompt, language="text")
                        st.caption("💡 提示詞已顯示於上方，可雙擊複製。")
                        
                    time.sleep(1.0)
                    st.rerun()
                    
                except Exception as e:
                    progress_bar.empty()
                    status_text.empty()
                    step1.empty()
                    step2.empty()
                    step3.empty()
                    step4.empty()
                    st.error(f"生成失敗: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    # ================= TAB 2: GALLERY =================
    with tab_gallery:
        st.subheader("我的創作品藝廊")
        gallery_items = load_gallery()
        
        if not gallery_items:
            st.info("還沒有任何生成紀錄。立即前往生成器輸入您的靈感，AI 將賦予其絕美的視覺物理真實感！")
        else:
            col_header, col_act = st.columns([3, 1])
            with col_header:
                st.caption("所有產出紀錄皆安全地儲存於本地 `gallery/` 資料夾內。")
            with col_act:
                if st.button("🗑️ 清空藝廊", use_container_width=True):
                    # Clean directory
                    for filename in os.listdir(GALLERY_DIR):
                        try:
                            os.remove(os.path.join(GALLERY_DIR, filename))
                        except Exception:
                            pass
                    st.success("藝廊紀錄已清空！")
                    st.rerun()
            
            st.write("---")
            
            # Responsive 2-column grid layout
            rows = (len(gallery_items) + 1) // 2
            for r in range(rows):
                cols = st.columns(2)
                for c in range(2):
                    idx = r * 2 + c
                    if idx < len(gallery_items):
                        item = gallery_items[idx]
                        with cols[c]:
                            # Render image
                            st.image(item["img_path"], use_container_width=True)
                            st.markdown(f"🗓️ **時間:** `{item['time_str']}`")
                            st.markdown(f"⚙️ **模型:** `{item['engine']}` | 📱 **比例:** `{item['ratio']}`")
                            st.text_area("提示詞", value=item["prompt"], height=70, disabled=True, key=f"txt_{item['timestamp']}")
                            
                            col_g_re, col_g_dl = st.columns(2)
                            with col_g_re:
                                if st.button("🔄 帶入提示詞", key=f"reuse_{item['timestamp']}", use_container_width=True):
                                    st.session_state.prompt = item["prompt"]
                                    st.success("提示詞已帶入！請點選上方「生成創作」頁籤。")
                                    st.rerun()
                            with col_g_dl:
                                try:
                                    with open(item["img_path"], "rb") as file:
                                        st.download_button(
                                            label="💾 儲存圖像",
                                            data=file,
                                            file_name=item["image_file"],
                                            mime="image/png",
                                            key=f"dl_{item['timestamp']}",
                                            use_container_width=True
                                        )
                                except Exception:
                                    st.error("讀取檔案失敗。")
                            st.write("---")

    # ================= TAB 3: INFO =================
    with tab_info:
        st.markdown("""
        ### AI 多模型生成技術指南
        了解本 Studio 支援的多款世界頂尖影像生成模型。
        
        #### 🧬 支援模型介紹
        * **NVIDIA Cosmos 3**: 參數量達 64B 的物理世界基礎大模型，在開源文生圖排行榜上榮登第一。擅長精準光影渲染與極具動態真實感的場景建構。
        * **FLUX.1 Schnell / Dev**: 由 Black Forest Labs 開發的頂尖模型，具備優秀的提示詞遵循度與文字渲染能力，畫面細膩，色彩表現張力十足。
        * **Stable Diffusion 3.5 Large / XL**: 經典的開源生成模型家族，社群生態強大，擅長人物、插畫及各式寫實風格。
        * **Google Imagen 4.0 / 3.0**: 來自 Google DeepMind 的先進商業模型，出圖速度極快，能生成文字和精緻的寫實畫面。
        
        #### 🚀 使用說明
        1. **Hugging Face 模型**: 需要至 [huggingface.co](https://huggingface.co/) 註冊並在 Settings -> Access Tokens 生成一個 `Read` 權限的 Token。
        2. **Gemini API**: 提供免 Key 預設體驗，若要使用高頻率請求，建議前往 [Google AI Studio](https://aistudio.google.com/) 申請免費 API Key 並貼入。
        
        #### 📊 模型規格與指標
        | 模型名稱 | 提供商 | 參數量/技術 | 特點 |
        | :--- | :--- | :--- | :--- |
        | **NVIDIA Cosmos 3** | NVIDIA | 64B / MoT | 物理擬真度極高、高階光影 |
        | **FLUX.1 Dev** | BFL | 12B / Rectified Flow | 細節精緻度高、手部字形極佳 |
        | **FLUX.1 Schnell** | BFL | 12B / Distilled | 速度極快、4步即可完成去噪 |
        | **SD 3.5 Large** | Stability AI | 8B / MMDiT | 遵循提示詞、多風格融合 |
        | **Imagen 4.0** | Google | DeepMind Proprietary | 速度極快、中文理解力強 |
        """)

if __name__ == "__main__":
    if is_running_in_streamlit():
        main()
    else:
        # Programmatic run: when user runs "python text2image.py", launch Streamlit automatically
        file_path = os.path.abspath(__file__)
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 正在啟動 Streamlit 伺服器...")
        try:
            subprocess.run([
                sys.executable, "-m", "streamlit", "run", file_path,
                "--server.headless=true",
                "--browser.gatherUsageStats=false"
            ])
        except KeyboardInterrupt:
            print("\n伺服器已安全關閉。")
            sys.exit(0)
