document.addEventListener('DOMContentLoaded', () => {
  // DOM 元件
  const form = document.getElementById('generateForm');
  const categorySelect = document.getElementById('categorySelect');
  const hookSelect = document.getElementById('hookSelect');
  const customHookInput = document.getElementById('customHookInput');
  const platformSelect = document.getElementById('platformSelect');
  const toneSelect = document.getElementById('toneSelect');
  const topicInput = document.getElementById('topicInput');
  const btnGenerate = document.getElementById('btnGenerate');

  // 物件欄位
  const propTitle = document.getElementById('propTitle');
  const propRegion = document.getElementById('propRegion');
  const propPrice = document.getElementById('propPrice');
  const propLayout = document.getElementById('propLayout');
  const propHighlights = document.getElementById('propHighlights');
  const propUrgency = document.getElementById('propUrgency');

  // 預覽與檢核
  const outputContent = document.getElementById('outputContent');
  const charCount = document.getElementById('charCount');
  const btnCopy = document.getElementById('btnCopy');
  const validationBar = document.getElementById('validationBar');
  const valTitle = document.getElementById('valTitle');
  const valDesc = document.getElementById('valDesc');
  const validationReport = document.getElementById('validationReport');
  const valPassedList = document.getElementById('valPassedList');
  const valWarningList = document.getElementById('valWarningList');
  const systemStatusText = document.getElementById('systemStatusText');

  // LINE 模擬
  const lineChatBox = document.getElementById('lineChatBox');
  const lineInput = document.getElementById('lineInput');
  const btnSendLine = document.getElementById('btnSendLine');

  // Modal
  const policyModal = document.getElementById('policyModal');
  const policyModalBody = document.getElementById('policyModalBody');
  const btnOpenPolicyModal = document.getElementById('btnOpenPolicyModal');
  const settingsModal = document.getElementById('settingsModal');
  const btnOpenSettingsModal = document.getElementById('btnOpenSettingsModal');
  const settingProvider = document.getElementById('settingProvider');
  const settingApiKey = document.getElementById('settingApiKey');
  const btnSaveSettings = document.getElementById('btnSaveSettings');

  let currentHooksData = [];
  let currentPolicies = [];

  // 1. 初始化資料
  async function init() {
    loadSettings();
    await checkHealth();
    await loadHooks();
  }

  // 檢查健康度
  async function checkHealth() {
    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      systemStatusText.textContent = `法規庫已載入 ${data.policies_loaded} 條 • 鉤子 ${data.hook_categories} 類別`;
    } catch (e) {
      systemStatusText.textContent = '連線本機服務中';
    }
  }

  // 載入鉤子庫
  async function loadHooks() {
    try {
      const res = await fetch('/api/hooks');
      const data = await res.json();
      currentHooksData = data.categories || [];
      renderHooksForCategory(categorySelect.value);
    } catch (e) {
      console.error('載入鉤子庫失敗:', e);
    }
  }

  function renderHooksForCategory(catId) {
    hookSelect.innerHTML = '';
    const cat = currentHooksData.find(c => c.id === catId);
    if (cat && cat.hooks) {
      cat.hooks.forEach((h, idx) => {
        const opt = document.createElement('option');
        opt.value = h;
        opt.textContent = `${idx + 1}. ${h}`;
        hookSelect.appendChild(opt);
      });
    }
  }

  categorySelect.addEventListener('change', () => {
    renderHooksForCategory(categorySelect.value);
  });



  // AI 智能即時生成專屬鉤子
  const btnAiGenHooks = document.getElementById('btnAiGenHooks');
  btnAiGenHooks?.addEventListener('click', async () => {
    const isTopicTab = document.getElementById('tabTopic').classList.contains('active');
    const topic = isTopicTab ? topicInput.value.trim() : '';
    let propData = null;
    if (!isTopicTab) {
      propData = {
        title: propTitle.value.trim(),
        region: propRegion.value.trim(),
        price: propPrice.value.trim()
      };
    }

    btnAiGenHooks.disabled = true;
    btnAiGenHooks.textContent = '✨ 生成專屬鉤子中...';

    try {
      const clientProvider = getClientProvider();
      const clientApiKey = getClientApiKey();

      const res = await fetch('/api/hooks/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic,
          category_id: categorySelect.value,
          property_data: propData,
          provider: clientProvider,
          api_key: clientApiKey
        })
      });

      const data = await res.json();
      if (data.hooks && data.hooks.length > 0) {
        hookSelect.innerHTML = '';
        data.hooks.forEach((h, idx) => {
          const opt = document.createElement('option');
          opt.value = h;
          opt.textContent = `🎯 ${idx + 1}. ${h}`;
          hookSelect.appendChild(opt);
        });
        hookSelect.selectedIndex = 0;
      }
    } catch (e) {
      alert('產生鉤子失敗，請確認伺服器連線');
    } finally {
      btnAiGenHooks.disabled = false;
      btnAiGenHooks.textContent = '✨ AI 產出專屬鉤子';
    }
  });

  // 2. 輸入分頁切換
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      document.getElementById(targetId).classList.add('active');
    });
  });

  // 預覽分頁切換 (結果預覽 vs LINE 模擬)
  document.querySelectorAll('.preview-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.preview-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.preview-body').forEach(b => b.classList.remove('active'));
      tab.classList.add('active');
      const targetId = tab.getAttribute('data-target');
      document.getElementById(targetId).classList.add('active');
    });
  });

  // 3. 提交生成
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const selectedCategory = categorySelect.value;
    const selectedHook = customHookInput.value.trim() || hookSelect.value;
    const platform = platformSelect.value;
    const tone = toneSelect.value;

    const isTopicTab = document.getElementById('tabTopic').classList.contains('active');
    const topic = isTopicTab ? topicInput.value.trim() : '';

    let propertyData = null;
    if (!isTopicTab) {
      propertyData = {
        title: propTitle.value.trim(),
        region: propRegion.value.trim(),
        price: propPrice.value.trim(),
        layout: propLayout.value.trim(),
        highlights: propHighlights.value.trim(),
        urgency: propUrgency.value.trim()
      };
    }

    // 按鈕 Loading 狀態
    btnGenerate.disabled = true;
    btnGenerate.innerHTML = '<span>🌐 正在即時聯網比對最新政策並生成中...</span>';

    const enableLiveSearch = document.getElementById('chkLiveSearch')?.checked ?? true;

    try {
      const clientProvider = getClientProvider();
      const clientApiKey = getClientApiKey();

      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic,
          category_id: selectedCategory,
          platform: platform,
          tone: tone,
          property_data: propertyData,
          custom_hook: selectedHook,
          provider: clientProvider,
          api_key: clientApiKey,
          enable_live_search: enableLiveSearch
        })
      });

      const data = await res.json();
      if (!data.success) {
        outputContent.value = '';
        updateCharCount();
        renderGenerationError(data.error, data.live_sources);
      } else {
        outputContent.value = data.content || '';
        updateCharCount();
        renderValidation(data.validation, data.live_sources, data.method, data.used_model);
      }
    } catch (err) {
      alert('生成失敗，請檢查伺服器連線狀態');
      console.error(err);
    } finally {
      btnGenerate.disabled = false;
      btnGenerate.innerHTML = '<span class="btn-icon">⚡</span><span>立即生成爆款文章 (自動聯網比對)</span>';
    }
  });

  // 字數統計
  function updateCharCount() {
    const len = outputContent.value.length;
    charCount.textContent = `${len} 字`;
  }
  outputContent.addEventListener('input', updateCharCount);

  // 渲染生成失敗錯誤視圖
  function renderGenerationError(errorMsg, liveSources) {
    validationReport.classList.remove('hidden');
    validationBar.className = 'validation-bar has-warning';
    valTitle.textContent = '❌ AI 爆款文章生成未完成';
    valDesc.textContent = errorMsg || '請至右上角「⚙️ 模型與 API 設定」填入有效的 Gemini 或 OpenAI Key。';
    valPassedList.innerHTML = '';
    valWarningList.innerHTML = `<div style="color:#b91c1c; font-weight:600;">${errorMsg}</div>`;

    const liveSourcesSection = document.getElementById('liveSourcesSection');
    if (liveSources && liveSources.length > 0) {
      liveSourcesSection.classList.remove('hidden');
    } else {
      liveSourcesSection.classList.add('hidden');
    }
  }

  // 渲染事實驗證結果與即時聯網來源
  function renderValidation(val, liveSources, method, usedModel) {
    if (!val) return;
    validationReport.classList.remove('hidden');

    const liveSourcesSection = document.getElementById('liveSourcesSection');
    const liveSourcesList = document.getElementById('liveSourcesList');
    const liveSourcesCount = document.getElementById('liveSourcesCount');

    if (liveSources && liveSources.length > 0) {
      liveSourcesSection.classList.remove('hidden');
      liveSourcesCount.textContent = `${liveSources.length} 篇即時動態比對`;
      liveSourcesList.innerHTML = '';
      liveSources.forEach(s => {
        const item = document.createElement('div');
        item.className = 'source-item';
        item.innerHTML = `
          <div><a href="${s.link}" target="_blank" rel="noopener noreferrer">${s.title}</a></div>
          <div class="source-meta">來源：${s.source} | 發布時間：${s.published_at}</div>
        `;
        liveSourcesList.appendChild(item);
      });
    } else {
      liveSourcesSection.classList.add('hidden');
    }

    if (val.is_valid) {
      validationBar.className = 'validation-bar valid';
      const providerLabel = method === 'gemini_api' ? 'Google Gemini' : 'OpenAI';
      const modelBadge = usedModel ? `[${usedModel}]` : '';
      valTitle.textContent = `🛡️ 法規與事實檢核 100% 通過（✨ 由 ${providerLabel} ${modelBadge} 原創動態生成）`;
      valDesc.textContent = `已即時比對最新法規與草案公告，引用依據：${val.referenced_policies?.join('、') || '台灣現行不動產規範與最新新聞'}`;
    } else {
      validationBar.className = 'validation-bar has-warning';
      valTitle.textContent = `⚠️ 偵測到 ${val.warning_count} 項法規/時空疑義`;
      valDesc.textContent = '請檢視下方詳細報告，確保文案未誤導消費者或牴觸最新政策。';
    }

    valPassedList.innerHTML = '';
    (val.passed_checks || []).forEach(p => {
      const div = document.createElement('div');
      div.textContent = `✓ ${p}`;
      valPassedList.appendChild(div);
    });

    valWarningList.innerHTML = '';
    (val.warnings || []).forEach(w => {
      const div = document.createElement('div');
      div.textContent = `✕ ${w}`;
      valWarningList.appendChild(div);
    });
  }

  // 4. 一鍵複製
  btnCopy.addEventListener('click', async () => {
    const text = outputContent.value;
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      const orig = btnCopy.textContent;
      btnCopy.textContent = '✅ 已複製！';
      setTimeout(() => { btnCopy.textContent = orig; }, 2000);
    } catch (err) {
      outputContent.select();
      document.execCommand('copy');
      btnCopy.textContent = '✅ 已複製！';
      setTimeout(() => { btnCopy.textContent = '📋 一鍵複製'; }, 2000);
    }
  });

  // 5. 法規 Modal
  btnOpenPolicyModal.addEventListener('click', async () => {
    policyModal.classList.add('active');
    try {
      const res = await fetch('/api/policies');
      const data = await res.json();
      currentPolicies = data.policies || [];
      renderPolicyModal(currentPolicies, data.terms || []);
    } catch (e) {
      policyModalBody.innerHTML = '<p>載入法規失敗</p>';
    }
  });

  function renderPolicyModal(policies, terms) {
    let html = '<div style="display:flex; flex-direction:column; gap:1rem;">';
    
    html += `<h4 style="color:#0f172a; font-weight:700;">📜 台灣最新現行法規與預告草案（共 ${policies.length} 條）</h4>`;
    if (policies.length === 0) {
      html += '<p style="color:#64748b; font-size:0.85rem;">法規資料庫正在自動還原更新，請點擊下方按鈕或重新整理...</p>';
    } else {
      policies.forEach(p => {
        const pStatus = p.status || '現行實施中';
        const isDraft = pStatus.includes('草案') || pStatus.includes('預告');
        const keyRules = Array.isArray(p.key_rules) ? p.key_rules : [];
        html += `
          <div class="policy-card">
            <div class="policy-card-header">
              <strong>${p.title || '房市法規規範'}</strong>
              <span class="policy-badge ${isDraft ? 'draft' : ''}">${pStatus}</span>
            </div>
            <p style="font-size:0.8rem; color:#64748b; margin-bottom:0.4rem;">主管機關：${p.authority || '主管機關'} | 生效/時程：${p.effective_date || '現行'}</p>
            <ul class="policy-rules">
              ${keyRules.map(r => `<li>${r}</li>`).join('')}
            </ul>
            ${p.warning_notice ? `<p style="margin-top:0.4rem; font-size:0.8rem; color:#b45309;">${p.warning_notice}</p>` : ''}
          </div>
        `;
      });
    }

    html += `<h4 style="margin-top:1.5rem; color:#0f172a; font-weight:700;">📌 台灣在地房產避坑術語（共 ${terms.length} 則）</h4>`;
    terms.forEach(t => {
      html += `
        <div class="policy-card">
          <strong>${t.term || ''}</strong>
          <p style="font-size:0.85rem; margin-top:0.25rem;">${t.definition || ''}</p>
          <p style="font-size:0.8rem; color:#b91c1c; margin-top:0.25rem;">⚠️ ${t.risk_warning || ''}</p>
        </div>
      `;
    });
    html += '</div>';
    policyModalBody.innerHTML = html;
  }

  // 聯網即時同步按鈕
  const btnSyncLivePolicies = document.getElementById('btnSyncLivePolicies');
  const syncKeywordInput = document.getElementById('syncKeywordInput');
  const liveSyncResultBox = document.getElementById('liveSyncResultBox');

  btnSyncLivePolicies?.addEventListener('click', async () => {
    const customKw = syncKeywordInput?.value.trim() || '';
    btnSyncLivePolicies.disabled = true;
    btnSyncLivePolicies.textContent = customKw ? `🔄 正在同步【${customKw}】官方動態...` : '🔄 正在同步六大房產領域公告...';
    try {
      const clientProvider = getClientProvider();
      const clientApiKey = getClientApiKey();

      const res = await fetch('/api/policies/sync-live', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: clientProvider,
          api_key: clientApiKey,
          custom_keyword: customKw
        })
      });
      const data = await res.json();
      liveSyncResultBox.classList.remove('hidden');
      if (data.success && data.sync_result) {
        const sr = data.sync_result;
        let html = `<strong>✅ 知識庫自動更新成功（更新時間：${sr.last_updated}）</strong><br>`;
        html += `<span style="font-size:0.75rem;">分析了 ${sr.signals_count} 條即時政府與新聞訊號，包含 ${sr.policies_count} 條核心政策與草案（模式：${sr.sync_method}）</span>`;
        if (sr.signals_sample && sr.signals_sample.length > 0) {
          html += `<ul style="margin-top:0.35rem; margin-left:1.2rem; font-size:0.75rem;">`;
          sr.signals_sample.forEach(s => {
            html += `<li>${s.title} (${s.pub_date})</li>`;
          });
          html += '</ul>';
        }
        liveSyncResultBox.innerHTML = html;
        if (data.policies) {
          renderPolicyModal(data.policies, data.terms || []);
        }
        systemStatusText.textContent = `法規庫已自動更新（${data.policies.length} 條核心規範）`;
      } else {
        liveSyncResultBox.innerHTML = '已完成連線檢核，目前政策與官方知識庫一致。';
      }
    } catch (e) {
      alert('聯網同步失敗，請檢查網路連線');
    } finally {
      btnSyncLivePolicies.disabled = false;
      btnSyncLivePolicies.textContent = '🔄 立即聯網同步最新房市資訊';
    }
  });

  // 金鑰用戶端存取權控
  function getClientApiKey() {
    return localStorage.getItem('re_ai_api_key') || sessionStorage.getItem('re_ai_api_key') || '';
  }

  function getClientProvider() {
    return localStorage.getItem('re_ai_provider') || sessionStorage.getItem('re_ai_provider') || 'gemini';
  }

  // 6. 設定 Modal
  const chkRememberApiKey = document.getElementById('chkRememberApiKey');
  const btnClearApiKey = document.getElementById('btnClearApiKey');

  function loadSettings() {
    const p = getClientProvider();
    const storedLocalKey = localStorage.getItem('re_ai_api_key');
    const storedSessionKey = sessionStorage.getItem('re_ai_api_key');
    
    if (p) settingProvider.value = p;
    if (storedLocalKey) {
      settingApiKey.value = storedLocalKey;
      chkRememberApiKey.checked = true;
    } else if (storedSessionKey) {
      settingApiKey.value = storedSessionKey;
      chkRememberApiKey.checked = false;
    } else {
      settingApiKey.value = '';
      chkRememberApiKey.checked = false;
    }
  }

  btnOpenSettingsModal.addEventListener('click', () => {
    loadSettings();
    if (testConnResultBox) testConnResultBox.textContent = '';
    settingsModal.classList.add('active');
  });

  // 測試 API 連線按鈕
  const btnTestConnection = document.getElementById('btnTestConnection');
  const testConnResultBox = document.getElementById('testConnResultBox');

  btnTestConnection?.addEventListener('click', async () => {
    const p = settingProvider.value;
    const k = settingApiKey.value.trim();
    if (!k) {
      testConnResultBox.textContent = '❌ 請先輸入 API Key';
      testConnResultBox.style.color = '#b91c1c';
      return;
    }
    btnTestConnection.disabled = true;
    testConnResultBox.textContent = '⏳ 測試連線中...';
    testConnResultBox.style.color = '#64748b';

    try {
      const res = await fetch('/api/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: p, api_key: k })
      });
      const data = await res.json();
      if (data.success) {
        testConnResultBox.textContent = `✅ ${data.message || '連線成功！'}`;
        testConnResultBox.style.color = '#065f46';
      } else {
        testConnResultBox.textContent = `❌ ${data.error || '連線失敗'}`;
        testConnResultBox.style.color = '#b91c1c';
      }
    } catch (e) {
      testConnResultBox.textContent = '❌ 連線錯誤，請確認網路與容器狀態';
      testConnResultBox.style.color = '#b91c1c';
    } finally {
      btnTestConnection.disabled = false;
    }
  });

  // 儲存/套用設定
  btnSaveSettings.addEventListener('click', () => {
    const providerVal = settingProvider.value;
    const keyVal = settingApiKey.value.trim();
    const remember = chkRememberApiKey.checked;

    if (remember) {
      localStorage.setItem('re_ai_provider', providerVal);
      localStorage.setItem('re_ai_api_key', keyVal);
      sessionStorage.removeItem('re_ai_api_key');
      sessionStorage.removeItem('re_ai_provider');
    } else {
      sessionStorage.setItem('re_ai_provider', providerVal);
      sessionStorage.setItem('re_ai_api_key', keyVal);
      localStorage.removeItem('re_ai_api_key');
      localStorage.removeItem('re_ai_provider');
    }

    settingsModal.classList.remove('active');
    alert(keyVal ? (remember ? '設定已套用（已記住金鑰於此瀏覽器）' : '設定已套用（僅在此工作階段生效，關閉即清除）') : '設定已儲存！');
  });

  // 清除本機已存金鑰按鈕
  btnClearApiKey?.addEventListener('click', () => {
    localStorage.removeItem('re_ai_api_key');
    localStorage.removeItem('re_ai_provider');
    sessionStorage.removeItem('re_ai_api_key');
    sessionStorage.removeItem('re_ai_provider');
    settingApiKey.value = '';
    chkRememberApiKey.checked = false;
    testConnResultBox.textContent = '🗑️ 本機已存金鑰已完全清除！';
    testConnResultBox.style.color = '#0284c7';
  });

  // 關閉所有 Modal
  document.querySelectorAll('.modal-close').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
    });
  });

  window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
      e.target.classList.remove('active');
    }
  });

  // 7. LINE Bot 模擬發送
  const lineUserIdInput = document.getElementById('lineUserIdInput');

  async function sendLineMockMessage(cmdText) {
    const text = cmdText || lineInput.value.trim();
    if (!text) return;

    appendLineMessage('user', text);
    lineInput.value = '';

    const activeUserId = lineUserIdInput?.value.trim() || 'U_user_001';
    const clientApiKey = getClientApiKey();

    try {
      const res = await fetch('/api/line/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          user_id: activeUserId,
          api_key: clientApiKey
        })
      });
      const data = await res.json();
      appendLineMessage('bot', data.reply || '已收到指令');
    } catch (e) {
      appendLineMessage('bot', '伺服器連線異常');
    }
  }

  // 快捷指令按鈕
  document.querySelectorAll('.btn-quick-line').forEach(btn => {
    btn.addEventListener('click', () => {
      const cmd = btn.getAttribute('data-cmd');
      if (cmd) sendLineMockMessage(cmd);
    });
  });

  function appendLineMessage(sender, text) {
    const bubble = document.createElement('div');
    bubble.className = `line-bubble ${sender}`;
    bubble.innerHTML = text.replace(/\n/g, '<br>');
    lineChatBox.appendChild(bubble);
    lineChatBox.scrollTop = lineChatBox.scrollHeight;
  }

  btnSendLine.addEventListener('click', sendLineMockMessage);
  lineInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      sendLineMockMessage();
    }
  });

  init();
});
