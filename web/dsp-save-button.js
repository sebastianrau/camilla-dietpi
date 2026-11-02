(() => {
  if (document.getElementById('dsp-permanent-save')) return;
  const panel = document.createElement('div');
  panel.id = 'dsp-permanent-save';
  panel.style.cssText = 'position:fixed;bottom:12px;right:12px;z-index:10000;background:#20252b;color:#fff;padding:12px;border:1px solid #687582;border-radius:8px;max-width:340px;font:14px system-ui;box-shadow:0 2px 12px #0006';
  const button = document.createElement('button');
  button.textContent = 'Save permanently';
  button.style.cssText = 'padding:8px 12px;cursor:pointer';
  const hint = document.createElement('div');
  hint.style.cssText = 'margin-top:8px;line-height:1.4';
  hint.textContent = 'Saves the current editor to its selected YAML, then makes it permanent. Choose a filename once for a new configuration.';
  const status = document.createElement('div');
  status.setAttribute('role', 'status');
  status.style.cssText = 'margin-top:8px;white-space:pre-wrap;max-height:180px;overflow:auto';
  status.textContent = 'Ready to save editor YAML and make it permanent.';
  panel.append(button, hint, status);
  document.body.append(panel);
  const endpoint = new URL('/save', window.location.href);
  endpoint.port = '5006';
  let timer;
  async function poll() {
    try {
      const response = await fetch(endpoint, {cache: 'no-store'});
      if (!response.ok) throw new Error(`Save service returned ${response.status}`);
      const result = await response.json();
      button.disabled = result.running;
      status.textContent = result.running ? result.message :
        result.ok === true ? 'Saved permanently. Audio and GUI restarted.' :
        result.ok === false ? `Save failed: ${result.message}` : 'Ready to save editor YAML and make it permanent.';
      if (result.running) timer = setTimeout(poll, 1000);
    } catch (error) {
      status.textContent = `Cannot verify save: ${error.message}. Check SSH before retrying.`;
      // A lost reply does not imply that a disk save failed. Keep polling status.
      timer = setTimeout(poll, 5000);
    }
  }
  button.addEventListener('click', async () => {
    if (!window.confirm('Save the current editor contents to the selected YAML and make them permanent? This overwrites that YAML and applies these settings when DSP restarts. Audio will pause briefly; gain resets to the configured startup value.')) return;
    clearTimeout(timer);
    button.disabled = true;
    status.textContent = 'Saving editor to YAML…';
    try {
      if (typeof window.camillaDspSaveYaml !== 'function') throw new Error('Editor integration is not ready. Refresh the GUI or reinstall the matching bridge.');
      await window.camillaDspSaveYaml();
    } catch (error) {
      button.disabled = false;
      status.textContent = `YAML save failed: ${error.message}. No permanent snapshot was requested.`;
      return;
    }
    status.textContent = 'YAML saved. Requesting permanent snapshot…';
    try {
      const response = await fetch(endpoint, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
      if (!response.ok && response.status !== 409) throw new Error(`Request returned ${response.status}`);
    } catch (error) {
      status.textContent = `Save request uncertain: ${error.message}. Checking status…`;
    }
    await poll();
  });
  poll();
})();
