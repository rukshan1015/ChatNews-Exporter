
import os, requests, json, tempfile, re, gradio as gr, io, csv, smtplib
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from IPython.display import Markdown, update_display
from email.message import EmailMessage


load_dotenv(override=True)
openai_api_key=os.getenv('OPENAI_API_KEY')
openai=OpenAI()


def news_total (
    query=None,                    # alias for NewsAPI `q`
    title=None,                    # -> qInTitle
    sources=None,                  # -> sources
    domains=None,                  # -> domains
    exclude_domains=None,          # -> excludeDomains
    from_date=None,                # -> from
    to_date=None,                  # -> to
    language="en",                 # -> language
    sort_by="publishedAt",         # -> sortBy: relevancy | popularity | publishedAt
    page_size=5,                   # -> pageSize (max 100)
    page=1                         # -> page
):



    if not (query or title or sources or domains):
        raise ValueError("Provide at least one of the followings: query, title, sources, or domains.")


    url='https://newsapi.org/v2/everything'
    headers = {"X-Api-Key": 'YOUR NEWS API KEY'} #  Or use .env to keep the API key hidden 
    params = {
            "q": query,
            "qInTitle": title,
            "sources": sources,
            "domains": domains,
            "excludeDomains": exclude_domains,
            "from": from_date,
            "to": to_date,
            "language": language,
            "sortBy": sort_by,
            "pageSize": min(int(page_size), 100),
            "page": int(page)
        }

    # To drop None values(strings) in the API call when the user doesn't provide the value for a parameter. This will build the new paramater list based on user input.
    # This voids the 'None' being sent to the API

    params_updated={k:v for k,v in params.items() if v is not None}

    news=requests.get(url=url, headers=headers, params=params_updated)

    return news.json()


# Exporting the list of articles

last_result=[] # list

def export_news ():
    global last_result
    if not last_result:
        return None
    today=datetime.now().strftime("%Y-%m-%d")

    fd, path = tempfile.mkstemp(prefix=f'News_{today}',suffix='.md')
    os.close(fd)

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Today's News\n\n")
            for article in last_result:
                title = article.get('title', 'Untitled')
                source = (article.get('source') or {}).get('name', '')
                date = article.get('publishedAt', '')
                url = article.get('url', '')
                description = article.get('description', '')

                f.write(f"## {title}\n")
                f.write(f"**Source:** {source}\n")
                f.write(f"**Date:** {date}\n")
                f.write(f"**URL:** {url}\n")
                if description:
                    f.write(f"**Description:** {description}\n")
                f.write("\n---\n\n")

        # Return just the file path, not a dictionary
        return path

    except Exception as e:
        print(f"Error creating export file: {e}")
        return None

# Function for exporting the last AI response

last_ai_response = ""

