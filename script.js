// 預設與狀態管理
const apiKey = ""; // 執行環境會動態注入 Key，此處維持為空字串即可
let currentEngine = "gemini"; // 預設使用內建 Gemini 免設定生圖，可隨時手動切換至 hf
let currentRatio = "1:1";
let isGenerating = false;
let galleryItems = [];

// Supported Models Dictionary
const MODELS = {
  "imagen-4.0-generate-001": { name: "Google Imagen 4.0", provider: "gemini" },
  "imagen-3.0-generate-002": { name: "Google Imagen 3.0", provider: "gemini" },
  "imagen-3.0-fast-generate-002": { name: "Google Imagen 3.0 Fast", provider: "gemini" },
  "nvidia/Cosmos3-Super-Text2Image": { name: "NVIDIA Cosmos 3", provider: "hf" },
  "black-forest-labs/FLUX.1-schnell": { name: "FLUX.1 Schnell", provider: "hf" },
  "black-forest-labs/FLUX.1-dev": { name: "FLUX.1 Dev", provider: "hf" },
  "stabilityai/stable-diffusion-3.5-large": { name: "Stable Diffusion 3.5 Large", provider: "hf" },
  "stabilityai/stable-diffusion-xl-base-1.0": { name: "Stable Diffusion XL 1.0", provider: "hf" }
};

// 初始化載入
window.onload = function() {
  // 讀取本地保存的選定模型
  const savedModel = localStorage.getItem("selected_model") || "imagen-4.0-generate-001";
  const select = document.getElementById("model-select");
  if (select && MODELS[savedModel]) {
    select.value = savedModel;
  }

  // 讀取本地保存的 HF Token 
  const savedToken = localStorage.getItem("hf_cosmos_token");
  if (savedToken) {
    document.getElementById("hf-token-input").value = savedToken;
  }
  
  // 讀取本地保存的 Gemini API Key (自訂)
  const savedGeminiKey = localStorage.getItem("user_gemini_key");
  if (savedGeminiKey) {
    document.getElementById("gemini-key-input").value = savedGeminiKey;
  }

  handleModelChange();
  
  // 載入作品藝廊
  renderGallery();
};

// 提示框 Toast 控制
function showToast(message, type = 'info') {
  const toast = document.getElementById("toast-box");
  const text = document.getElementById("toast-text");
  const icon = document.getElementById("toast-icon");
  
  text.innerText = message;
  
  if (type === 'success') {
    icon.className = "fa-solid fa-circle-check text-nvidia-500";
  } else if (type === 'error') {
    icon.className = "fa-solid fa-triangle-exclamation text-red-500";
  } else if (type === 'warning') {
    icon.className = "fa-solid fa-circle-exclamation text-yellow-500";
  } else {
    icon.className = "fa-solid fa-circle-info text-nvidia-400";
  }

  toast.classList.remove("opacity-0", "pointer-events-none", "-translate-y-2");
  toast.classList.add("opacity-100", "translate-y-0");

  setTimeout(() => {
    toast.classList.remove("opacity-100", "translate-y-0");
    toast.classList.add("opacity-0", "pointer-events-none", "-translate-y-2");
  }, 4000);
}

// 切換設定面板折疊狀態
function toggleSettings() {
  const content = document.getElementById("settings-content");
  const chevron = document.getElementById("settings-chevron");
  
  if (content.classList.contains("hidden")) {
    content.classList.remove("hidden");
    chevron.style.transform = "rotate(180deg)";
  } else {
    content.classList.add("hidden");
    chevron.style.transform = "rotate(0deg)";
  }
}

