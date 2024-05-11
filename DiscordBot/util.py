import re 
def parse_report_details(message_content):
    # Regex to extract the report ID and reporting user ID
    pattern = re.compile(r"Report ID: (\S+)\n.*\nReporting User: (\d+)")
    match = pattern.search(message_content)
    
    if not match:
        return None, None  # Or handle this case as an error or exception

    report_id = match.group(1)
    reporting_user_id = match.group(2)
    
    return report_id, reporting_user_id

def extract_report_id(message_content):
    match = re.search(r"REPORT ID: (\S+)", message_content)
    if match:
        return match.group(1)
    return None

def remove_report_id(message):
    pattern = re.compile(r"Report ID: \S+")
    cleaned_content = pattern.sub('', message).strip()
    return cleaned_content