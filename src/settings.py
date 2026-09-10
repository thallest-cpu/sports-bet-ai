import os
from urllib.parse import urlparse


def secret(name, default=''):
    try:
        import streamlit as st
        value = st.secrets.get(name)
        if value is not None:
            return str(value)
    except Exception:
        pass
    return os.environ.get(name, default)


def licensed_photo(url, source):
    """An API URL alone is not proof of a publication license."""
    allowed = {s.strip() for s in secret('LICENSED_PHOTO_SOURCES').split(',') if s.strip()}
    host = urlparse(str(url or '')).hostname
    return str(url) if source in allowed and urlparse(str(url)).scheme == 'https' and host == 'media.api-sports.io' else ''
