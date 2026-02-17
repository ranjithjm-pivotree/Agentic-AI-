import re
from fastapi import FastAPI, Request, HTTPException
from jira import JIRA

# ==========================================
# 1. JIRA CONFIGURATION
# ==========================================
JIRA_SERVER = "https://your-domain.atlassian.net"
JIRA_EMAIL = "your-email@domain.com"
# Generate this in your Atlassian Account Settings -> Security -> API Tokens
JIRA_API_TOKEN = "your-jira-api-token"  

# Initialize the Jira Client
jira = JIRA(
    server=JIRA_SERVER,
    basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN)
)

# ==========================================
# 2. FASTAPI SETUP
# ==========================================
app = FastAPI(title="Agentic QA Listener")

@app.post("/webhook/pr-merged")
async def pr_merged_webhook(request: Request):
    """
    This endpoint listens for POST requests from your Git provider.
    """
    # Parse the incoming JSON payload
    payload = await request.json()
    
    # Extract the PR title and branch name (Assuming GitHub payload structure)
    try:
        if "pull_request" in payload:
            pr_action = payload["action"]
            pr_title = payload["pull_request"]["title"]
            branch_name = payload["pull_request"]["head"]["ref"]
            is_merged = payload["pull_request"]["merged"]
            
            # GUARD: Only proceed if the PR was actually merged, not just closed
            if pr_action == "closed" and not is_merged:
                return {"status": "ignored", "reason": "PR was closed without merging."}
            
            # Combine title and branch to search for the Jira ticket ID
            search_text = f"{pr_title} {branch_name}"
        else:
            return {"status": "ignored", "reason": "Not a Pull Request event."}
            
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid Webhook Payload structure.")

    # ==========================================
    # 3. EXTRACT JIRA TICKET ID
    # ==========================================
    # Regex looks for standard Jira formats: 2+ uppercase letters, a hyphen, and numbers (e.g., PROJ-123)
    jira_match = re.search(r'[A-Z]{2,}-\d+', search_text)
    
    if not jira_match:
        print("⚠️ No Jira ticket found in PR title or branch.")
        return {"status": "ignored", "reason": "No Jira ticket ID found."}
        
    jira_ticket_id = jira_match.group(0)
    print(f"\n🎯 [TRIGGER] PR Merged! Found Jira Ticket: {jira_ticket_id}")

    # ==========================================
    # 4. FETCH JIRA REQUIREMENTS
    # ==========================================
    try:
        # Fetch the issue from Jira
        issue = jira.issue(jira_ticket_id)
        
        summary = issue.fields.summary
        description = issue.fields.description
        
        # Note: If your "Acceptance Criteria" is a custom field in Jira, 
        # it will look something like this instead of 'description':
        # acceptance_criteria = issue.fields.customfield_10034 
        
        print(f"📋 Ticket Summary: {summary}")
        print(f"📄 Description/Requirements:\n{description}\n")
        
    except Exception as e:
        print(f"❌ Failed to fetch Jira ticket: {e}")
        raise HTTPException(status_code=500, detail="Jira API Fetch Error")

    # ---> STEP 3 (Git Pull) & STEP 4 (LLM Test Generation) WILL GO HERE <---

    return {
        "status": "success", 
        "ticket": jira_ticket_id, 
        "message": "Requirements gathered. Ready for AI generation."
    }