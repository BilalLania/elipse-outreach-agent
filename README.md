# 🎯 Elipse Studio — AI Outreach Agent & Lead Dashboard

An automated AI outreach system that researches physical and configurable product businesses, identifies companies lacking interactive 3D web configurators, enriches contact details, drafts personalized cold emails, and manages the outreach pipeline.

---

## ⚡ Features

- **🧠 Google Gemini 3.6 Flash Agent:** Generates targeted search strategies and drafts hyper-personalized cold outreach emails.
- **🌐 Live Web Research:** Searches the web in real-time to find target companies and observe product catalogs.
- **🎯 Contact Enrichment:** Integrates with Hunter.io to discover verified sales/founder emails.
- **💾 Persistent SQLite Database:** Tracks leads across statuses (`new`, `approved`, `sent`, `rejected`) and prevents duplicate outreach.
- **📊 Interactive Streamlit Dashboard:**
  - Real-time pipeline metrics and status filtering.
  - In-browser draft editing & approval workflow.
  - **1-Click Mailto Trigger:** Opens your pre-filled email draft directly in Outlook/Gmail/Apple Mail.
  - **CSV Export:** Download qualified leads for email campaigns or CRM import.

---

## 🚀 Getting Started (Local Setup)

### 1. Clone the repository & Install Dependencies
```bash
git clone <your-repo-url>
cd outreach_system
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory (or copy from `.env.example`):
```env
# Required: Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Hunter.io API Key for decision-maker email lookups
HUNTER_API_KEY=your_hunter_api_key_here

# Optional: Your Calendly / booking URL
CALENDAR_LINK=https://calendly.com/your-name/15-mins-meeting
```

### 3. Launch the Dashboard
```bash
streamlit run app.py
```
This opens the dashboard at `http://localhost:8501`.

---

## ☁️ Deploying to the Cloud (Free & Easy)

### Option 1: Streamlit Community Cloud (Recommended)
1. Push your repository to **GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Elipse Outreach System"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git push -u origin main
   ```
2. Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
3. Click **"New App"** and select your repository and `app.py`.
4. Under **"Advanced Settings" $\rightarrow$ "Secrets"**, paste your `.env` variables:
   ```toml
   GEMINI_API_KEY = "your_actual_key"
   HUNTER_API_KEY = "your_actual_key"
   CALENDAR_LINK = "https://calendly.com/your-name/15-mins-meeting"
   ```
5. Click **Deploy**! Your app is now live on the web with a public URL.

---

## 🔒 Security
- `.env`, `leads.db`, and temporary files are strictly ignored via `.gitignore` to prevent any credential leaks.
