import os
import requests
from typing import List, Optional
from pydantic import BaseModel

class Pipeline:
    class Valves(BaseModel):
        pipelines: List[str] = ["*"]
        target_user_roles: List[str] = ["admin", "user"]  # Roles allowed for data retrieval

    def __init__(self):
        self.type = "filter"
        self.name = "Space Data Retrieval Pipeline"
        self.valves = self.Valves()

    async def on_startup(self):
        print(f"Pipeline startup: {self.name}")
        pass

    async def on_shutdown(self):
        print(f"Pipeline shutdown: {self.name}")
        pass

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        print(f"Inlet function called - Processing Request")
        print(f"Request body: {body}")
        print(f"User info: {user}")

        # Log the roles being checked
        print(f"Expected roles: {self.valves.target_user_roles}")
        print(f"User role: {user.get('role', 'unknown')}")

        # Initialize a response message list
        response_messages = []

        # Only retrieve space data for specific user roles
        if user.get("role", "unknown") in self.valves.target_user_roles:
            print(f"User role verified, retrieving space data...")
            api_data = self.retrieve_space_data()
            print(f"API Data Retrieved: {api_data}")  # Debugging API response
            if api_data:
                response_message = f"Available Space Details: {api_data}"
                response_messages.append({
                    "role": "assistant",
                    "content": response_message
                })
                print(f"Response message added: {response_message}")
            else:
                response_message = "No available spaces found or error occurred."
                response_messages.append({
                    "role": "assistant",
                    "content": response_message
                })
                print(f"Response message added: {response_message}")
        else:
            print(f"User role does not permit data retrieval.")
            response_messages.append({
                "role": "assistant",
                "content": "Your role does not permit space data retrieval."
            })

        # Append the space data or error message as the assistant's response
        if response_messages:
            body["messages"].extend(response_messages)
            print(f"Final response being returned: {body['messages']}")

        return body

    def retrieve_space_data(self) -> str:
        """Function to retrieve space data from the external API"""
        try:
            api_url = "https://7a340f9a-48e7-44ed-8852-14cd58697a9c-00-3ohyjqpej24i8.worf.replit.dev/api/spaces"
            print(f"Calling API at: {api_url}")
            response = requests.get(api_url)

            if response.status_code == 200:
                data = response.json()
                print(f"Data retrieved from API: {data}")  # Debugging API response
                if data and isinstance(data, list) and len(data) > 0:
                    # Format the data into a human-readable string
                    space_info = f"ID: {data[0][0]}, Location: {data[0][2]}, Price: ${data[0][3]} per month, Type: {data[0][6]}"
                    print(f"Formatted space info: {space_info}")
                    return space_info
                else:
                    print(f"Empty or malformed data from API: {data}")
                    return "No space data available."
            else:
                print(f"Failed to retrieve space data. Status code: {response.status_code}")
                return f"Error: Failed to retrieve data. Status code: {response.status_code}"
        except Exception as e:
            print(f"Error occurred while calling the API: {str(e)}")
            return f"Error occurred while retrieving data: {str(e)}"
