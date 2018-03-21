"""
Working with notifications
"""
from notifications.client import ProctorNotificator


def send_notification(data, channel):
    """
    Send message to subscribers
    """
    res = data.copy()
    res['course_event_id'] = int(channel)
    ProctorNotificator.notify(res)
