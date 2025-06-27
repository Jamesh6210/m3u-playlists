import json
from bs4 import BeautifulSoup

def extract_payload_from_file(file_path):
    """
    Extracts the payload object from the provided HTML file.

    Parameters:
    file_path (str): The path to the HTML file.

    Returns:
    dict: The payload object as a dictionary.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract the initial path
        react_app_tag = soup.find('react-app')
        if react_app_tag:
            initial_path = react_app_tag['initial-path']
            if initial_path:
                initial_path = initial_path.split('/tv-logo/tv-logos/tree/main/')[0] + '/tv-logo/tv-logos/tree/main/'
                initial_path = initial_path.replace('/tree', '')

        # Find the script tag with the payload
        script_tag = soup.find('script', {'type': 'application/json', 'data-target': 'react-app.embeddedData'})

        if script_tag:
            # Extract the JSON content from the script tag
            json_content = script_tag.string
            # Load it into a Python dictionary
            data = json.loads(json_content)
            # Extract the payload object
            payload = data.get('payload', {})

            # Append the initial path to the payload object
            if initial_path:
                payload['initial_path'] = initial_path

            return payload
        else:
            print('Script tag with the payload not found.')
            return {}

    except FileNotFoundError:
        print(f'The file {file_path} does not exist.')
        return {}
    except Exception as e:
        print(f'An error occurred: {e}')
        return {}

def search_tree_items(search_string, json_obj):
    """
    Searches the JSON object's tree.items for matches of each part of the search string.

    Parameters:
    search_string (str): The string to search for.
    json_obj (dict): The JSON object to search within.

    Returns:
    list: A list of matches found.
    """
    matches = []
    search_words = search_string.lower().split()

    items = json_obj.get('tree', {}).get('items', [])

    for item in items:
        imgName = item['name'].lower()
        for word in search_words:
            if word in imgName:
                if imgName not in matches:
                    matches.append({'id':item, 'source':''})

    return matches

# Example usage
if __name__ == "__main__":
    file_path = 'example.html'  # Replace with your actual HTML file path
    payload = extract_payload_from_file(file_path)
    search_string = 'custom directory'
    matches = search_tree_items(search_string, payload)
    print(json.dumps(matches, indent=2))