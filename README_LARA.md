# 🚀 LARA - Laptop AI Remote Agent

This folder contains the complete, production-ready source code for LARA.

## 📦 What's inside:

- **`backend/`**: The FastAPI server that handles WhatsApp webhooks and communicates with Groq AI.
- **`agent/`**: The local laptop agent that executes commands (includes Playwright DOM automation).
- **`start.bat`**: The one-click script to launch everything.

## 🛠️ Setup Instructions:

1. **Environment**:
   - Open `backend/.env` and update your `WHATSAPP_ACCESS_TOKEN`.
   - Ensure the `GROQ_API_KEY` is active.

2. **Launch**:
   - Simply double-click `start.bat`.
   - It will start the backend, the ngrok tunnel (Static URL), and the Laptop Agent.

3. **WhatsApp Configuration**:
   - Callback URL: `https://rinsing-keenness-scorch.ngrok-free.dev/webhook/whatsapp`
   - Verify Token: `verify_lara_bot`

## 🌟 Key Features:
- **Direct YouTube Play**: Uses DOM automation (Playwright) to play songs in Brave by default.
- **System Controls**: Volume, Notepad, Screenshots, and Keyboard shortcuts.
- **Visual Intelligence**: Vision AI support for clicking specific screen elements.
- **Persistent Browser**: Keeps the Brave window open for seamless music listening.

---
*Created by Antigravity AI*
