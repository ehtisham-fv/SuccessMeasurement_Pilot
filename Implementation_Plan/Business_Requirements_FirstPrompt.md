# 🧠 Prompt for AI Agent – Success Measurement (Phase 1 Setup)

You are tasked to **plan and implement** the foundational project structure for the initiative **“Success Measurement.”**  
This initiative evaluates software project teams based on their Jira and GitHub activities to measure productivity and efficiency after introducing AI-assisted tools (ChatGPT Enterprise, Cursor IDE, GitHub Copilot, etc.) in Q3 2025.

---

## 🎯 Project Goal
Build a modular and scalable Python-based system that:
1. Fetches **Jira** and **GitHub** data for each project team.
2. Stores all data locally in **CSV files** for further analytics.
3. Allows easy extension to multiple teams — each with unique Jira boards and GitHub repositories.
4. Ensures **secure credentials handling**, **clean modular design**, and **full data retrieval with pagination**.

---

## 🧩 System Architecture Requirements

### 🏗️ Root Folder Structure
```
success_measurement/
│
├── shared/                             # Shared reusable modules
│   ├── github_client.py                # Handles GitHub API calls
│   ├── jira_client.py                  # Handles Jira API calls
│   ├── utils.py                        # Helper functions (e.g., pagination, date parsing)
│
├── Omnichannel_Customer_Account/       # First project team folder
│   ├── config.yaml                     # Project-specific configuration
│   ├── run_analysis.py                 # Runs the end-to-end workflow for this team
│
├── .env                                # Environment variables (sensitive info)
├── .gitignore                          # Ensures .env and generated data are excluded
└── requirements.txt                    # Required dependencies
```

---

## 🔐 Environment Configuration (.env)
Sensitive credentials will be provided here (and excluded via `.gitignore`):
```
ATLASSIAN_EMAIL=<email>
ATLASSIAN_API_TOKEN=<token>
ATLASSIAN_BASE_URL=https://fielmann.atlassian.net
GITHUB_TOKEN=<token>
GITHUB_ORG=fielmann-ag
```

---

## ⚙️ Project Configuration for Omnichannel Customer Account

File: `Omnichannel_Customer_Account/config.yaml`

```yaml
project_name: "Omnichannel Customer Account"
project_key: "OA"
board_name: "Omnichannel Account Board"
base_url: "https://fielmann.atlassian.net"

statuses:
  refinement: ["Refinement"]
  todo: ["TODO"]
  in_progress: ["In Progress"]
  ready_for_review: ["Ready for Review"]
  in_review: ["In Review"]
  done: ["Done"]

repositories:
  - organization: "fielmann-ag"
    repository: "agent-insight-hub"
    full_repo_path: "fielmann-ag/agent-insight-hub"
    branch: "main"

  - organization: "fielmann-ag"
    repository: "customer-gdpr-deletion"
    full_repo_path: "fielmann-ag/customer-gdpr-deletion"
    branch: "main"
```

---

## 🧮 Data to Fetch and Store

### 🟦 From GitHub (per repository)
Store results in `data/github_data.csv` with columns:
| PR Name | PR Number | Created At | Merged At | # Comments | # Commits | # Files Changed |

Implement:
- REST API: `GET /repos/{owner}/{repo}/pulls`
- Include pagination (e.g., `?per_page=100&page=n`)
- For each PR, call sub-endpoints to gather commits, comments, and file changes.

### 🟨 From Jira
Store results in `data/jira_data.csv` with columns:
| Ticket Key | Summary | Type | Created | In Progress Timestamp | Done Timestamp |

Implement:
- REST API: `/rest/api/3/search?jql=project=OA`
- Use pagination via `startAt` and `maxResults`
- Track transitions from “In Progress” → “Done” using the `changelog` endpoint or status history.

---

## 🔄 Workflow – run_analysis.py
1. Load `.env` and `config.yaml`
2. Connect to Jira and GitHub using shared clients.
3. Fetch all relevant data using paginated requests.
4. Save clean CSVs under `Omnichannel_Customer_Account/data/`.
5. Print summary logs (e.g., “Fetched 523 PRs across 2 repositories”).
6. Handle retries and error logging gracefully.

---

## 📦 Shared Code Expectations

### `shared/github_client.py`
- Class `GitHubClient` with methods:
  - `get_pull_requests()`
  - `get_pr_comments()`
  - `get_pr_commits()`
  - `get_pr_file_changes()`
- Built-in pagination, retries, and data flattening.

### `shared/jira_client.py`
- Class `JiraClient` with methods:
  - `get_all_issues()`
  - `get_issue_transitions()`
- Uses API tokens and handles pagination.
- Extracts status transition timestamps.

### `shared/utils.py`
- Common helpers (pagination loops, CSV writing, logging setup).

---

## 🧠 AI Agent Objectives
- Plan and generate this full folder structure and boilerplate code.
- Implement secure API connections for both Jira and GitHub.
- Include working pagination logic.
- Output final data in CSV format.
- Ensure extensibility — adding a new project folder with config should require **no code change** in shared modules.

---

## ✅ Deliverables (End of Phase 1)
1. Complete folder structure as above.
2. Working Jira + GitHub connectors.
3. Successful data retrieval for:
   - Jira: Omnichannel Customer Account board.
   - GitHub: `agent-insight-hub` and `customer-gdpr-deletion`.
4. Generated CSV files for Jira and GitHub data.
5. Clean logs showing fetch completion.