// 下拉選單模型變更
function handleModelChange() {
  const select = document.getElementById("model-select");
  const modelVal = select.value;
  const modelInfo = MODELS[modelVal];
  
  currentEngine = modelInfo.provider;
  const tokenWrapper = document.getElementById("hf-token-wrapper");
  const badge = document.getElementById("current-mode-badge");
  
  if (currentEngine === "hf") {
    tokenWrapper.classList.remove("hidden");
    badge.innerText = `目前使用：Hugging Face - ${modelInfo.name}`;
  } else {
    tokenWrapper.classList.add("hidden");
    badge.innerText = `目前使用：Gemini Imagen - ${modelInfo.name}`;
  }
  
  localStorage.setItem("selected_model", modelVal);
}

// 密鑰可見性切換 (Hugging Face)
function toggleTokenVisibility() {
  const input = document.getElementById("hf-token-input");
  const icon = document.getElementById("token-eye-icon");
  if (input.type === "password") {
    input.type = "text";
    icon.className = "fa-solid fa-eye-slash text-xs";
  } else {
    input.type = "password";
    icon.className = "fa-solid fa-eye text-xs";
  }
}

// 密鑰可見性切換 (Gemini)
function toggleGeminiKeyVisibility() {
  const input = document.getElementById("gemini-key-input");
  const icon = document.getElementById("gemini-key-eye-icon");
  if (input.type === "password") {
    input.type = "text";
    icon.className = "fa-solid fa-eye-slash text-xs";
  } else {
    input.type = "password";
    icon.className = "fa-solid fa-eye text-xs";
  }
}

// 限制與更新字數計數
function updateCharCount() {
  const text = document.getElementById("prompt-textarea").value;
  const countSpan = document.getElementById("prompt-char-count");
  countSpan.innerText = `${text.length} / 500`;
}

function clearPrompt() {
  document.getElementById("prompt-textarea").value = "";
  updateCharCount();
  
  // 重設所有風格按鈕樣式
  document.querySelectorAll(".style-btn").forEach(btn => {
    if (btn.innerText.includes("無預設") || btn.innerHTML.includes("無預設") || btn.innerHTML.includes("❌")) {
      btn.className = "style-btn bg-slate-900 border border-slate-800 p-2.5 rounded-xl text-center active:scale-95 transition-all text-slate-500";
    } else {
      btn.className = "style-btn bg-cardBg border border-slate-800 hover:border-slate-700 p-2.5 rounded-xl text-center active:scale-95 transition-all text-slate-300";
    }
  });
}

// 畫面比例選擇切換
function selectRatio(ratio) {
  currentRatio = ratio;
  document.querySelectorAll(".ratio-btn").forEach(btn => {
    btn.className = "ratio-btn border border-slate-800 bg-slate-900 text-slate-400 py-3 rounded-xl flex flex-col items-center justify-center transition-all";
  });
  
  const activeBtn = document.getElementById(`ratio-${ratio.replace(':', '-')}`);
  if (activeBtn) {
    activeBtn.className = "ratio-btn border border-nvidia-500 bg-nvidia-500/10 text-nvidia-400 py-3 rounded-xl flex flex-col items-center justify-center transition-all";
  }
}

