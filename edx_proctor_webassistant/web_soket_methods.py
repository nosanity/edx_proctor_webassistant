"""
Working with notifications
"""
from notifications.client import ProctorNotificator


def send_notification(data, channel, action=None):
    """
    Send message to subscribers
    """
    res = data.copy()
    res['course_event_id'] = int(channel)
    res['action'] = action if action else 'change_status'
    ProctorNotificator.notify(res)
