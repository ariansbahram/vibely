import secrets

# Keeps each user's Spotify token in memory, keyed by a random session ID.
# Everything here is lost when the server restarts.
_sessions = {}


def create_session(token_info):
    session_id = secrets.token_urlsafe(32)   # long random "ticket number"
    _sessions[session_id] = token_info
    return session_id


def get_token(session_id):
    return _sessions.get(session_id)          # None if the ticket isn't found


def update_token(session_id, token_info):
    _sessions[session_id] = token_info        # used when a token is refreshed