// 應用風格預設到 Prompt
function applyStyle(style, btnElement) {
  const textarea = document.getElementById("prompt-textarea");
  let originalText = textarea.value;

  const styleRegex = /,\s*(traditional Chinese painting|ink wash style|elegant|dynasty core|detailed watercolor brushstrokes|ultra cute|chibi|pastel colors|3D clay render|toy aesthetic|Studio Ghibli style|hand-drawn anime|lush green hills|nostalgic anime aesthetic|cyberpunk|futuristic city|photorealistic|hyperdetailed|anime illustration|vibrant colors|oil painting|robotic physical simulation|nvidia style|precise physics|watercolor painting).*/gi;
  originalText = originalText.replace(styleRegex, "");

  document.querySelectorAll(".style-btn").forEach(btn => {
    if (btn.innerText.includes("無預設") || btn.innerHTML.includes("無預設") || btn.innerHTML.includes("❌")) {
      btn.className = "style-btn bg-slate-900 border border-slate-800 p-2.5 rounded-xl text-center active:scale-95 transition-all text-slate-500";
    } else {
      btn.className = "style-btn bg-cardBg border border-slate-800 hover:border-slate-700 p-2.5 rounded-xl text-center active:scale-95 transition-all text-slate-300";
    }
  });

  if (btnElement) {
    if (style === 'empty') {
      btnElement.className = "style-btn bg-slate-900 border border-nvidia-500 text-nvidia-400 p-2.5 rounded-xl text-center active:scale-95 transition-all shadow-glow";
    } else {
      btnElement.className = "style-btn border border-nvidia-500 bg-nvidia-500/10 text-nvidia-400 p-2.5 rounded-xl text-center active:scale-95 transition-all shadow-glow";
    }
  }

  let styleSuffix = "";
  switch(style) {
    case 'chinese':
      styleSuffix = ", traditional Chinese painting, ink wash style, elegant, dynasty core, detailed watercolor brushstrokes";
      break;
    case 'cute':
      styleSuffix = ", ultra cute, chibi, pastel colors, 3D clay render, toy aesthetic, charming, soft lighting";
      break;
    case 'ghibli':
      styleSuffix = ", Studio Ghibli style, hand-drawn anime, lush green hills, soft nostalgic lighting, nostalgic anime aesthetic, masterpiece";
      break;
    case 'cyberpunk':
      styleSuffix = ", cyberpunk, futuristic city, neon glow, high-tech, unreal engine 5, 8k";
      break;
    case 'realistic':
      styleSuffix = ", photorealistic, hyperdetailed, 8k resolution, cinematic lighting, dslr camera, sharp focus";
      break;
    case 'anime':
      styleSuffix = ", anime illustration, beautiful hand-drawn art, vibrant colors, makoto shinkai style, high-res";
      break;
    case 'watercolor':
      styleSuffix = ", watercolor painting, artistic splatters, soft lighting, masterpiece, detailed texture";
      break;
    case 'physic-ai':
      styleSuffix = ", robotic physical simulation, precise physics, mechanical gears, metal textures, nvidia style, realistic raytracing";
      break;
    case 'empty':
    default:
      styleSuffix = "";
      break;
  }

  textarea.value = originalText + styleSuffix;
  updateCharCount();
  showToast(`已套用相關風格標籤！`, 'success');
}

// 底欄導航列切換
function switchTab(tabId) {
  document.getElementById("view-generator").classList.add("hidden");
  document.getElementById("view-gallery").classList.add("hidden");
  document.getElementById("view-info").classList.add("hidden");
  
  document.getElementById("nav-generator").className = "flex flex-col items-center gap-1 text-slate-500 hover:text-slate-300 transition-colors py-1 px-3";
  document.getElementById("nav-gallery").className = "flex flex-col items-center gap-1 text-slate-500 hover:text-slate-300 transition-colors py-1 px-3";
  document.getElementById("nav-info").className = "flex flex-col items-center gap-1 text-slate-500 hover:text-slate-300 transition-colors py-1 px-3";

  document.getElementById(`view-${tabId}`).classList.remove("hidden");
  document.getElementById(`nav-${tabId}`).className = "flex flex-col items-center gap-1 text-nvidia-400 transition-colors py-1 px-3";
}

// 指數退避重試請求封裝 (Exponential Backoff)
async function fetchWithRetry(url, options, maxRetries = 5) {
  let delay = 1000;
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return response;
      if (response.status === 429 || response.status >= 500) {
        await new Promise(resolve => setTimeout(resolve, delay));
        delay *= 2;
        continue;
      }
      return response;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, delay));
      delay *= 2;
    }
  }
}

