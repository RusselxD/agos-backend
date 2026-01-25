
def format_name_proper(name: str) -> str:
    """Format a name to proper case (first letter capitalized)."""
    return ' '.join(part.capitalize() for part in name.split())