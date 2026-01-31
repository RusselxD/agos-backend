from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize the limiter
# key_func determines how users are identified (by IP address here)
limiter = Limiter(key_func=get_remote_address)
