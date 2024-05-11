import re 
def parse_report_details(message_content):
    # Regex to extract the report ID and reporting user ID
    pattern = re.compile(r"Reported User: (\d+)\n.*\nMessage: (\S+)\n.*\nAbuse Type: (\S+)\n.*\nReporting User: (\d+)")
    match = pattern.search(message_content)
    
    if not match:
        return None, None, None, None  # Or handle this case as an error or exception

    reported_user = match.group(1)
    message = match.group(2)
    abuse_type = match.group(3)
    reporting_user = match.group(4)
    return int(reported_user), message, abuse_type, int(reporting_user)

def extract_report_id(message_content):
    match = re.search(r"REPORT ID: (\S+)", message_content)
    if match:
        return match.group(1)
    return None

def remove_report_id(message):
    pattern = re.compile(r"REPORT ID: \S+")
    cleaned_content = pattern.sub('', message).strip()
    return cleaned_content