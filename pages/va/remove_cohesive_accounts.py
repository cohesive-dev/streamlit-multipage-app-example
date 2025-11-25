import streamlit as st


def remove_cohesive_accounts():
    st.title("Remove Cohesive Accounts")

    # Fetch all organizations
    conn = st.connection("postgresql", type="sql")
    organizations = conn.query(
        "SELECT id, name FROM platform_organizations ORDER BY name;"
    )

    if len(organizations) == 0:
        st.write("No organizations found.")
        return

    # Select organization
    org_name_to_id = {row["name"]: row["id"] for _, row in organizations.iterrows()}

    selected_org_name = st.selectbox(
        "Select the organization to remove accounts for:", list(org_name_to_id.keys())
    )

    selected_org_id = org_name_to_id[selected_org_name]

    # First button triggers confirmation
    if st.button(f"Remove ALL accounts for '{selected_org_name}'"):
        st.warning(
            f"Are you sure you want to permanently delete ALL accounts for "
            f"**{selected_org_name}**?"
        )

        # Second button: final confirmation with spinner
        if st.button("Yes, delete all accounts now"):
            with st.spinner("Deleting accounts…"):
                conn.execute(
                    """
                    DELETE FROM account
                    WHERE platform_organization_id = :org_id
                    """,
                    {"org_id": selected_org_id},
                )

            st.success(f"All accounts for **{selected_org_name}** have been removed.")


remove_cohesive_accounts()
