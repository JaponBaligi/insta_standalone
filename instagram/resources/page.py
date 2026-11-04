from ..client import GraphClient

def list_pages(client: GraphClient, fields: str = "id,name") -> dict:
    """List the Facebook Pages the token can access (helper to find a Page ID)."""
    return client.get("me/accounts", fields=fields)

def get_instagram_account(client: GraphClient, page_id: str) -> dict:
    """Get the Instagram business/creator account connected to a Facebook Page."""
    return client.get(
        page_id,
        fields="instagram_business_account{id,username,name}",
    )