def export_ai_response():
    global last_ai_response

    if not last_ai_response:
        return None

    today = datetime.now().strftime("%Y-%m-%d")

    # Create temporary file
    fd, path = tempfile.mkstemp(prefix=f'AI_Response_{today}_', suffix='.md')
    os.close(fd)

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("# AI Response Export\n\n")
            f.write(f"**Exported on:** {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write("---\n\n")
            f.write(last_ai_response)
            f.write("\n\n")

        return path

    except Exception as e:
        print(f"Error creating export file: {e}")
        return None

# Function for Email sender

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _normalize_emails(items):
    out, seen = [], set()
    for raw in items or []:
        e = (raw or "").strip().strip(",;")
        if e and e.lower() not in seen and EMAIL_REGEX.match(e):
            out.append(e); seen.add(e.lower())
    return out

def _parse_emails(file_obj, manual_text):
    emails = []
    # From file (optional): .csv (email column or scan) or .txt (comma/newline/semicolon-separated)
    if file_obj:
        name = (getattr(file_obj, "name", "") or "").lower()
        data = file_obj.read() if hasattr(file_obj, "read") else file_obj
        text = data.decode("utf-8", errors="ignore")
        if name.endswith(".csv"):
            s = io.StringIO(text)
            try:
                reader = csv.DictReader(s)
                cols = [c.lower() for c in (reader.fieldnames or [])]
                if "email" in cols:
                    col = reader.fieldnames[cols.index("email")]
                    for row in reader: emails.append(row.get(col, ""))
                else:
                    s.seek(0)
                    for row in csv.reader(io.StringIO(text)):
                        for cell in row:
                            if EMAIL_REGEX.match((cell or "").strip()):
                                emails.append(cell)
            except Exception:
                for tok in re.split(r"[,\n;]+", text):
                    if EMAIL_REGEX.match(tok.strip()): emails.append(tok)
        else:  # treat as .txt
            for tok in re.split(r"[,\n;]+", text):
                if EMAIL_REGEX.match(tok.strip()): emails.append(tok)

    # From textbox (optional)
    if manual_text:
        for tok in re.split(r"[,\n;]+", manual_text):
            if EMAIL_REGEX.match(tok.strip()):
                emails.append(tok)

    return _normalize_emails(emails)

def _send_email_smtp(subject, body, recipients):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd  = os.getenv("SMTP_PASS")
    from_addr = os.getenv("SMTP_FROM") or user

    if not (host and port and user and pwd and from_addr):
        return "❌ Missing SMTP config in .env (SMTP_HOST/PORT/USER/PASS/SMTP_FROM)."
    if not recipients:
        return "❌ No valid email addresses."

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)

        with smtplib.SMTP(host, port) as s:
            s.starttls()          # TLS on 587
            s.login(user, pwd)
            s.send_message(msg)
        return f"✅ Sent to {len(recipients)} recipient(s)."
    except Exception as e:
        return f"❌ Send failed: {e}"

# Gradio handler — sends whatever is currently in last_ai_response
def send_last_ai_output(uploaded_file, manual_emails_text):
    global last_ai_response
    emails = _parse_emails(uploaded_file, manual_emails_text)
    if not last_ai_response:
        return "❌ No AI output yet. Ask the assistant to summarize/translate first."
    subject = (last_ai_response.strip().splitlines()[0] or "News Summary")[:120]
    return _send_email_smtp(subject=subject, body=last_ai_response, recipients=emails)


news_function = {
    "name": "news_total",
    "description": "Fetches news articles from NewsAPI's 'everything' endpoint. Use this function when the user asks for general news or specific topics. At least one of query, title, sources, or domains must be provided. You can also filter by date range, language, sort order, and page size.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {"type": "string", "description": "Keyword or phrase to search in all article fields."},
        "title": {"type": "string", "description": "Keyword or phrase to search only in article titles."},
        "sources": {"type": "string", "description": "Comma-separated list of source IDs (e.g., 'bbc-news,cnn')."},
        "domains": {"type": "string", "description": "Comma-separated list of domains to restrict search (e.g., 'bbc.co.uk,techcrunch.com')."},
        "exclude_domains": {"type": "string", "description": "Comma-separated list of domains to exclude from results."},
        "from_date": {"type": "string", "description": "Oldest article date in YYYY-MM-DD format."},
        "to_date": {"type": "string", "description": "Newest article date in YYYY-MM-DD format."},
        "language": {"type": "string", "description": "Language of the articles (default 'en')."},
        "sort_by": {"type": "string", "enum": ["relevancy","popularity","publishedAt"], "description": "Order to sort the results."},
        "page_size": {"type": "integer", "description": "Number of results per page (default 5, max 100)."},
        "page": {"type": "integer", "description": "Page number of results to fetch (default 1)."}
      },
      "required": []
    }
  }


tools=[{'type':'function','function':news_function}] 


