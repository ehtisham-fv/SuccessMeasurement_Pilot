# Success Measurement - Data Collection System

A Python-based system for collecting GitHub and Jira metrics to measure software project team productivity and efficiency after introducing AI-assisted tools.

## 📋 Overview

This system fetches data from:
- **GitHub**: Pull requests (PRs), comments, commits, and file changes
- **Jira**: Issues with status transition timestamps

Data is stored in CSV format for further analysis.

## 🏗️ Project Structure

```
success_measurement/
├── shared/                             # Reusable modules
│   ├── __init__.py
│   ├── github_client.py                # GitHub API client
│   ├── jira_client.py                  # Jira API client
│   └── utils.py                        # Helper functions
│
├── Omnichannel_Customer_Account/       # Project folder
│   ├── __init__.py
│   ├── config.yaml                     # Project-specific configuration
│   ├── run_analysis.py                 # Main execution script
│   └── data/                           # Generated CSV files
│       ├── github_data.csv
│       └── jira_data.csv
│
├── .env                                # Environment variables (DO NOT COMMIT)
├── .gitignore                          # Git ignore rules
├── requirements.txt                    # Python dependencies
└── README.md                           # This file
```

## 🚀 Setup Instructions

### 1. Prerequisites

- Python 3.11 or higher
- GitHub Personal Access Token
- Jira API Token
- Access to target repositories and Jira projects

### 2. Install Dependencies

```bash
cd success_measurement
pip install -r requirements.txt
```

Or use a virtual environment (recommended):

```bash
cd success_measurement
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the `success_measurement/` directory (the user mentioned they already have this at `SuccessMeasurement_Pilot/.env` - you may need to copy or reference it):

```bash
# Copy the existing .env or create a new one
# If you have it at SuccessMeasurement_Pilot/.env, you can:
# cp ../SuccessMeasurement_Pilot/.env .env
```

The `.env` file should contain:

```env
# Atlassian/Jira Credentials
ATLASSIAN_EMAIL=your-email@fielmann.com
ATLASSIAN_API_TOKEN=your-jira-api-token
ATLASSIAN_BASE_URL=https://fielmann.atlassian.net

# GitHub Credentials
GITHUB_TOKEN=your-github-personal-access-token
GITHUB_ORG=fielmann-ag
```

**Important:** Never commit the `.env` file to version control. It's already in `.gitignore`.

#### How to Get API Tokens:

**GitHub Personal Access Token:**
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Required scopes: `repo` (full control of private repositories)

**Jira API Token:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create API token
3. Copy and save it securely

### 4. Configure Project Settings

Edit `Omnichannel_Customer_Account/config.yaml` if needed:

```yaml
project_name: "Omnichannel Customer Account"
project_key: "OA"
date_range_months: 12  # Adjust date range (default: 12 months)

statuses:
  in_progress: ["In Progress"]
  done: ["Done"]
  # ... other statuses

repositories:
  - organization: "fielmann-ag"
    repository: "agent-insight-hub"
  # ... other repositories
```

## 🏃 Running the Analysis

### Option 1: Run Directly

```bash
cd success_measurement/Omnichannel_Customer_Account
python run_analysis.py
```

### Option 2: Run as Module

```bash
cd success_measurement
python -m Omnichannel_Customer_Account.run_analysis
```

### Expected Output

The script will:
1. Load environment variables and configuration
2. Fetch GitHub pull requests for all configured repositories
3. Fetch Jira issues for the specified project
4. Save data to CSV files in `Omnichannel_Customer_Account/data/`
5. Display a summary of collected data

Example output:
```
============================================================
SUCCESS MEASUREMENT - DATA COLLECTION
Project: Omnichannel Customer Account
============================================================
Loading environment variables...
Loading configuration from config.yaml...
Project: Omnichannel Customer Account
Date Range: Last 12 months
Repositories: 2
Jira Project Key: OA

============================================================
PHASE 1: FETCHING GITHUB DATA
============================================================
Fetching PRs for fielmann-ag/agent-insight-hub...
Found 87 PRs in date range for agent-insight-hub
Processed 10/87 PRs for agent-insight-hub
...
Completed fetching 87 PRs for agent-insight-hub
Successfully wrote 150 records to github_data.csv

