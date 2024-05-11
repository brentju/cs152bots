import re 
def parse_report_details(message_content):
    details = {
        "reported_user": None,
        "message": None,
        "abuse_type": None,
        "additional_info": None,
        "reporting_user": None,
        "report_id": None
    }

    lines = message_content.split('\n')
    print(lines)
    for line in lines:
        if line.startswith("Reported User:"):
            print(line.split("Reported User: "))
            details["reported_user"] = int(line.split("Reported User: ")[1])
        elif line.startswith("Message:"):
            details["message"] = line.split("Message: ")[1]
        elif line.startswith("Abuse Type:"):
            details["abuse_type"] = line.split("Abuse Type: ")[1]
        elif line.startswith("Additional Info:"):
            details["additional_info"] = line.split("Additional Info: ")[1]
        elif line.startswith("Reporting User:"):
            details["reporting_user"] = int(line.split("Reporting User: ")[1])
        elif line.startswith("REPORT ID:"):
            details["report_id"] = line.split("REPORT ID: ")[1]

    return details




def extract_report_id(message_content):
    match = re.search(r"REPORT ID: (\S+)", message_content)
    if match:
        return match.group(1)
    return None

def remove_report_id(message):
    pattern = re.compile(r"REPORT ID: \S+")
    cleaned_content = pattern.sub('', message).strip()
    return cleaned_content