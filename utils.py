from datetime import date, timedelta
from typing import Optional

def proxima_segunda(base: Optional[date] = None) -> date:
    if base is None:
        base = date.today()
    dow = base.weekday()
    add = (7 - dow) % 7 or 7
    return base + timedelta(days=add)
