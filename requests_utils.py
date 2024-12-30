import re

def get_active_requests(metrics_text):
    active_requests_regex = r'request_count_total\{.*?\}\s+([\d\.]+)'
    
    match = re.search(active_requests_regex, metrics_text)
    if match:
        return float(match.group(1)) 
    return None