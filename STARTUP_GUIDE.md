# Bank Support Chatbot - Startup Guide

Every time you close VS Code or restart your computer, you need to follow these exact steps to start the application again.

## Step 1: Open the Project
1. Open VS Code.
2. Ensure you have the `scratch` folder open (`c:\Users\ayush\.gemini\antigravity\scratch`).

## Step 2: Start the Backend (FastAPI)
1. Open a new terminal in VS Code (`Terminal` -> `New Terminal`).
2. Activate your virtual environment by typing:
   ```powershell
   .\venv\Scripts\activate
   ```
   *(You should see `(venv)` appear at the beginning of your terminal prompt).*

3. Start the backend server by typing:

   ```powershell
   uvicorn backend.main:app --reload
   ```
4. Leave this terminal running in the background.

## Step 3: Start the Frontend (Streamlit)
1. Open a **second** terminal in VS Code (click the `+` icon in the terminal panel).
2. Activate the virtual environment again in this new terminal:
   ```powershell
   .\venv\Scripts\activate
   ```
3. Start the frontend Streamlit application by typing:
   ```powershell
   streamlit run frontend/app.py
   ```
4. This command will automatically open a new tab in your web browser with the Bank Support Chatbot.

---

### Troubleshooting
* **Red squiggly lines in VS Code?** Press `Ctrl + Shift + P`, type `Python: Select Interpreter`, and select `.\venv\Scripts\python.exe`.
* **"ModuleNotFoundError"?** Make sure you ran `.\venv\Scripts\activate` in the terminal before running the server commands.
