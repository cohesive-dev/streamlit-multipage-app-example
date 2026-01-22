import streamlit as st
import json
import base64
import os
from github import Github
from datetime import datetime
from bs4 import BeautifulSoup

from clients.smartlead.index import get_campaigns


# Constants
GITHUB_OWNER = "cohesive-dev"
GITHUB_REPO_NAME = "cohesive-ai-campaigns"
GITHUB_BRANCH = "main"
GITHUB_TOKEN = st.secrets.get("GITHUB_PAT_TOKEN", os.getenv("GITHUB_PAT_TOKEN"))


def html_to_text(html_content: str) -> str:
    """Convert HTML to plain text, preserving line breaks."""
    soup = BeautifulSoup(html_content, "lxml")

    for br in soup.find_all("br"):
        br.replace_with("\n")

    for div in soup.find_all("div"):
        div.replace_with(div.get_text() + "\n")

    return soup.get_text()


def get_github_repo():
    """Get the GitHub repository object."""
    if not GITHUB_TOKEN:
        st.error("GitHub token not found. Please set GITHUB_PAT_TOKEN in secrets.")
        return None

    g = Github(GITHUB_TOKEN)
    return g.get_repo(f"{GITHUB_OWNER}/{GITHUB_REPO_NAME}")


def get_file_commits(repo, campaign_id: int) -> list:
    """Get list of commits for a specific campaign file."""
    path = f"{campaign_id}.json"

    try:
        commits = repo.get_commits(path=path)
        commit_list = []
        for commit in commits:
            commit_list.append(
                {
                    "sha": commit.sha,
                    "short_sha": commit.sha[:7],
                    "message": commit.commit.message,
                    "date": commit.commit.author.date,
                    "author": commit.commit.author.name,
                }
            )
        return commit_list
    except Exception as e:
        st.error(f"Failed to get commits: {e}")
        return []


def get_file_at_commit(
    repo, campaign_id: int, commit_sha: str
) -> tuple[str | None, dict | None]:
    """Get file content at a specific commit."""
    path = f"{campaign_id}.json"

    try:
        file_content = repo.get_contents(path, ref=commit_sha)
        content = base64.b64decode(file_content.content).decode("utf-8")
        data = json.loads(content)
        return content, data
    except Exception as e:
        st.error(f"Failed to get file at commit: {e}")
        return None, None


def get_current_file_sha(repo, campaign_id: int) -> str | None:
    """Get the current SHA of the file for updating."""
    path = f"{campaign_id}.json"

    try:
        file = repo.get_contents(path, ref=GITHUB_BRANCH)
        return file.sha
    except Exception:
        return None


def commit_reverted_file(
    repo, campaign_id: int, content: str, commit_message: str
) -> bool:
    """Commit the reverted file to GitHub."""
    path = f"{campaign_id}.json"

    try:
        # Get current file SHA
        file_sha = get_current_file_sha(repo, campaign_id)

        if file_sha:
            repo.update_file(
                path=path,
                message=commit_message,
                content=content,
                sha=file_sha,
                branch=GITHUB_BRANCH,
            )
        else:
            repo.create_file(
                path=path,
                message=commit_message,
                content=content,
                branch=GITHUB_BRANCH,
            )
        return True
    except Exception as e:
        st.error(f"Failed to commit reverted file: {e}")
        return False


# Initialize session state
if "selected_campaign_id" not in st.session_state:
    st.session_state.selected_campaign_id = None
if "commits" not in st.session_state:
    st.session_state.commits = []
if "selected_commit" not in st.session_state:
    st.session_state.selected_commit = None
if "reverted_content" not in st.session_state:
    st.session_state.reverted_content = None
if "reverted_data" not in st.session_state:
    st.session_state.reverted_data = None

st.title("Revert Campaign Template")
st.markdown("Revert a campaign template to a previous version from Git history.")

# Step 1: Select Campaign
st.subheader("1. Select Campaign")

with st.spinner("Loading campaigns..."):
    campaigns = get_campaigns()

