import datetime
from datetime import timezone
from decimal import Decimal


def current_utc_timestamp() -> Decimal:
    dt = datetime.datetime.now(timezone.utc)
    utc_time = dt.replace(tzinfo=timezone.utc)
    utc_timestamp = utc_time.timestamp()

    return Decimal(utc_timestamp)