// AI 提示詞大師最佳化 - 調用 Gemini-2.5-Flash
async function handlePromptUpsample() {
  const textarea = document.getElementById("prompt-textarea");
  const originalPrompt = textarea.value.trim();
  
  if (!originalPrompt) {
    showToast("請先輸入一點簡短的靈感，再讓 AI 大師進行最佳化！", "warning");
    return;
  }

  const upsampleBtn = document.getElementById("btn-upsample");
  const originalBtnHTML = upsampleBtn.innerHTML;
  
  upsampleBtn.disabled = true;
  upsampleBtn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i> <span>AI 正在精密改寫提示詞...</span>`;
  
  let activeGeminiKey = apiKey;
  const userGeminiKey = document.getElementById("gemini-key-input").value.trim();
  
  if (userGeminiKey) {
    activeGeminiKey = userGeminiKey;
    localStorage.setItem("user_gemini_key", userGeminiKey);
  } else {
    localStorage.removeItem("user_gemini_key");
  }

  if (!activeGeminiKey) {
    showToast("進行 AI 最佳化需要輸入 Gemini API Key！請先在引擎設定中輸入您的 Key。", "error");
    const settingsContent = document.getElementById("settings-content");
    if (settingsContent.classList.contains("hidden")) {
      toggleSettings();
    }
    upsampleBtn.disabled = false;
    upsampleBtn.innerHTML = originalBtnHTML;
    return;
  }

  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${activeGeminiKey}`;
    
    const payload = {
      contents: [{
        parts: [{ text: originalPrompt }]
      }],
      systemInstruction: {
        parts: [{
          text: "You are an expert prompt engineer for advanced image diffusion models. Rewrite and significantly expand the user prompt into a highly detailed, visually stunning, and physically realistic English prompt. Describe camera perspective, lighting, textures, materials, and composition details. Do not include introductory words or titles. Do not output markdown, just output the raw prompt in English."
        }]
      }
    };

    const response = await fetchWithRetry(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errDetail = await response.text();
      let parsedError;
      try {
        parsedError = JSON.parse(errDetail);
      } catch(e) {}
      const errorMsg = parsedError?.error?.message || errDetail || "未知伺服器錯誤";
      throw new Error(`API 連線失敗 (${response.status})：${errorMsg}`);
    }

    const data = await response.json();
    const optimizedText = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
    
    if (optimizedText) {
      textarea.value = optimizedText;
      updateCharCount();
      showToast("AI 提示詞最佳化完成！已特別優化物理和光影細節。", "success");
    } else {
      showToast("AI 傳回了空白優化，已維持原提示詞。", "warning");
    }
  } catch (err) {
    console.error("Gemini Error: ", err);
    showToast(`AI 優化失敗：${err.message}`, "error");
    
    const settingsContent = document.getElementById("settings-content");
    if (settingsContent.classList.contains("hidden")) {
      toggleSettings();
    }
  } finally {
    upsampleBtn.disabled = false;
    upsampleBtn.innerHTML = originalBtnHTML;
  }
}

