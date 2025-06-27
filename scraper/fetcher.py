import gzip
import requests
import os
import xml.etree.ElementTree as ET

def fetchXML(filename, url):
    
    if doesFileExist(filename):
        return
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch {url}")

    if url.endswith('.gz'):
        try:
            decompressed_data = gzip.decompress(response.content)
            saveFileAsBytes(filename, decompressed_data)
        except Exception as e:
            print(f"Failed to decompress and parse XML from {url}: {e}")
    else:
        try:
            saveFileAsBytes(filename, response.content)
        except Exception as e:
            print(f"Failed to parse XML from {url}: {e}")

def fetchHTML(filename, url):

    if doesFileExist(filename):
        return
    
    # Send a GET request to the URL
    response = requests.get(url)    

    # Write the content to the file
    saveFile(filename, response.text)

    print(f'Webpage downloaded and saved to {filename}')

def saveFile(filename, content):
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(content)

def saveFileAsBytes(filename, content):
    with open(filename, 'wb') as file:
        file.write(content)

def doesFileExist(filename):
    if os.path.isfile(filename):
        print(f'File exists, not download new version {filename}.')
        return True
    else:
        return False