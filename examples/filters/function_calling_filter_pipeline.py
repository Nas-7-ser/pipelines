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

        def return_marda(self) -> str:
            """
            Returns 'marda' when asked.
            """
            return "marda"

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

    def __init__(self):
        super().__init__()
        self.name = "My Tools and Space Data Retrieval Pipeline"
        self.valves = self.Valves(
            **{
                **self.valves.model_dump(),
                "pipelines": ["*"],  # Connect to all pipelines
            },
        )
        self.tools = self.Tools(self)

    async def on_startup(self):
        print(f"Pipeline startup: {self.name}")
        pass

    async def on_shutdown(self):
        print(f"Pipeline shutdown: {self.name}")
        pass

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

            # Retrieve space data
            api_data = self.retrieve_space_data()  # Using the Tools class method
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

            # Adding current time to the response
            current_time = self.tools.get_current_time()
            response_messages.append({
                "role": "assistant",
                "content": f"Current Time: {current_time}"
            })

            # Example of returning 'marda'
            marda_response = self.tools.return_marda()
            response_messages.append({
                "role": "assistant",
                "content": f"Marda Response: {marda_response}"
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