// 開始影像生成主控制流
async function triggerGenerate() {
  const textarea = document.getElementById("prompt-textarea");
  const prompt = textarea.value.trim();

  if (!prompt) {
    showToast("請輸入生圖提示詞 (Prompt)！", "warning");
    return;
  }

  if (isGenerating) return;
  isGenerating = true;

  const select = document.getElementById("model-select");
  const currentModel = select.value;
  const modelInfo = MODELS[currentModel];
  const modelDisplayName = modelInfo.name;

  // 介面鎖定
  document.getElementById("btn-generate").disabled = true;
  document.getElementById("btn-generate").innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i> 生成處理中...`;
  
  const loaderPanel = document.getElementById("loader-panel");
  const resultPanel = document.getElementById("result-panel");
  
  loaderPanel.classList.remove("hidden");
  resultPanel.classList.add("hidden");

  // 進度重設與模擬跑條
  updateLoader(10, "正在連線到安全生成網關...");
  document.getElementById("step-1").className = "flex items-center gap-2.5 text-xs text-nvidia-400 font-medium";
  document.getElementById("step-1").querySelector("i").className = "fa-solid fa-spinner animate-spin text-nvidia-400 text-[10px]";
  
  document.getElementById("step-2").className = "flex items-center gap-2.5 text-xs text-slate-500";
  document.getElementById("step-2").querySelector("i").className = "fa-solid fa-circle-dot text-[8px]";
  
  document.getElementById("step-3").className = "flex items-center gap-2.5 text-xs text-slate-500";
  document.getElementById("step-3").querySelector("i").className = "fa-solid fa-circle-dot text-[8px]";
  
  document.getElementById("step-4").className = "flex items-center gap-2.5 text-xs text-slate-500";
  document.getElementById("step-4").querySelector("i").className = "fa-solid fa-circle-dot text-[8px]";

  let progressInterval = setInterval(() => {
    const percentElement = document.getElementById("loader-percent");
    let cur = parseInt(percentElement.innerText);
    if (cur < 90) {
      let step = Math.floor(Math.random() * 8) + 4;
      let nextPercent = Math.min(90, cur + step);
      
      if (nextPercent > 25 && nextPercent <= 50) {
        updateLoader(nextPercent, "分發模型權重與物理張量計算...");
        document.getElementById("step-1").className = "flex items-center gap-2.5 text-xs text-slate-400";
        document.getElementById("step-1").querySelector("i").className = "fa-solid fa-circle-check text-nvidia-500 text-[10px]";
        
        document.getElementById("step-2").className = "flex items-center gap-2.5 text-xs text-nvidia-400 font-medium";
        document.getElementById("step-2").querySelector("i").className = "fa-solid fa-spinner animate-spin text-nvidia-400 text-[10px]";
      } else if (nextPercent > 50 && nextPercent <= 80) {
        updateLoader(nextPercent, "高解析度去噪擴散演算進行中...");
        document.getElementById("step-2").className = "flex items-center gap-2.5 text-xs text-slate-400";
        document.getElementById("step-2").querySelector("i").className = "fa-solid fa-circle-check text-nvidia-500 text-[10px]";
        
        document.getElementById("step-3").className = "flex items-center gap-2.5 text-xs text-nvidia-400 font-medium";
        document.getElementById("step-3").querySelector("i").className = "fa-solid fa-spinner animate-spin text-nvidia-400 text-[10px]";
      } else if (nextPercent > 80) {
        updateLoader(nextPercent, "解碼潛在空間並合成最終像素...");
        document.getElementById("step-3").className = "flex items-center gap-2.5 text-xs text-slate-400";
        document.getElementById("step-3").querySelector("i").className = "fa-solid fa-circle-check text-nvidia-500 text-[10px]";
        
        document.getElementById("step-4").className = "flex items-center gap-2.5 text-xs text-nvidia-400 font-medium";
        document.getElementById("step-4").querySelector("i").className = "fa-solid fa-spinner animate-spin text-nvidia-400 text-[10px]";
      } else {
        updateLoader(nextPercent);
      }
    }
  }, 900);

  try {
    let imageUrl = "";
    
    if (currentEngine === "hf") {
      const tokenInput = document.getElementById("hf-token-input").value.trim();
      if (!tokenInput) {
        toggleSettings();
        throw new Error("請先在引擎設定中輸入您的 Hugging Face Access Token！");
      }
      
      localStorage.setItem("hf_cosmos_token", tokenInput);
      
      const hfUrl = `https://api-inference.huggingface.co/models/${currentModel}`;
      const response = await fetchWithRetry(hfUrl, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${tokenInput}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ 
          inputs: prompt,
          parameters: {
            width: currentRatio === "16:9" ? 1280 : (currentRatio === "9:16" ? 720 : 1024),
            height: currentRatio === "16:9" ? 720 : (currentRatio === "9:16" ? 1280 : 1024)
          }
        })
      });

      if (!response.ok) {
        const errDetail = await response.text();
        if (response.status === 503) {
          throw new Error("模型正在 Hugging Face 後端熱機啟動中，請等待 10~20 秒後再次嘗試！");
        }
        throw new Error(`HF 端回傳錯誤 (${response.status})：${errDetail || '請確認 Token 是否正確與模型權限。'}`);
      }

      const blob = await response.blob();
      imageUrl = URL.createObjectURL(blob);
      
    } else {
      let activeGeminiKey = apiKey;
      const userGeminiKey = document.getElementById("gemini-key-input").value.trim();
      if (userGeminiKey) {
        activeGeminiKey = userGeminiKey;
        localStorage.setItem("user_gemini_key", userGeminiKey);
      } else {
        localStorage.removeItem("user_gemini_key");
      }

      if (!activeGeminiKey) {
        toggleSettings();
        throw new Error("此模型需要輸入 Gemini API Key！請先在「生成引擎與模型設定」中貼上您的 Key。");
      }

      const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${currentModel}:predict?key=${activeGeminiKey}`;
      const payload = {
        bytes: true, // Some environments might require this, otherwise predict endpoint structure:
        instances: [
          { prompt: prompt }
        ],
        parameters: {
          sampleCount: 1,
          aspectRatio: currentRatio
        }
      };

      const response = await fetchWithRetry(geminiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errDetail = await response.text();
        let parsedError;
        try { parsedError = JSON.parse(errDetail); } catch(e) {}
        const errorMsg = parsedError?.error?.message || errDetail || "未知連線錯誤";
        throw new Error(`Gemini 預覽引擎回報錯誤 (${response.status})：${errorMsg}`);
      }

      const resultData = await response.json();
      const b64Bytes = resultData.predictions?.[0]?.bytesBase64Encoded;
      if (!b64Bytes) {
        throw new Error("未能成功獲取圖像字節流。");
      }

      imageUrl = `data:image/png;base64,${b64Bytes}`;
    }

    // 生成結束
    clearInterval(progressInterval);
    updateLoader(100, "圖像渲染完畢！");
    document.getElementById("step-4").className = "flex items-center gap-2.5 text-xs text-slate-400";
    document.getElementById("step-4").querySelector("i").className = "fa-solid fa-circle-check text-nvidia-500 text-[10px]";

    // 更新結果卡片
    const resultImg = document.getElementById("result-image");
    resultImg.src = imageUrl;
    document.getElementById("result-prompt").innerText = prompt;
    
    const engineBadge = document.getElementById("result-engine-badge");
    engineBadge.innerText = modelDisplayName;
    if (currentEngine === "hf") {
      engineBadge.className = "text-[9px] bg-nvidia-950 border border-nvidia-800 text-nvidia-400 px-2 py-0.5 rounded";
    } else {
      engineBadge.className = "text-[9px] bg-indigo-950 border border-indigo-800 text-indigo-300 px-2 py-0.5 rounded";
    }

    setTimeout(() => {
      loaderPanel.classList.add("hidden");
      resultPanel.classList.remove("hidden");
      resultPanel.scrollIntoView({ behavior: 'smooth' });
      
      addToGallery(imageUrl, prompt, currentModel);
      showToast("圖像物理渲染生成完成！", "success");
    }, 600);

  } catch (error) {
    clearInterval(progressInterval);
    loaderPanel.classList.add("hidden");
    showToast(error.message || "發生未知錯誤，請檢察網路與 Token 配置。", "error");
  } finally {
    isGenerating = false;
    document.getElementById("btn-generate").disabled = false;
    document.getElementById("btn-generate").innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-base"></i><span>開始進行 AI 畫像生成</span>`;
  }
}

