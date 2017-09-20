from django.http import HttpResponse

MAP = {}


def http_status(status, reason_phrase=None):
    cls = MAP.get(status)
    if not cls:
        cls = type('Http%s' % status, (HttpResponse,), {'status_code': status})
        MAP[status] = cls

    if reason_phrase:
        rcls = MAP.get((status, reason_phrase))
        if not rcls:
            rcls = type('Http%s' % status, (cls,), {'reason_phrase': reason_phrase})
            MAP[(status, reason_phrase)] = rcls
        cls = rcls

    return cls()