============================================================
PHASE 2: FETCHING JIRA DATA
============================================================
Fetching Jira issues for project OA...
Found 523 issues in date range for OA
Processed 50/523 issues for OA
...
Completed fetching 523 issues for OA
Successfully wrote 523 records to jira_data.csv

============================================================
SUMMARY
============================================================
Total Pull Requests: 150
Total Jira Issues: 523

Data saved to:
  - GitHub: Omnichannel_Customer_Account/data/github_data.csv
  - Jira:   Omnichannel_Customer_Account/data/jira_data.csv

============================================================
DATA COLLECTION COMPLETED SUCCESSFULLY
============================================================
```

## 📊 Output Data Format

### github_data.csv

| Column | Type | Description |
|--------|------|-------------|
| repository | string | Repository name |
| pr_name | string | Pull request title |
| pr_number | integer | PR number |
| created_at | datetime | When PR was created (YYYY-MM-DD HH:MM:SS) |
| merged_at | datetime | When PR was merged (empty if not merged) |
| is_merged | boolean | Whether PR is merged to base branch |
| num_comments | integer | Total comments (review + issue comments) |
| num_commits | integer | Number of commits |
| num_files_changed | integer | Number of files changed |

### jira_data.csv

| Column | Type | Description |
|--------|------|-------------|
| ticket_key | string | Jira ticket key (e.g., "OA-123") |
| summary | string | Issue summary/title |
| type | string | Issue type (Story, Bug, Task, etc.) |
| created | datetime | When issue was created (YYYY-MM-DD HH:MM:SS) |
| in_progress_timestamp | datetime | LATEST "In Progress" transition |
| done_timestamp | datetime | LATEST "Done" transition |

## 🔧 Configuration Options

### Date Range

Adjust the `date_range_months` parameter in `config.yaml`:

```yaml
date_range_months: 12  # Collect data from last 12 months
```

### Status Definitions

Customize Jira status names in `config.yaml`:

```yaml
statuses:
  in_progress: ["In Progress", "In Development"]  # Match your board's statuses
  done: ["Done", "Closed", "Resolved"]
```

**Important:** Status names must match **exactly** (case-sensitive) with your Jira board.

## 🚨 Error Handling

The system uses an **abort-on-error** strategy:
- If any critical error occurs (API failure, missing credentials, etc.), the script aborts immediately
- No partial data is written
- Errors are logged with clear messages
- Transient network errors are retried automatically (3 attempts)

## 📝 Adding New Projects

To add a new project team:

1. Create a new folder: `success_measurement/NewProjectName/`
2. Copy `config.yaml` from an existing project
3. Update configuration with new project details
4. Copy `run_analysis.py` (or create a symlink)
5. Run the analysis

No changes to shared modules required!

## 🛠️ Troubleshooting

### Issue: "Missing required environment variables"
- **Solution:** Ensure `.env` file exists and contains all required variables

### Issue: "Jira API error: 401"
- **Solution:** Check Jira credentials in `.env` file. Verify API token is valid.

### Issue: "GitHub API error: 401"
- **Solution:** Check GitHub token in `.env` file. Ensure token has `repo` scope.

### Issue: "No data found in date range"
- **Solution:** Increase `date_range_months` in `config.yaml` or verify project has data in the specified period.

### Issue: Rate limit errors
- **Solution:** The system automatically handles rate limits. Wait for the script to resume after cooldown period.

## 📦 Dependencies

- `requests` - HTTP requests to APIs
- `python-dotenv` - Environment variable management
- `PyYAML` - YAML configuration parsing
- `tenacity` - Retry logic for API calls
- `python-dateutil` - Date/time utilities
- `tqdm` - Progress bars (optional)

## 🔐 Security Notes

- **Never commit `.env` file** - It contains sensitive credentials
- `.gitignore` is configured to exclude:
  - `.env` files
  - Generated CSV data files
  - Python cache files
- Rotate API tokens regularly
- Use tokens with minimal required permissions

## 📈 Next Steps (Future Enhancements)

- Database storage (PostgreSQL/SQLite)
- Incremental updates (fetch only new data)
- Data visualization dashboard
- Automated scheduling (cron jobs)
- Team comparison analytics
- Export to other formats (JSON, Excel)

## 📄 License

Internal Fielmann AG project.

## 🤝 Support

For issues or questions, contact the Success Measurement team.

---

**Version:** 1.0.0  
**Last Updated:** October 30, 2025