if campaigns:
    campaign_options = {f"{c.name} (ID: {c.id})": c.id for c in campaigns}
    selected_campaign_label = st.selectbox(
        "Select a campaign",
        options=[""] + list(campaign_options.keys()),
        index=0,
    )

    if selected_campaign_label:
        campaign_id = campaign_options[selected_campaign_label]

        if st.button("Load Edit History", type="primary"):
            repo = get_github_repo()
            if repo:
                with st.spinner("Loading edit history..."):
                    commits = get_file_commits(repo, campaign_id)

                if commits:
                    st.session_state.selected_campaign_id = campaign_id
                    st.session_state.commits = commits
                    st.session_state.selected_commit = None
                    st.session_state.reverted_content = None
                    st.success(
                        f"Found {len(commits)} commits for campaign {campaign_id}"
                    )
                else:
                    st.warning(
                        f"No commits found for campaign {campaign_id}. The file may not exist in the repository."
                    )

# Step 2: Select Commit
if st.session_state.commits:
    st.divider()
    st.subheader("2. Select Commit to Revert To")

    # Display commits in a table-like format
    for i, commit in enumerate(st.session_state.commits):
        col1, col2, col3 = st.columns([1, 3, 1])

        with col1:
            st.code(commit["short_sha"])

        with col2:
            st.markdown(f"**{commit['message']}**")
            st.caption(
                f"{commit['author']} • {commit['date'].strftime('%Y-%m-%d %H:%M:%S')}"
            )

        with col3:
            if st.button("Select", key=f"select_{commit['sha']}"):
                st.session_state.selected_commit = commit
                repo = get_github_repo()
                if repo:
                    with st.spinner("Loading file content..."):
                        content, data = get_file_at_commit(
                            repo, st.session_state.selected_campaign_id, commit["sha"]
                        )
                        st.session_state.reverted_content = content
                        st.session_state.reverted_data = data
                st.rerun()

        if i < len(st.session_state.commits) - 1:
            st.markdown("---")

# Step 3: Preview and Confirm
if st.session_state.selected_commit and st.session_state.reverted_content:
    st.divider()
    st.subheader("3. Preview and Confirm Revert")

    commit = st.session_state.selected_commit
    st.info(f"Reverting to commit: **{commit['short_sha']}** - {commit['message']}")

    # Show preview of the content
    st.markdown("#### Preview File Content")
    if st.session_state.reverted_data:
        data = st.session_state.reverted_data

        # Display sequences and variants in readable text format
        for index, seq in enumerate(data.get("sequences", [])):
            st.markdown(f"### Sequence {index + 1}")
            st.markdown(f"**Subject:** {seq.get('subject', 'N/A')}")

            variants = seq.get("variants", [])
            if variants:
                for variant in variants:
                    st.markdown(
                        f"**Variant {variant.get('variant_label', 'N/A')}** (ID: {variant.get('id', 'N/A')})"
                    )
                    st.markdown(f"Subject: {variant.get('subject', 'N/A')}")

                    # Convert HTML to text for display
                    email_body = variant.get("email_body", "")
                    text_content = html_to_text(email_body)

                    # Use a styled container for better readability
                    st.markdown(
                        f'<div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 12px; font-family: monospace; white-space: pre-wrap; max-height: 300px; overflow-y: auto; color: #212529;">{text_content}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                # No variants, show main email body
                email_body = seq.get("email_body", "")
                text_content = html_to_text(email_body)
                st.markdown(
                    f'<div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 12px; font-family: monospace; white-space: pre-wrap; max-height: 300px; overflow-y: auto; color: #212529;">{text_content}</div>',
                    unsafe_allow_html=True,
                )

            st.divider()
    else:
        st.code(st.session_state.reverted_content, language="json")

    # Commit message input
    default_message = f"Revert campaign {st.session_state.selected_campaign_id} to commit {commit['short_sha']}"
    commit_message = st.text_input(
        "Commit Message",
        value=default_message,
        placeholder="Enter commit message for the revert",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", type="secondary"):
            st.session_state.selected_commit = None
            st.session_state.reverted_content = None
            st.session_state.reverted_data = None
            st.rerun()

    with col2:
        if st.button("Confirm Revert", type="primary"):
            if not commit_message:
                st.error("Please enter a commit message")
            else:
                repo = get_github_repo()
                if repo:
                    with st.spinner("Committing reverted file..."):
                        success = commit_reverted_file(
                            repo,
                            st.session_state.selected_campaign_id,
                            st.session_state.reverted_content,
                            commit_message,
                        )

                    if success:
                        st.success(
                            f"✅ Successfully reverted campaign {st.session_state.selected_campaign_id} to commit {commit['short_sha']}"
                        )

                        # Clear state
                        st.session_state.selected_commit = None
                        st.session_state.reverted_content = None
                        st.session_state.reverted_data = None
                        st.session_state.commits = []
                    else:
                        st.error("Failed to commit the reverted file")
