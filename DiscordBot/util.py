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