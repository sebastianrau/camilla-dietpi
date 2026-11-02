// Registered by the pinned CamillaGUI 4.1.0 application constructor.
window.camillaDspRegisterEditor = (editor) => {
  window.camillaDspSaveYaml = async () => {
    const filename = editor.state.currentConfigFile;
    if (!filename) throw new Error('Choose a YAML filename in CamillaGUI first, then click Save permanently.');
    // Capture editor contents, including unapplied changes, at click time.
    const config = JSON.parse(JSON.stringify(editor.state.undoRedo.current()));
    async function post(path, body) {
      const response = await fetch(path, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
      });
      const message = await response.text();
      if (!response.ok || message.trim() !== 'OK') throw new Error(message || `GUI request failed (${response.status})`);
    }
    await post('/api/saveconfigfile', {filename, config});
    await post('/api/setactiveconfigfile', {name: filename});
    // Do not mark later edits as saved if the user changed the editor meanwhile.
    if (editor.state.currentConfigFile === filename &&
        JSON.stringify(editor.state.undoRedo.current()) === JSON.stringify(config)) {
      editor.setState({unsavedChanges: false});
    }
    return filename;
  };
};
