from datetime import datetime


def generate_tracking_code(created_at: datetime, sequence: int) -> str:
    return f"KRG-{created_at:%Y%m%d}-{sequence:06d}"
