# Smart DBA Bot - Streamlit Cloud Deployment

## 🚀 Deploy to Streamlit Cloud

This Smart DBA Bot application is ready for Streamlit Cloud deployment. Follow these steps:

### 1. Prerequisites
- GitHub repository with your code
- Streamlit Cloud account (free at [share.streamlit.io](https://share.streamlit.io))
- Database credentials and API tokens

### 2. Deployment Steps

#### Step 1: Push to GitHub
```bash
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin main
```

#### Step 2: Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Connect your GitHub repository
4. Select branch: `main`
5. Main file path: `app.py`
6. Click "Deploy!"

#### Step 3: Configure Secrets
In your Streamlit Cloud app dashboard, go to **Settings > Secrets** and add:

```toml
# GitHub Token for LLM API
GITHUB_TOKEN = "your_github_token_here"
OPENAI_MODEL = "gpt-4o"

# Database Configuration
HEALTH_CHECK_HOST_1 = "your_db_host_1"
HEALTH_CHECK_HOST_2 = "your_db_host_2"
HEALTH_CHECK_HOST_3 = "your_db_host_3"
HEALTH_CHECK_HOST_4 = "your_db_host_4"
HEALTH_CHECK_DB = "inventory"
HEALTH_CHECK_USER = "your_db_username"
HEALTH_CHECK_PASSWORD = "your_db_password"
HEALTH_CHECK_PORT = "5432"
```

### 3. Features

✅ **Live Database Queries**: Query PostgreSQL databases across multiple datacenters  
✅ **Natural Language Processing**: Ask questions in plain English  
✅ **Excel Export**: Automatic Excel generation for large result sets  
✅ **Authentication**: Secure login system  
✅ **Multi-Database Support**: Oracle, PostgreSQL, MySQL, SQL Server  
✅ **Real-time Results**: Live query execution with progress tracking  

### 4. Environment Support

The application supports both:
- **Local Development**: Using `.env` file
- **Streamlit Cloud**: Using `secrets.toml` configuration

### 5. Login Credentials

Default login (update in `config.yaml`):
- **Username**: `dba_admin`
- **Password**: `botdba321`

### 6. Example Questions

- "Show me all servers in DC4"
- "List databases with uptime more than 10 days"
- "Show me Oracle servers across all datacenters"
- "Which servers have RAM more than 16GB?"

### 7. File Structure

```
chat_bot_db/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── config.yaml           # Authentication configuration
├── simple_auth.py        # Authentication module
├── .streamlit/
│   ├── config.toml       # Streamlit configuration
│   └── secrets.toml      # Secrets (local only - not in git)
├── src/
│   ├── env_helper.py     # Environment variable handler
│   ├── intelligent_live_query.py  # Query system
│   └── excel_exporter.py # Excel export functionality
└── README.md             # This file
```

### 8. Security Notes

🔒 **Never commit sensitive data**:
- Secrets are managed through Streamlit Cloud dashboard
- Local `.env` and `secrets.toml` files are in `.gitignore`
- Database passwords are encrypted in transit

### 9. Troubleshooting

**Common Issues:**

1. **Import Errors**: Ensure all dependencies are in `requirements.txt`
2. **Database Connection**: Check database credentials in secrets
3. **Authentication Failed**: Verify config.yaml settings
4. **Memory Issues**: Streamlit Cloud has memory limits for free tier

**Logs**: Check Streamlit Cloud app logs for detailed error messages.

### 10. Support

For issues or questions:
1. Check Streamlit Cloud app logs
2. Verify all secrets are properly configured
3. Ensure database hosts are accessible from Streamlit Cloud

---

## 🎯 Quick Start

1. **Deploy**: Connect GitHub repo to Streamlit Cloud
2. **Configure**: Add secrets in Streamlit Cloud dashboard  
3. **Login**: Use `dba_admin` / `botdba321`
4. **Query**: Ask "show me all servers in DC4"

Your Smart DBA Bot is ready! 🎉

1: git clone git@gitlab.com:one-bottomline/cloud/dce-database/smart_chat_bot.git

2: set the env to venv 
python3 -m venv .venv
source .venv/bin/activate  [ to start the venv]

3: pip install -r requirements.txt

4: streamlit run app.py

