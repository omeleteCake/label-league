from supabase import Client, create_client

from common.config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


_admin_client: Client | None = None


def get_admin_client() -> Client:
    global _admin_client

    if _admin_client is None:
        _admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    return _admin_client
