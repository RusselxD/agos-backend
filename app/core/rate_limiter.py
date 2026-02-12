from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


# Custom key function to get real IP behind proxy
def get_real_ip(request: Request) -> str:
    # Try to get the real IP from proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, get the first one (client IP)
        return forwarded_for.split(",")[0].strip()
    
    # Fallback to X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Final fallback to remote address
    return get_remote_address(request)


# Initialize the limiter with custom key function
limiter = Limiter(key_func=get_real_ip)