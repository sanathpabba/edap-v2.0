import datetime as dt


def is_bday(d):
    return d.weekday() < 5


def bdays(start, end):
    d, out = start, []
    while d <= end:
        if is_bday(d):
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def add_bdays(d, n):
    while n > 0:
        d += dt.timedelta(days=1)
        if is_bday(d):
            n -= 1
    return d
