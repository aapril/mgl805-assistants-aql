from supabase import create_client, Client
import pipe_src as config

# Initiallize the client tool
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# Deriving the endpoint types
def derive_endpoint_type(http_method: str) -> str:
    if not http_method:
        return "UNKNOWN"
    
    method = http_method.upper()
    if method == "GET": 
        return "READ"
    elif method in ["POST", "PUT", "PATCH", "DELETE"]: 
        return "MUTATION"
    return "UNKNOWN"