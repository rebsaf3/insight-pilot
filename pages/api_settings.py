"""API key management page — create, view, revoke API keys."""

import streamlit as st

from auth.session import require_auth, get_current_workspace, user_has_permission
from config.settings import TIERS, BASE_URL
from db import queries
from services.api_key_service import create_api_key, revoke_api_key, list_api_keys, has_api_access


def show():
    user = require_auth()
    ws = get_current_workspace()
    if not ws:
        st.warning("Please select a workspace.")
        st.stop()

    if not user_has_permission(user.id, ws.id, "manage_api_keys"):
        st.error("You don't have permission to manage API keys.")
        st.stop()

    st.title("API Settings")

    # Check if API add-on is active
    tier_config = TIERS.get(ws.tier, TIERS["free"])
    if not tier_config.get("api_addon_available"):
        st.info("API access is available on Pro and Enterprise plans. Upgrade your plan to enable the REST API.")
        st.stop()

    if not has_api_access(ws.id):
        st.warning("The API Access add-on is not active for this workspace.")
        st.write("Enable the API Access add-on ($15/mo) from the **Billing** page to create and use API keys.")
        if st.button("Go to Billing"):
            st.switch_page("pages/billing.py")
        st.stop()

    tab_keys, tab_docs = st.tabs(["API Keys", "Quick Start"])

    # ------------------------------------------------------------------ Keys
    with tab_keys:
        st.subheader("API Keys")

        # Show newly created key
        if "new_api_key" in st.session_state:
            st.warning("Copy your API key now — it will not be shown again.")
            st.code(st.session_state["new_api_key"], language=None)
            if st.button("I've copied the key"):
                st.session_state.pop("new_api_key", None)
                st.rerun()
            st.divider()

        # Create new key
        with st.form("create_key_form"):
            st.markdown("### Create New API Key")
            key_name = st.text_input("Key Name", placeholder="e.g., Production API, CI/CD Pipeline")
            col1, col2, col3 = st.columns(3)
            with col1:
                perm_read = st.checkbox("Read", value=True, help="List projects, files, dashboards")
            with col2:
                perm_write = st.checkbox("Write", value=True, help="Create/update/delete resources")
            with col3:
                perm_analyze = st.checkbox("Analyze", value=True, help="Run AI analysis")
            submitted = st.form_submit_button("Create API Key", use_container_width=True)

        if submitted:
            if not key_name.strip():
                st.error("Please enter a name for the API key.")
            else:
                permissions = {
                    "read": perm_read,
                    "write": perm_write,
                    "analyze": perm_analyze,
                }
                full_key, key_id = create_api_key(ws.id, user.id, key_name.strip(), permissions)
                st.session_state["new_api_key"] = full_key
                st.rerun()

        # List existing keys
        st.divider()
        st.markdown("### Active Keys")
        keys = list_api_keys(ws.id)

        if not keys:
            st.info("No API keys created yet.")
        else:
            for k in keys:
                creator = queries.get_user_by_id(k.created_by)
                creator_name = creator.display_name if creator else "Unknown"

                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.write(f"**{k.name}**")
                    st.caption(f"Prefix: `{k.key_prefix}...`")
                with col2:
                    perms = k.permissions
                    perm_list = [p for p, v in perms.items() if v]
                    st.caption(f"Permissions: {', '.join(perm_list)}")
                    st.caption(f"Created by: {creator_name}")
                with col3:
                    st.caption(f"Created: {k.created_at[:10]}")
                    if k.last_used_at:
                        st.caption(f"Last used: {k.last_used_at[:16]}")
                    else:
                        st.caption("Last used: Never")
                with col4:
                    if st.button("Revoke", key=f"revoke_{k.id}", type="primary"):
                        revoke_api_key(k.id)
                        st.success(f"API key '{k.name}' revoked.")
                        st.rerun()

    # ------------------------------------------------------------------ Docs
    with tab_docs:
        st.subheader("Quick Start Guide")

        st.markdown(f"""
### Authentication

All API requests require an API key in the `Authorization` header:

```
Authorization: Bearer ip_xxxxxxxxxxxx
```

### Base URL

```
{BASE_URL}/api/v1
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/projects` | List all projects |
| `POST` | `/projects` | Create a project |
| `GET` | `/projects/{{id}}` | Get project details |
| `PUT` | `/projects/{{id}}` | Update a project |
| `DELETE` | `/projects/{{id}}` | Delete a project |
| `POST` | `/projects/{{id}}/upload` | Upload a file |
| `GET` | `/projects/{{id}}/files` | List files |
| `GET` | `/projects/{{id}}/dashboards` | List dashboards |
| `POST` | `/projects/{{id}}/dashboards` | Create dashboard |
| `GET` | `/dashboards/{{id}}` | Get dashboard with charts |
| `DELETE` | `/dashboards/{{id}}` | Delete dashboard |
| `POST` | `/analyze` | Run AI analysis |
| `GET` | `/workspace` | Workspace info |
| `GET` | `/workspace/usage` | Usage summary |

### Example: Upload & Analyze

```bash
# Upload a CSV file
curl -X POST {BASE_URL}/api/v1/projects/PROJECT_ID/upload \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "file=@data.csv"

# Run analysis
curl -X POST {BASE_URL}/api/v1/analyze \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{{"file_id": "FILE_ID", "prompt": "Create a bar chart of sales by region"}}'
```

### Rate Limits

- 100 requests per minute per API key
- File uploads: max {TIERS.get(ws.tier, TIERS['free'])['max_file_size_mb']} MB
""")


show()
