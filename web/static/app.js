function profilePayload() {
  return {
    region: document.getElementById('region').value,
    industry: document.getElementById('industry').value,
    has_hw_identification: false,
    has_haz_waste_room: false,
    has_transfer_manifest: false,
    has_training: false,
    vendor_qualified: false
  };
}

function showToast(message, isError = false) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.remove('hidden');
  toast.classList.toggle('error', isError);
  setTimeout(() => toast.classList.add('hidden'), 2200);
}

async function requestJson(url, options = {}) {
  const res = await fetch(url, options);
  let data = {};
  try { data = await res.json(); } catch (e) { data = {}; }
  if (!res.ok) {
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return data;
}

function setAskLoading(loading) {
  const btn = document.getElementById('askBtn');
  const spinner = document.getElementById('askSpinner');
  const text = document.getElementById('askText');
  btn.disabled = loading;
  spinner.classList.toggle('hidden', !loading);
  text.textContent = loading ? '处理中...' : '发送问题';
}

async function ask() {
  const answerEl = document.getElementById('answer');
  const question = document.getElementById('question').value.trim();
  if (!question) {
    answerEl.textContent = '请先输入问题。';
    showToast('请先输入问题', true);
    return;
  }

  setAskLoading(true);
  try {
    const data = await requestJson('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        token: document.getElementById('token').value,
        question,
        profile: profilePayload()
      })
    });
    const answer = data.answer || JSON.stringify(data, null, 2);
    const citations = (data.citations || []).length
      ? "

[KB引用]
" + data.citations.join("
")
      : "";
    answerEl.textContent = answer + citations;
    showToast(data.rag_enabled ? '问答完成（含知识库引用）' : '问答完成');
  } catch (e) {
    answerEl.textContent = `请求失败: ${e.message}`;
    showToast(e.message, true);
  } finally {
    setAskLoading(false);
  }
}

async function gap() {
  const btn = document.getElementById('gapBtn');
  const out = document.getElementById('gap');
  btn.disabled = true;
  btn.textContent = '生成中...';
  try {
    const data = await requestJson('/api/gap', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token: document.getElementById('token').value, profile: profilePayload()})
    });
    out.textContent = data.result || JSON.stringify(data, null, 2);
    showToast('整改清单已生成');
  } catch (e) {
    out.textContent = `请求失败: ${e.message}`;
    showToast(e.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = '生成整改清单';
  }
}

async function upload() {
  const out = document.getElementById('uploadResult');
  const btn = document.getElementById('uploadBtn');
  const fileInput = document.getElementById('file');
  const f = fileInput.files[0];
  if (!f) {
    out.textContent = '请先选择文件。';
    showToast('请先选择文件', true);
    return;
  }

  const fd = new FormData();
  fd.append('token', document.getElementById('token').value);
  fd.append('project', document.getElementById('project').value);
  fd.append('file', f);

  btn.disabled = true;
  btn.textContent = '上传中...';
  try {
    const data = await requestJson('/api/upload', {method: 'POST', body: fd});
    out.textContent = JSON.stringify(data, null, 2);
    showToast('上传成功');
  } catch (e) {
    out.textContent = `上传失败: ${e.message}`;
    showToast(e.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = '上传文件';
  }
}

async function kbIngest() {
  const out = document.getElementById('kbResult');
  const title = document.getElementById('kbTitle').value.trim() || 'untitled';
  const project = document.getElementById('kbProject').value.trim() || 'default-project';
  const text = document.getElementById('kbText').value.trim();
  if (!text) {
    out.textContent = '请先输入要入库的文本。';
    showToast('请先输入要入库的文本', true);
    return;
  }
  try {
    const data = await requestJson('/api/kb/ingest', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token: document.getElementById('token').value, title, project, text})
    });
    out.textContent = JSON.stringify(data, null, 2);
    showToast('知识入库成功');
  } catch (e) {
    out.textContent = `入库失败: ${e.message}`;
    showToast(e.message, true);
  }
}

async function kbList() {
  const out = document.getElementById('kbResult');
  try {
    const token = encodeURIComponent(document.getElementById('token').value);
    const project = encodeURIComponent(document.getElementById('kbProject').value || '');
    const data = await requestJson(`/api/kb/list?token=${token}&project=${project}`);
    out.textContent = JSON.stringify(data, null, 2);
    showToast('已刷新列表');
  } catch (e) {
    out.textContent = `列表获取失败: ${e.message}`;
    showToast(e.message, true);
  }
}

async function kbSearch() {
  const out = document.getElementById('kbResult');
  const query = document.getElementById('kbQuery').value.trim();
  if (!query) {
    out.textContent = '请输入检索词。';
    showToast('请输入检索词', true);
    return;
  }
  try {
    const data = await requestJson('/api/kb/search', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        token: document.getElementById('token').value,
        query,
        project: document.getElementById('kbProject').value || undefined,
        top_k: 5
      })
    });
    out.textContent = JSON.stringify(data, null, 2);
    showToast('检索完成');
  } catch (e) {
    out.textContent = `检索失败: ${e.message}`;
    showToast(e.message, true);
  }
}

function bindEvents() {
  document.getElementById('askBtn').addEventListener('click', ask);
  document.getElementById('gapBtn').addEventListener('click', gap);
  document.getElementById('uploadBtn').addEventListener('click', upload);
  document.getElementById('kbIngestBtn').addEventListener('click', kbIngest);
  document.getElementById('kbListBtn').addEventListener('click', kbList);
  document.getElementById('kbSearchBtn').addEventListener('click', kbSearch);
  document.getElementById('logoutBtn').addEventListener('click', () => showToast('已退出（演示态）'));
  document.getElementById('exportBtn').addEventListener('click', () => showToast('证据包导出功能开发中'));
}

document.addEventListener('DOMContentLoaded', bindEvents);