// 控制生圖進度條更新
function updateLoader(percent, text) {
  document.getElementById("loader-percent").innerText = `${percent}%`;
  document.getElementById("loader-bar").style.width = `${percent}%`;
}

// 將產出的圖像加入藝廊紀錄中
function addToGallery(imgUrl, promptStr, modelKey) {
  const item = {
    id: Date.now(),
    url: imgUrl,
    prompt: promptStr,
    engine: MODELS[modelKey]?.name || modelKey,
    ratio: currentRatio,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  };
  
  galleryItems.unshift(item);
  renderGallery();
}

// 重新繪製藝廊
function renderGallery() {
  const grid = document.getElementById("gallery-grid");
  const emptyState = document.getElementById("gallery-empty");
  const badge = document.getElementById("gallery-badge");

  if (galleryItems.length === 0) {
    grid.classList.add("hidden");
    emptyState.classList.remove("hidden");
    badge.classList.add("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  grid.classList.remove("hidden");
  
  badge.classList.remove("hidden");
  badge.innerText = galleryItems.length;

  grid.innerHTML = "";
  galleryItems.forEach(item => {
    const div = document.createElement("div");
    div.className = "bg-cardBg border border-slate-800 rounded-xl overflow-hidden shadow flex flex-col justify-between";
    div.innerHTML = `
      <div class="relative bg-slate-950 aspect-square overflow-hidden flex items-center justify-center">
        <img src="${item.url}" alt="創作品" class="w-full h-full object-cover" />
        <span class="absolute top-2 left-2 text-[8px] bg-darkBg/80 backdrop-blur text-slate-300 border border-slate-700 px-1.5 py-0.5 rounded">
          ${item.ratio}
        </span>
        <span class="absolute bottom-2 right-2 text-[8px] bg-nvidia-950/90 text-nvidia-300 font-semibold px-1.5 py-0.5 rounded">
          ${item.engine}
        </span>
      </div>
      <div class="p-2.5 space-y-1.5 flex-1 flex flex-col justify-between">
        <p class="text-[10px] text-slate-300 line-clamp-2 select-text font-normal leading-relaxed">${item.prompt}</p>
        <div class="flex items-center justify-between text-[8px] text-slate-500 border-t border-slate-800/80 pt-1.5 mt-auto">
          <span>${item.time}</span>
          <div class="flex gap-2">
            <button onclick="reusePrompt('${item.prompt.replace(/'/g, "\\'")}')" class="text-nvidia-400 hover:text-nvidia-300" title="重複使用提示詞">
              <i class="fa-solid fa-arrow-rotate-left"></i>
            </button>
            <button onclick="downloadDirectly('${item.url}')" class="text-slate-400 hover:text-white" title="儲存檔案">
              <i class="fa-solid fa-download"></i>
            </button>
          </div>
        </div>
      </div>
    `;
    grid.appendChild(div);
  });
}

// 重用提示詞
function reusePrompt(promptStr) {
  document.getElementById("prompt-textarea").value = promptStr;
  updateCharCount();
  switchTab('generator');
  showToast("已將藝廊提示詞帶入輸入框！", "success");
}

// 清空藝廊
function clearAllGallery() {
  if (galleryItems.length === 0) return;
  galleryItems = [];
  renderGallery();
  showToast("藝廊紀錄已成功清空。", "info");
}

// 下載結果圖片 (支援 iframe 限制下的下載)
function downloadResult() {
  const img = document.getElementById("result-image");
  if (!img.src) return;
  downloadDirectly(img.src);
}

// 下載動作
function downloadDirectly(url) {
  const a = document.createElement("a");
  a.href = url;
  a.download = `AIStudio-Image-${Date.now()}.png`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showToast("已開始下載，請檢查您的系統儲存檔案！", "success");
}

// 複製提示詞
function copyGeneratedPrompt() {
  const promptText = document.getElementById("result-prompt").innerText;
  if (!promptText) return;
  
  const tempTextarea = document.createElement("textarea");
  tempTextarea.value = promptText;
  tempTextarea.style.position = "fixed";
  tempTextarea.style.opacity = "0";
  document.body.appendChild(tempTextarea);
  tempTextarea.select();
  
  try {
    const successful = document.execCommand('copy');
    if (successful) {
      showToast("完整提示詞複製成功！", "success");
    } else {
      showToast("複製失敗，請手動選擇複製。", "error");
    }
  } catch (err) {
    showToast("裝置不支援快捷複製。", "error");
  }
  
  document.body.removeChild(tempTextarea);
}