system_prompt = '''You are a helpful news assistant that retrieves and summarizes current events.

- When a user asks for news, always use the `news_total` function to fetch articles.
- At least one search filter must be provided:
  • `query` for general keyword searches,
  • `title` for keywords that must appear in article titles,
  • `sources` for specific outlets (e.g. "bbc-news"),
  • `domains` for specific websites (e.g. "bbc.co.uk").
- Use optional filters when the user specifies:
  • `from_date` and `to_date` for date ranges,
  • `language` to restrict the language,
  • `sort_by` for ordering results (relevancy, popularity, publishedAt),
  • `page_size` to control how many articles to return (default 5).
- If the user is vague (e.g. "show me the news"), default to `query="news"`, `language="en"`, and `sort_by="publishedAt"`.
- After calling the function, present the headlines clearly, listing title, source, and URL. Summarize briefly rather than dumping raw JSON.
- If no results are returned, apologize and suggest trying a broader search term or another source/country.
- Always keep responses concise, neutral, and focused on the news content.'''


max_history=5 # to limit interaction for last 5 chats

def chat (user_prompt, history):

    global last_ai_response  # global variable is set where its generated

    trimmed_history = history[-max_history:]

    messages=[{'role':'system','content':system_prompt}]
    messages+=trimmed_history
    messages+=[{'role':'user','content':user_prompt}]

    response=openai.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        tools=tools,
    )

    if response.choices[0].finish_reason=='tool_calls':
        message_tool=response.choices[0].message
        response = handle_tool_call(message_tool)
        messages.append(message_tool)
        messages.extend(response)
        response=openai.chat.completions.create(model='gpt-4o-mini',messages=messages)   

    last_ai_response= response.choices[0].message.content or 'Done'  #assigning the top respone to last_ai_response, to generate an export file
    return last_ai_response


def handle_tool_call(message_tool):
    global last_result # global variable is set where its generated
    response = []

    for tc in message_tool.tool_calls:
        arguments = json.loads(tc.function.arguments or "{}")
        # Pick a topic from the first non-empty filter we see (optional)

        if tc.function.name=='news_total':
            result = news_total(**arguments)
            last_result=result.get("articles",[])

        else:
            result = {"error": f"Unknown tool {tc.function.name}"}

        response.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps({'args':arguments, 'result':result})
        })

    return response


## DARK MODE

force_dark_mode = """
function refresh() {
    const url = new URL(window.location);
    if (url.searchParams.get('__theme') !== 'dark') {
        url.searchParams.set('__theme', 'dark');
        window.location.href = url.href;
    }
}
"""


small_file_css = """
.file-preview {
    max-height: 30px !important;
    height: 30px !important;
}
/* Target the entire file component */
.gr-file {
    max-height: 50px !important;
}
"""

# UI with Gradio

with gr.Blocks(js=force_dark_mode, css=small_file_css) as demo:

    gr.Markdown("""# NewsGPT - Chat, Summarize, Translate, Export

    Get the latest news through intelligent conversation. Ask for any topic and receive real-time articles with AI-powered summaries and analysis. 
    Export your results to Markdown or send them by email instantly for easy sharing and reference."""
    )                                                                                                                                                                                              

    chatbot = gr.ChatInterface(
        fn=chat,
        type='messages',
        flagging_mode='never'
    )
    with gr.Row():
        export_article = gr.Button("📥 Export Articles")
        export_file_articles = gr.File(label="Download Articles List", height=50)
    with gr.Row():
        export_summary = gr.Button("📥 Export Last AI Response (Summary/Translation)")
        export_ai_response_file = gr.File(label = "Download Last AI response (.md)", height=50)

    with gr.Row():
        email_file = gr.File(label="Upload emails (.csv or .txt)", file_types=[".csv", ".txt"])

    with gr.Row():
        email_text = gr.Textbox(label="Or paste emails (comma/newline/semicolon separated)")

    with gr.Row():
        email_send_btn = gr.Button("✉️ Send Last AI Output")
        email_status = gr.Markdown()


    export_article.click(
        fn=export_news,        # This should return {"file": path}
        outputs=export_file_articles
    )
    export_summary.click(
        fn=export_ai_response,
        outputs= export_ai_response_file
    )

    email_send_btn.click(
        fn=send_last_ai_output,
        inputs=[email_file, email_text],
        outputs=email_status
    )


demo.launch(share=True)

