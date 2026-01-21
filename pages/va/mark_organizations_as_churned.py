import streamlit as st
from sqlalchemy import text


def get_active_organizations():
    conn = st.connection("postgresql", type="sql")
    query = """
SELECT *
  FROM platform_organizations
  where paused = false
"""
    campaigns = conn.query(query, ttl=0)
    return list(campaigns.to_dict(orient="records"))


def pause_platform_organizations(
    org_ids: list[str] | None = None,
) -> int:
    """
    Returns number of rows updated
    """
    params = {}
    query_str = """
      UPDATE platform_organizations
      SET "paused" = true,
        "updatedAt" = NOW()
      WHERE 1 = 1
    """
    if org_ids:
        query_str += " AND id = ANY(:org_ids)"
        params["org_ids"] = org_ids

    query = text(query_str)

    conn = st.connection("postgresql", type="sql")
    with conn.session as session:
        result = session.execute(query, params)
        updated_count = result.rowcount
        session.commit()

    return updated_count


st.title("Pause Platform Organizations")

orgs = get_active_organizations()

# Create a multiselect dropdown for organization selection
org_names = [f"{org['name']} (ID: {org['id']})" for org in orgs]
selected_orgs = st.multiselect(
    "Select organizations to pause",
    options=org_names,
    help="Search and select one or more organizations",
)

# Extract org IDs from selected items
selected_org_ids = []
if selected_orgs:
    for selected in selected_orgs:
        # Extract ID from the format "Name (ID: 123)"
        org_id = selected.split("ID: ")[1].rstrip(")")
        selected_org_ids.append(org_id)

    st.write(f"Selected {len(selected_org_ids)} organization(s)")

confirm = st.checkbox("I understand this will pause ALL selected organizations")

if st.button("Pause organizations", disabled=not confirm):
    updated = pause_platform_organizations(org_ids=selected_org_ids)
    st.success(f"Paused {updated} organizations")
