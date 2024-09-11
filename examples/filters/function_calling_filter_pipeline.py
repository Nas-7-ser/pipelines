import os
import requests
from typing import Literal, List, Optional
from datetime import datetime
from pydantic import BaseModel

from blueprints.function_calling_blueprint import Pipeline as FunctionCallingBlueprint

class Pipeline(FunctionCallingBlueprint):
    class Valves(FunctionCallingBlueprint.Valves):
        # Custom parameters can be added here
        pipelines: List[str] = ["*"]  # Connect to all pipelines
        target_user_roles: List[str] = ["admin", "user"]  # Roles allowed for data retrieval

    class Tools:
        def __init__(self, pipeline) -> None:
            self.pipeline = pipeline

        def get_current_time(self) -> str:
            """
            Get the current time.

            :return: The current time.
            """
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            return f"Current Time = {current_time}"

        def calculator(self, equation: str) -> str:
            """
            Calculate the result of an equation.

            :param equation: The equation to calculate.
            """
            try:
                result = eval(equation)
                return f"{equation} = {result}"
            except Exception as e:
                print(e)
                return "Invalid equation"

        def retrieve_space_data(self) -> str:
            """
            Retrieve space data from the external API.
            :return: The space data as a string.
            """
            try:
                api_url = "https://7a340f9a-48e7-44ed-8852-14cd58697a9c-00-3ohyjqpej24i8.worf.replit.dev/api/spaces"
                print(f"Calling API at: {api_url}")
                response = requests.get(api_url)

                if response.status_code == 200:
                    data = response.json()
                    if data and isinstance(data, list) and len(data) > 0:
                        space_info = f"ID: {data[0][0]}, Location: {data[0][2]}, Price: ${data[0][3]} per month, Type: {data[0][6]}"
                        return space_info
                    else:
                        return "No space data available."
                else:
                    return f"Error: Failed to retrieve data. Status code: {response.status_code}"
            except Exception as e:
                return f"Error occurred while retrieving data: {str(e)}"

        def send_chat_message(self, message: str, user_id: int) -> str:
            """
            Sends a chat message to the chat API.
            """
            api_url = "http://127.0.0.1:59721/api/v1/chats/create"  # Adjust to your endpoint
            data = {"message": message, "user_id": user_id}
            headers = {
                "Content-Type": "application/json",
                # Add Authorization header if required
                # "Authorization": "Bearer YOUR_API_KEY"
            }

            try:
                response = requests.post(api_url, headers=headers, json=data)
                response.raise_for_status()  # Raises an HTTPError for bad responses
                return response.text
            except requests.exceptions.HTTPError as err:
                return f"Error: {err}"

    def __init__(self):
        super().__init__()
        self.name = "My Tools Pipeline"
        self.valves = self.Valves(
            **{
                **self.valves.model_dump(),
                "pipelines": ["*"],  # Connect to all pipelines
            },
        )
        self.tools = self.Tools(self)

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """
        Main inlet function to process requests.
        :param body: The request body.
        :param user: User information.
        :return: The modified body with responses.
        """
        print(f"Inlet function called - Processing Request")
        print(f"Request body: {body}")
        print(f"User info: {user}")

        # Initialize a response message list
        response_messages = []

        # Check user role and perform actions
        if user.get("role", "unknown") in self.valves.target_user_roles:
            print(f"User role verified")

            # Sending a chat message (example usage)
            chat_response = self.tools.send_chat_message("Hello, this is a test message", user.get("id", 1))
            print(f"Chat response: {chat_response}")

            response_messages.append({
                "role": "assistant",
                "content": f"Chat API Response: {chat_response}"
            })

            # Retrieve space data (example usage)
            api_data = self.tools.retrieve_space_data()  # Using the Tools class method
            print(f"API Data Retrieved: {api_data}")  # Debugging API response
            if api_data:
                response_message = f"Available Space Details: {api_data}"
                response_messages.append({
                    "role": "assistant",
                    "content": response_message
                })
            else:
                response_messages.append({
                    "role": "assistant",
                    "content": "No available spaces found or error occurred."
                })

        else:
            response_messages.append({
                "role": "assistant",
                "content": "Your role does not permit data retrieval."
            })

        # Append the space data or error message as the assistant's response
        if response_messages:
            body["messages"].extend(response_messages)
            print(f"Final response being returned: {body['messages']}")

        return body
