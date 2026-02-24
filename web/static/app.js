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
    return;
  }

  setAskLoading(true);
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        token: document.getElementById('token').value,
        question,
        profile: profilePayload()
      })
    });
    const data = await res.json();
    answerEl.textContent = data.answer || data.detail || JSON.stringify(data, null, 2);
  } catch (e) {
    answerEl.textContent = `请求失败: ${e}`;
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
    const res = await fetch('/api/gap', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        token: document.getElementById('token').value,
        profile: profilePayload()
      })
    });
    const data = await res.json();
    out.textContent = data.result || data.detail || JSON.stringify(data, null, 2);
  } catch (e) {
    out.textContent = `请求失败: ${e}`;
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
    return;
  }

  const fd = new FormData();
  fd.append('token', document.getElementById('token').value);
  fd.append('project', document.getElementById('project').value);
  fd.append('file', f);

  btn.disabled = true;
  btn.textContent = '上传中...';
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: fd });
    const data = await res.json();
    out.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    out.textContent = `上传失败: ${e}`;
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
    return;
  }
  const res = await fetch('/api/kb/ingest', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({token: document.getElementById('token').value, title, project, text})
  });
  const data = await res.json();
  out.textContent = JSON.stringify(data, null, 2);
}

async function kbList() {
  const out = document.getElementById('kbResult');
  const token = encodeURIComponent(document.getElementById('token').value);
  const project = encodeURIComponent(document.getElementById('kbProject').value || '');
  const res = await fetch(`/api/kb/list?token=${token}&project=${project}`);
  const data = await res.json();
  out.textContent = JSON.stringify(data, null, 2);
}

async function kbSearch() {
  const out = document.getElementById('kbResult');
  const query = document.getElementById('kbQuery').value.trim();
  if (!query) {
    out.textContent = '请输入检索词。';
    return;
  }
  const res = await fetch('/api/kb/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      token: document.getElementById('token').value,
      query,
      project: document.getElementById('kbProject').value || undefined,
      top_k: 5
    })
  });
  const data = await res.json();
  out.textContent = JSON.stringify(data, null, 2);
}
