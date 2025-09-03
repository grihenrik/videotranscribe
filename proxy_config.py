#!/usr/bin/env python3
"""
Proxy Configuration for YouTube Access
=====================================

This file contains proxy configuration options to help bypass YouTube restrictions.
"""

import os

# =============================================================================
# PUBLIC PROXY SERVICES (Use with caution - may be slow or unreliable)
# =============================================================================

# Free SOCKS proxies (example - replace with actual working proxies)
PUBLIC_SOCKS_PROXIES = [
    # "socks5://103.150.209.217:1080",
    # "socks5://103.85.22.17:1080", 
    # "socks5://103.85.22.94:1080",
]

# Free HTTP proxies (example - replace with actual working proxies)
PUBLIC_HTTP_PROXIES = [
    # "http://103.150.209.217:8080",
    # "http://103.85.22.17:8080",
]

# =============================================================================
# PROXY SERVICE PROVIDERS (Paid/Premium options)
# =============================================================================

# ProxyMesh (paid service)
PROXYMESH_CONFIG = {
    "enabled": False,
    "username": os.getenv("PROXYMESH_USERNAME"),
    "password": os.getenv("PROXYMESH_PASSWORD"),
    "endpoints": [
        "rotating-residential.proxymesh.com:31280",
        "us-wa.proxymesh.com:31280",
    ]
}

# Bright Data (formerly Luminati) - paid service
BRIGHT_DATA_CONFIG = {
    "enabled": False,
    "username": os.getenv("BRIGHT_DATA_USERNAME"), 
    "password": os.getenv("BRIGHT_DATA_PASSWORD"),
    "endpoint": "brd.superproxy.io:22225"
}

# SmartProxy - paid service
SMARTPROXY_CONFIG = {
    "enabled": False,
    "username": os.getenv("SMARTPROXY_USERNAME"),
    "password": os.getenv("SMARTPROXY_PASSWORD"), 
    "endpoint": "gate.smartproxy.com:10000"
}

# =============================================================================
# CONFIGURATION FUNCTIONS
# =============================================================================

def get_proxy_url():
    """
    Get the configured proxy URL based on environment and settings.
    
    Priority order:
    1. Environment variable YOUTUBE_PROXY
    2. Configured premium proxy service
    3. Public proxy list
    4. No proxy (None)
    
    Returns:
        str or None: Proxy URL or None if no proxy configured
    """
    
    # Check environment variable first
    env_proxy = os.getenv("YOUTUBE_PROXY")
    if env_proxy:
        return env_proxy
    
    # Check premium proxy services
    if PROXYMESH_CONFIG["enabled"] and PROXYMESH_CONFIG["username"]:
        endpoint = PROXYMESH_CONFIG["endpoints"][0]
        username = PROXYMESH_CONFIG["username"]
        password = PROXYMESH_CONFIG["password"]
        return f"http://{username}:{password}@{endpoint}"
    
    if BRIGHT_DATA_CONFIG["enabled"] and BRIGHT_DATA_CONFIG["username"]:
        endpoint = BRIGHT_DATA_CONFIG["endpoint"]
        username = BRIGHT_DATA_CONFIG["username"]
        password = BRIGHT_DATA_CONFIG["password"]
        return f"http://{username}:{password}@{endpoint}"
    
    if SMARTPROXY_CONFIG["enabled"] and SMARTPROXY_CONFIG["username"]:
        endpoint = SMARTPROXY_CONFIG["endpoint"]
        username = SMARTPROXY_CONFIG["username"]
        password = SMARTPROXY_CONFIG["password"]
        return f"http://{username}:{password}@{endpoint}"
    
    # Try public proxies (if any are configured)
    if PUBLIC_SOCKS_PROXIES:
        return PUBLIC_SOCKS_PROXIES[0]
    
    if PUBLIC_HTTP_PROXIES:
        return PUBLIC_HTTP_PROXIES[0]
    
    # No proxy configured
    return None

def test_proxy(proxy_url):
    """
    Test if a proxy is working by making a simple request.
    
    Args:
        proxy_url (str): Proxy URL to test
        
    Returns:
        bool: True if proxy is working, False otherwise
    """
    import requests
    import urllib3
    from urllib3.exceptions import InsecureRequestWarning
    
    # Disable SSL warnings for proxy testing
    urllib3.disable_warnings(InsecureRequestWarning)
    
    try:
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # Test with a simple request
        response = requests.get(
            'http://httpbin.org/ip',
            proxies=proxies,
            timeout=10,
            verify=False
        )
        
        if response.status_code == 200:
            print(f"✅ Proxy working: {proxy_url}")
            print(f"   IP: {response.json().get('origin', 'Unknown')}")
            return True
        else:
            print(f"❌ Proxy failed: {proxy_url} (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Proxy failed: {proxy_url} (Error: {e})")
        return False

# =============================================================================
# SETUP INSTRUCTIONS
# =============================================================================

SETUP_INSTRUCTIONS = """
Proxy Setup Instructions:
========================

1. ENVIRONMENT VARIABLE (Recommended for testing):
   export YOUTUBE_PROXY="socks5://your-proxy:port"
   # or
   export YOUTUBE_PROXY="http://username:password@proxy:port"

2. PREMIUM PROXY SERVICES (Recommended for production):
   
   a) ProxyMesh:
      - Sign up at https://proxymesh.com/
      - Set environment variables:
        export PROXYMESH_USERNAME="your-username"
        export PROXYMESH_PASSWORD="your-password"
      - Enable in proxy_config.py: PROXYMESH_CONFIG["enabled"] = True
   
   b) Bright Data:
      - Sign up at https://brightdata.com/
      - Set environment variables:
        export BRIGHT_DATA_USERNAME="your-username"
        export BRIGHT_DATA_PASSWORD="your-password"
      - Enable in proxy_config.py: BRIGHT_DATA_CONFIG["enabled"] = True
   
   c) SmartProxy:
      - Sign up at https://smartproxy.com/
      - Set environment variables:
        export SMARTPROXY_USERNAME="your-username" 
        export SMARTPROXY_PASSWORD="your-password"
      - Enable in proxy_config.py: SMARTPROXY_CONFIG["enabled"] = True

3. FREE PROXIES (Not recommended for production):
   - Find working proxies from sites like:
     * https://free-proxy-list.net/
     * https://www.proxy-list.download/
   - Add them to PUBLIC_SOCKS_PROXIES or PUBLIC_HTTP_PROXIES lists
   - Note: Free proxies are often unreliable and slow

4. LOCAL PROXY (Advanced users):
   - Set up your own proxy server (Squid, 3proxy, etc.)
   - Use SSH tunneling: ssh -D 1080 user@server
   - Set: export YOUTUBE_PROXY="socks5://127.0.0.1:1080"

Testing:
========
Run this file directly to test proxy configuration:
    python proxy_config.py
"""

if __name__ == "__main__":
    print("Proxy Configuration Test")
    print("=" * 50)
    
    proxy = get_proxy_url()
    if proxy:
        print(f"Configured proxy: {proxy}")
        print("Testing proxy...")
        test_proxy(proxy)
    else:
        print("No proxy configured.")
        print("\n" + SETUP_INSTRUCTIONS)
