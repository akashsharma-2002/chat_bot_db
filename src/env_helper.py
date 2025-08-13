# src/env_helper.py
"""
Environment Helper for Streamlit Cloud and Local Development
==========================================================

This module handles environment variables for both local development (.env file)
and Streamlit Cloud deployment (secrets.toml).
"""

import os
import streamlit as st
from dotenv import load_dotenv


def get_env_var(key: str, default: str = None) -> str:
    """
    Get environment variable from either Streamlit secrets or .env file.
    
    Args:
        key: Environment variable key
        default: Default value if key not found
        
    Returns:
        Environment variable value
    """
    # Try Streamlit secrets first (for cloud deployment)
    try:
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    
    # Fallback to standard environment variables (.env file for local)
    load_dotenv()  # Load .env file if it exists
    return os.getenv(key, default)


def load_database_config():
    """
    Load database configuration for both local and cloud environments.
    
    Returns:
        dict: Database configuration
    """
    return {
        'GITHUB_TOKEN': get_env_var('GITHUB_TOKEN'),
        'OPENAI_MODEL': get_env_var('OPENAI_MODEL', 'gpt-4o'),
        'HEALTH_CHECK_HOST_1': get_env_var('HEALTH_CHECK_HOST_1'),
        'HEALTH_CHECK_HOST_2': get_env_var('HEALTH_CHECK_HOST_2'),
        'HEALTH_CHECK_HOST_3': get_env_var('HEALTH_CHECK_HOST_3'),
        'HEALTH_CHECK_HOST_4': get_env_var('HEALTH_CHECK_HOST_4'),
        'HEALTH_CHECK_DB': get_env_var('HEALTH_CHECK_DB', 'inventory'),
        'HEALTH_CHECK_USER': get_env_var('HEALTH_CHECK_USER'),
        'HEALTH_CHECK_PASSWORD': get_env_var('HEALTH_CHECK_PASSWORD'),
        'HEALTH_CHECK_PORT': get_env_var('HEALTH_CHECK_PORT', '5432')
    }
