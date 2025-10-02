# NewsGPT — Chat, Summarize/Translate, Export & Email

Get the latest news through intelligent conversation. Ask for any topic and receive real-time articles with AI-powered summaries and analysis. Export to Markdown **or email the final output** for easy sharing.

---

## Features
- Chat to fetch timely news (NewsAPI)
- AI **summary** (headline + concise paragraph)
- AI **translation**
- One-click **export** to `.md`
- One-click **email** the last AI output (single email or list via `.txt/.csv` upload or paste)

---

## Quickstart

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env`**
   ```env
   OPENAI_API_KEY=sk-...

   # SMTP (SendGrid example — easiest free option)
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USER=apikey
   SMTP_PASS=YOUR_SENDGRID_API_KEY
   SMTP_FROM=your_verified_sender@example.com

   # (Recommended) NewsAPI key if you read from env
   NEWSAPI_KEY=your_newsapi_key
   ```

3. **Add your NewsAPI key**
   - **Fastest:** in `chatbot_NewsAPI.py`, set your key where the request headers are defined.
   - **Recommended (env-based):**
     ```python
     headers = {"X-Api-Key": os.getenv("NEWSAPI_KEY")}
     ```
     Then put `NEWSAPI_KEY=...` in your `.env` (see Step 2).

4. **Run the app**
   ```bash
   python chatbot_NewsAPI.py
   ```
   Open the Gradio URL shown in the console.

---

## Usage
- Ask: “latest tariffs news from major US & EU outlets” (or any topic).
- Use the chatbot to **Summarize** to get a headline + concise paragraph and **Translate** to other languages.
- **Export** the assistant’s output to Markdown **or** **Email** it:
  - Upload a `.txt`/`.csv` of emails **or** paste addresses (comma/newline/semicolon).
  - Click **Send Last AI Output**.

---

## Troubleshooting (quick)
- **SMTP auth failed** → Check SendGrid creds, verified sender, and port **587** (TLS).
- **“No AI output yet”** → Ask the assistant to summarize/translate first; then export/email.

---

## Notes
- Don’t commit secrets—keep keys in `.env` (add it to `.gitignore`).
- To keep the app local-only, run Gradio without `share=True`.

---

## License
MIT (suggested).
