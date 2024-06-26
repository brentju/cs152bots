import re
import numpy as np

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
    for line in lines:
        line = line.strip()
        if line.startswith("Reported User:"):
            details["reported_user"] = int(line.split("Reported User: ")[1])
        elif line.startswith("Message:"):
            if len(line.split("Message: ")) > 1:
                details["message"] = line.split("Message: ")[1]
            else:
                details["message"] = "No message found"
        elif line.startswith("Abuse Type:"):
            details["abuse_type"] = line.split("Abuse Type: ")[1]
        elif line.startswith("Additional Info:"):
            details["additional_info"] = line.split("Additional Info: ")[1]
        elif line.startswith("Reporting User:"):
            if line.split("Reporting User: ")[1] == "automatic":
                details["reporting_user"] = "automatic"
            else:
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

def download_image(image_url, save_path):
    try:
        # Send a HTTP GET request to the image URL
        response = requests.get(image_url)

        # Check if the request was successful
        if response.status_code == 200:
            # Open the image from the response content
            image = Image.open(BytesIO(response.content))

            # Save the image to the specified path
            image.save(save_path)
            print(f"Image successfully saved to {save_path}")
        else:
            print(f"Failed to retrieve the image. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")
