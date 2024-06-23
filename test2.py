import requests

# Set the base URL for your API
BASE_URL = 'http://127.0.0.1:8001/uploads/file_uploads'

# Define the GUID and file information
guid = 'dummy_file.zip'  # Replace with an actual GUID from your database

# Headers for the requests
headers = {
    'Content-Type': 'application/json',
}

# Function to update the priority
def update_priority(guid, priority):
    url = f'{BASE_URL}/update_priority/'
    data = {
        'guid': guid,
        'priority': priority,
    }
    response = requests.post(url, json=data, headers=headers)
    print('Update Priority Response:', response.json())

# Function to update the status
def update_status(guid, status):
    url = f'{BASE_URL}/update_status/'
    data = {
        'guid': guid,
        'status': status,
    }
    response = requests.post(url, json=data, headers=headers)
    print('Update Status Response:', response.json())

# # Test updating the priority
# print("Testing Update Priority API")
# update_priority(guid, 1)  # Set priority to 1

# Test pausing the upload
print("\nTesting Pause Upload API")
update_status(guid, 'paused')

# # Test resuming the upload
# print("\nTesting Resume Upload API")
# update_status(guid, 'resume')

# # Test canceling the upload
# print("\nTesting Cancel Upload API")
# update_status(guid, 'cancel')
