import re 
def parse_report_details(message_content):
    pattern = re.compile(r"Reported User: (\d+)\nMessage: ([^\n]+)\nAbuse Type: ([^\n]+)\nAdditional Info: ([^\n]+)\nReporting User: (\d+)\nREPORT ID: ([^\n]+)", re.DOTALL)
    match = pattern.search(message_content)
    
    if not match:
        print("No match found")
        return None, None, None, None, None, None

    reported_user_id = match.group(1)
    message = match.group(2)
    abuse_type = match.group(3)
    additional_info = match.group(4)
    reporting_user_id = match.group(5)
    report_id = match.group(6)
    return int(reported_user_id), message, abuse_type, additional_info, int(reporting_user_id), report_id


def extract_report_id(message_content):
    match = re.search(r"REPORT ID: (\S+)", message_content)
    if match:
        return match.group(1)
    return None

def remove_report_id(message):
    pattern = re.compile(r"REPORT ID: \S+")
    cleaned_content = pattern.sub('', message).strip()
    return cleaned_content