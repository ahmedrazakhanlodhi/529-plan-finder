# 529 Plan Finder — The 529 Network

A guided questionnaire helping families find the best 529 college savings plan.
Data compiled by The 529 Network.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub
2. Connect at share.streamlit.io
3. Add email credentials in the Secrets tab (see .streamlit/secrets.toml for template)

## Embed (iframe)

```html
<iframe src="https://your-app.streamlit.app"
        width="100%" height="700px" frameborder="0"></iframe>
```

## Structure

```
529-plan-finder/
├── app.py                   # Main app — 3 screens (welcome, questionnaire, results)
├── requirements.txt
├── utils/
│   ├── knowledge_base.py    # All 51 state tax data + 17 plan records
│   ├── translations.py      # EN + ES strings; t() helper
│   ├── scoring.py           # Plan ranking engine
│   ├── pdf_generator.py     # PDF summary (reportlab)
│   └── email_sender.py      # SMTP + SendGrid email delivery
└── .streamlit/
    ├── config.toml          # Brand theme
    └── secrets.toml         # Email credentials template
```
