# AI Choose Now — Pythonista Port (iOS + LAN Ollama)

This repository contains a native **Pythonista** port of [AI Choose Now](https://github.com/ehewlett3/AI-Choose-Now), adapted for iPhone/iPad.

The app runs locally in Pythonista and talks to an Ollama server hosted on a Mac on the same LAN. The Ollama host IP and model are configurable from the app UI.

## What this port includes

- Native Pythonista UI (`ui` module)
- Configurable Ollama server host + port (for LAN use)
- Configurable model name
- Scenario essentials input
- Story rendering + 3 choice buttons
- Custom free-text action input
- Maintains rolling adventure context for coherent turns

## Mac setup (Ollama host)

1. Install Ollama on the Mac and start it.
2. Pull at least one chat model, e.g.:

   ```bash
   ollama pull llama3.1:8b
   ```

3. Ensure Ollama is reachable from your iPhone/iPad on the local network (same subnet/VPN-free).
4. Verify firewall allows inbound access to port `11434`.

## iOS / Pythonista setup

1. Open Pythonista on iOS.
2. Copy `ai_choose_now_pythonista.py` into Pythonista.
3. Run the script.
4. In the top bar, set:
   - **Ollama host** (Mac LAN IP, e.g. `192.168.1.50`)
   - **Port** (`11434` unless changed)
   - **Model** (e.g. `llama3.1:8b`)
5. Enter scenario essentials and tap **New Game**.

## Notes

- This is a native iOS Pythonista experience (not Flask/webview based).
- The app intentionally uses a strict output format prompt to keep choices parseable.
- If the model does not follow format exactly, the parser falls back and still produces 3 choices.
