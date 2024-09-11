
import os
import requests
from typing import Literal, List, Optional
from datetime import datetime

from pydantic import BaseModel
from blueprints.function_calling_blueprint import Pipeline as FunctionCallingBlueprint


class Pipeline(FunctionCallingBlueprint):
    class Valves(FunctionCallingBlueprint.Valves):
        pipelines: List[str] = ["*"]  # Connect to all pipelines
        target_user_roles: List[str] = ["admin", "user"]  # Roles allowed for data retrieval
        SPACE_API_KEY: str = ""

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

        def get_space_data(self, location: Optional[str] = None) -> str:
            """
            Retrieve space data from the external API.
            If location is provided, it can filter spaces based on location.
            :param location: The location to filter spaces (optional).
            :return: The available space data.
            """
            if self.pipeline.valves.SPACE_API_KEY == "":
                return "Space API Key not set, please set it up."

            # Define the parameters for the request
            params = {
                "apikey": self.pipeline.valves.SPACE_API_KEY,  # If your API requires an API key
                "location": location if location else "",  # Optional location filter
            }

            api_url = "https://7a340f9a-48e7-44ed-8852-14cd58697a9c-00-3ohyjqpej24i8.worf.replit.dev/api/spaces"  # Replace with the actual space API URL

            try:
                response = requests.get(api_url, params=params)
                response.raise_for_status()  # Raises an HTTPError for bad responses
                data = response.json()

                # Debugging the response to check its structure
                print(f"Data received from API: {data}")

                # Handling case where data is a list of lists
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    # Extracting values from the list using indices
                    space_info = f"ID: {data[0][0]}, Location: {data[0][2]}, Price: ${data[0][3]} per month, Type: {data[0][6]}"
                    return space_info
                else:
                    return "No available spaces found."
            except requests.exceptions.HTTPError as e:
                return f"Error occurred: {str(e)}"
            except Exception as e:
                return f"An error occurred while retrieving data: {str(e)}"

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
        self.name = "My Tools Pipeline"
        self.valves = self.Valves(
            **{
                **self.valves.model_dump(),
                "pipelines": ["*"],  # Connect to all pipelines
                "SPACE_API_KEY": os.getenv("SPACE_API_KEY", ""),  # Set this key through environment variables
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

            # Retrieve space data (optional location filter can be used)
            api_data = self.tools.get_space_data(location="Downtown")  # Example with location filter
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
                    "content": "No available spaces found."
                })

            # Adding current time to the response
            current_time = self.tools.get_current_time()
            response_messages.append({
                "role": "assistant",
                "content": f"Current Time: {current_time}"
            })

        else:
            response_messages.append({
                "role": "assistant",
                "content": "Your role does not permit space data retrieval."
            })

        # Append the space data or error message as the assistant's response
        if response_messages:
            body["messages"].extend(response_messages)
            print(f"Final response being returned: {body['messages']}")

        return body
