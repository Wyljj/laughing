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

async function ask() {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      token: document.getElementById('token').value,
      question: document.getElementById('question').value,
      profile: profilePayload()
    })
  });
  const data = await res.json();
  document.getElementById('answer').textContent = data.answer || JSON.stringify(data, null, 2);
}

async function gap() {
  const res = await fetch('/api/gap', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      token: document.getElementById('token').value,
      profile: profilePayload()
    })
  });
  const data = await res.json();
  document.getElementById('gap').textContent = data.result || JSON.stringify(data, null, 2);
}

async function upload() {
  const fd = new FormData();
  fd.append('token', document.getElementById('token').value);
  fd.append('project', document.getElementById('project').value);
  const f = document.getElementById('file').files[0];
  if (!f) return;
  fd.append('file', f);

  const res = await fetch('/api/upload', { method: 'POST', body: fd });
  const data = await res.json();
  document.getElementById('uploadResult').textContent = JSON.stringify(data, null, 2);
}
