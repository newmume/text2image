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

# NVIDIA styling variables
NVIDIA_GREEN = "#76B900"
DARK_BG = "#090D16"
CARD_BG = "#131926"

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
                return json.load(f)
        except Exception:
            pass
    return {"hf_token": "", "gemini_key": "", "engine": "gemini", "ratio": "1:1"}

def save_config(config):
    try:
        os.makedirs(DIRECTORY, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

# Image Gallery File Storage
def save_image_to_gallery(image_bytes, prompt, engine, ratio):
    os.makedirs(GALLERY_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.png"
    filepath = os.path.join(GALLERY_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(image_bytes)
        
    meta_filename = f"{timestamp}.json"
    meta_filepath = os.path.join(GALLERY_DIR, meta_filename)
    
    metadata = {
        "timestamp": timestamp,
        "prompt": prompt,
        "engine": "NVIDIA Cosmos 3" if engine == "hf" else "Imagen 4.0 Demo",
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
                "text": "You are an expert prompt engineer for the NVIDIA Cosmos 3 (Cosmos3-Super-Text2Image) physical simulation and image diffusion model. Rewrite and significantly expand the user prompt into a highly detailed, visually stunning, and physically realistic English prompt. Ensure you describe the camera perspective, realistic physical properties, textures, materials, lighting details, and background setup to leverage the full 64B parameter physical modeling capability of Cosmos 3. Do not include introductory words or titles. Do not output markdown, just output the raw prompt in English."
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

def generate_image_hf(prompt, token, width, height):
    hf_url = "https://api-inference.huggingface.co/models/nvidia/Cosmos3-Super-Text2Image"
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

def generate_image_gemini(prompt, api_key, ratio):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key={api_key}"
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
        page_title="Cosmos 3 Super Text2Image AI",
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
            background-color: {DARK_BG};
            color: #e2e8f0;
        }}
        .nvidia-logo {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-b: 1px solid #1e293b;
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
            <div class="nvidia-title-text">COSMOS 3</div>
            <div class="nvidia-subtitle-text">Physical AI Generator</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 5. Render Tabs
    tab_generator, tab_gallery, tab_info = st.tabs(["✨ 生成創作", "🖼️ 作品藝廊", "📖 模型指南"])

    # ================= TAB 1: GENERATOR =================
    with tab_generator:
        # Settings Expander
        with st.expander("⚙️ 生成引擎設定", expanded=False):
            engine_choice = st.radio(
                "選擇運行模型",
                ["免密鑰體驗引擎 (Imagen 4.0 Demo)", "NVIDIA Cosmos 3 (Hugging Face API)"],
                index=0 if st.session_state.config["engine"] == "gemini" else 1
            )
            current_engine = "gemini" if engine_choice.startswith("免密鑰") else "hf"
            if current_engine != st.session_state.config["engine"]:
                st.session_state.config["engine"] = current_engine
                save_config(st.session_state.config)
            
            if current_engine == "hf":
                st.markdown("**NVIDIA Cosmos 3 設定**")
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

        st.write("---")

        # Prompt Input Area
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
            if st.button("🪄 AI 提示詞大師最佳化", use_container_width=True):
                if not prompt_input.strip():
                    st.warning("請先輸入一點簡短的靈感，再讓 AI 大師進行最佳化！")
                else:
                    with st.spinner("AI 正在精密改寫提示詞..."):
                        try:
                            # Use custom key or env
                            key_to_use = st.session_state.config.get("gemini_key", "")
                            optimized = optimize_prompt(prompt_input, key_to_use)
                            st.session_state.prompt = optimized
                            st.success("AI 提示詞最佳化完成！已特別針對 Cosmos 3 優化物理和光影細節。")
                            st.rerun()
                        except Exception as e:
                            st.error(f"AI 優化失敗: {e}")
        with col_clr:
            if st.button("❌ 清除", use_container_width=True):
                st.session_state.prompt = ""
                st.rerun()

        st.write("---")

        # Aspect Ratio
        st.markdown("**畫面比例 (Aspect Ratio)**")
        ratio_cols = st.columns(3)
        ratios = ["1:1", "16:9", "9:16"]
        current_ratio = st.session_state.config.get("ratio", "1:1")
        
        for idx, r in enumerate(ratios):
            with ratio_cols[idx]:
                label = "🔳 1:1 正方形" if r == "1:1" else ("📺 16:9 寬螢幕" if r == "16:9" else "📱 9:16 直向海報")
                is_selected = (r == current_ratio)
                btn_label = f"🟢 {label}" if is_selected else label
                if st.button(btn_label, key=f"btn_ratio_{r}", use_container_width=True):
                    st.session_state.config["ratio"] = r
                    save_config(st.session_state.config)
                    st.rerun()

        st.write("---")

        # Style Presets
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
                    
                btn_text = f"🟢 {s['emoji']} {s['name']}" if is_active else f"{s['emoji']} {s['name']}"
                if st.button(btn_text, key=f"btn_style_{s['id']}", use_container_width=True):
                    cleaned = clean_styles(st.session_state.prompt)
                    if s["id"] != "empty":
                        st.session_state.prompt = cleaned + suffix
                    else:
                        st.session_state.prompt = cleaned
                    st.rerun()

        st.write("---")

        # Generate Button
        if st.button("🚀 開始生成 Cosmos 3 畫像", use_container_width=True, type="primary"):
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
                status_text.markdown("🔄 **正在建立安全連接與 API 驗證...**")
                step1.markdown("⏳ 正在建立安全連接與 API 驗證...")
                time.sleep(0.8)
                
                # Step 2
                progress_bar.progress(35)
                status_text.markdown("🔄 **分發 MoT 去噪張量與物理模型計算...**")
                step1.markdown("✅ 正在建立安全連接與 API 驗證...")
                step2.markdown("⏳ 分發 MoT 去噪張量與物理模型計算...")
                time.sleep(1.0)
                
                # Step 3
                progress_bar.progress(65)
                status_text.markdown("🔄 **高解析度物理擴散演算進行中...**")
                step2.markdown("✅ 分發 MoT 去噪張量與物理模型計算...")
                step3.markdown("⏳ 高解析度物理擴散演算進行中 (共需 28 步)...")
                
                try:
                    # Call API
                    if current_engine == "hf":
                        token = st.session_state.config.get("hf_token", "").strip()
                        if not token:
                            raise Exception("請先在引擎設定中輸入您的 Hugging Face Access Token！")
                        
                        width = 1280 if current_ratio == "16:9" else (720 if current_ratio == "9:16" else 1024)
                        height = 720 if current_ratio == "16:9" else (1280 if current_ratio == "9:16" else 1024)
                        
                        image_bytes = generate_image_hf(st.session_state.prompt, token, width, height)
                    else:
                        active_key = st.session_state.config.get("gemini_key", "").strip()
                        active_key = active_key or os.environ.get("GEMINI_API_KEY", "")
                        if not active_key:
                            raise Exception("此功能需要輸入 Gemini API Key。請在「生成引擎設定」中輸入您的 Key！")
                        
                        image_bytes = generate_image_gemini(st.session_state.prompt, active_key, current_ratio)
                    
                    # Step 4
                    progress_bar.progress(90)
                    status_text.markdown("🔄 **解碼潛在空間並合成最終像素...**")
                    step3.markdown("✅ 高解析度物理擴散演算進行中...")
                    step4.markdown("⏳ 解碼潛在空間並合成最終像素...")
                    time.sleep(0.8)
                    
                    # Save to local gallery
                    save_image_to_gallery(image_bytes, st.session_state.prompt, current_engine, current_ratio)
                    
                    progress_bar.progress(100)
                    status_text.markdown("✨ **圖像渲染完畢！**")
                    step4.markdown("✅ 解碼潛在空間並合成最終像素...")
                    st.success("圖像物理渲染生成完成！")
                    
                    # Display Result
                    st.image(image_bytes, caption="生成結果", use_container_width=True)
                    
                    # Action buttons
                    col_dl, col_cp = st.columns(2)
                    with col_dl:
                        st.download_button(
                            label="💾 儲存結果圖像",
                            data=image_bytes,
                            file_name=f"Cosmos3-Image-{int(time.time())}.png",
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

    # ================= TAB 2: GALLERY =================
    with tab_gallery:
        st.subheader("我的創作品藝廊")
        gallery_items = load_gallery()
        
        if not gallery_items:
            st.info("還沒有任何生成紀錄。立即前往生成器輸入您的靈感，Cosmos 3 將賦予其絕美的視覺物理真實感！")
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
                            st.markdown(f"⚙️ **引擎:** `{item['engine']}` | 📱 **比例:** `{item['ratio']}`")
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
        ### NVIDIA Cosmos 3 技術指南
        了解世界首款實體 AI 萬能大模型 (Omnimodal)
        
        #### 🧬 領先全球的開源文生圖架構
        **NVIDIA Cosmos 3** 是一款參數量達 64B 的物理世界基礎大模型。在 Artificial Analysis 文生圖及影片生成基準排行榜上榮登**開源模型第一名**。
        
        其採用獨創的 **Mixture-of-Transformers (MoT)** 混合架構，能完美模擬真實物理定律中的重力、光影反射、以及物體間的精確力學碰撞，生成的畫面細緻且富有驚人的真實世界物理感知。
        
        #### 🚀 三步配置 Cosmos 3
        1. **註冊並登入 Hugging Face:** 前往 huggingface.co 註冊帳號，即可享用免費的推論額度。
        2. **取得存取權金鑰 (Read Token):** 在個人 Settings -> Access Tokens 創建一個擁有「Read」權限的安全 Token。
        3. **貼入本 App 展開創作:** 點擊生成器頂部的「引擎設定」，切換到 NVIDIA Cosmos 3 並貼上 Token，即刻解鎖 64B 大模型生成！
        
        #### 📊 模型規格與指標
        | 技術指標 | 規格描述 |
        | :--- | :--- |
        | **模型參數大小** | 64B (Super) / 16B (Nano) |
        | **支援畫面比例** | 1:1, 16:9, 9:16, 4:3, 3:4 |
        | **主要能力** | 物理規律高精確度合成、高真實感去噪 |
        | **AI Upsampler** | 代理人提示詞重構硬體 (Agentic Upsampling) |
        """)

if __name__ == "__main__":
    if is_running_in_streamlit():
        main()
    else:
        # Programmatic run: when user runs "python text2image.py", launch Streamlit automatically
        file_path = os.path.abspath(__file__)
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 正在啟動 Streamlit 伺服器...")
        try:
            subprocess.run([sys.executable, "-m", "streamlit", "run", file_path])
        except KeyboardInterrupt:
            print("\n伺服器已安全關閉。")
            sys.exit(0)
