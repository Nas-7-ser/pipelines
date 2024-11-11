import os
import aiohttp
import asyncio
from typing import Literal, List, Optional
from datetime import datetime
from pydantic import BaseModel, HttpUrl, ValidationError
from blueprints.function_calling_blueprint import Pipeline as FunctionCallingBlueprint
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Product(BaseModel):
    content: str
    description: str
    image_url: HttpUrl

class Pipeline(FunctionCallingBlueprint):
    class Valves(FunctionCallingBlueprint.Valves):
        pipelines: List[str] = ["*"]  # Connect to all pipelines
        target_user_roles: List[str] = ["admin", "user"]  # Roles allowed for data retrieval
        PRODUCT_API_KEY: str = ""  # Updated from SPACE_API_KEY

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

        async def get_product_data(self, product_ids: Optional[List[int]] = None) -> (str, Optional[str]):
            """
            Retrieve product data from the external API.
            If product_ids are provided, it fetches them individually.
            :param product_ids: List of product IDs to retrieve (optional).
            :return: A tuple containing the product info string and the image path (if any).
            """
            if self.pipeline.valves.PRODUCT_API_KEY == "":
                return "Product API Key not set, please set it up.", None

            if product_ids is None:
                # Define your product IDs here. This can be dynamically fetched if your API provides such an endpoint.
                product_ids = [1, 2]  # Update as needed

            base_api_url = "https://8b33b8d0-de52-4c5c-a799-f440d0d6112a-00-1eqvns0ze6d2x.picard.replit.dev/data/"

            try:
                async with aiohttp.ClientSession() as session:
                    tasks = [self.fetch_product(session, pid, base_api_url) for pid in product_ids]
                    products = await asyncio.gather(*tasks)

                # Filter out any None results due to failed requests or validation errors
                products = [prod for prod in products if prod is not None]

                if products:
                    formatted_products = []
                    for product in products:
                        product_info = (
                            f"Content: {product.content}, "
                            f"Description: {product.description}, "
                            f"Image URL: {product.image_url}"
                        )
                        formatted_products.append(product_info)
                        logger.debug(f"Formatted product info: {product_info}")

                    formatted_output = "\n".join(formatted_products)
                    return formatted_output, None  # Image handling can be adjusted as needed
                else:
                    return "No products found or all retrievals failed.", None

            except Exception as e:
                logger.exception(f"An error occurred while retrieving product data: {str(e)}")
                return f"An error occurred while retrieving data: {str(e)}", None

        async def fetch_product(self, session: aiohttp.ClientSession, pid: int, base_url: str) -> Optional[Product]:
            """
            Fetch a single product by ID and validate it.
            :param session: The aiohttp client session.
            :param pid: The product ID.
            :param base_url: The base API URL.
            :return: A Product instance or None if failed.
            """
            try:
                url = f"{base_url}{pid}"
                headers = {
                    "Authorization": f"Bearer {self.pipeline.valves.PRODUCT_API_KEY}"
                }
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    product = Product(**data)
                    return product
            except aiohttp.ClientResponseError as e:
                logger.error(f"Failed to retrieve product ID {pid}: {e.status} {e.message}")
                return None
            except ValidationError as ve:
                logger.error(f"Validation error for product ID {pid}: {ve}")
                return None
            except Exception as e:
                logger.error(f"Error retrieving product ID {pid}: {str(e)}")
                return None

        def download_image(self, image_url: str) -> Optional[str]:
            """
            Download an image from the provided URL and save it locally.
            :param image_url: The URL of the image to download.
            :return: The local path of the saved image or None if failed.
            """
            try:
                # Assuming the image URL is already a direct link
                response = requests.get(image_url)
                response.raise_for_status()  # Raise an error for bad responses

                # Extract the image name from the URL and save it locally
                image_name = image_url.split("/")[-1]
                image_path = os.path.join("images", image_name)

                # Ensure the directory exists
                if not os.path.exists("images"):
                    os.makedirs("images")

                # Write the image data to the file
                with open(image_path, "wb") as f:
                    f.write(response.content)

                logger.info(f"Image downloaded and saved at {image_path}")
                return image_path

            except Exception as e:
                logger.error(f"Failed to download image: {str(e)}")
                return None

        def calculator(self, equation: str) -> str:
            """
            Calculate the result of an equation.
            :param equation: The equation to calculate.
            """
            try:
                result = eval(equation)
                return f"{equation} = {result}"
            except Exception as e:
                logger.error(f"Calculator error: {str(e)}")
                return "Invalid equation"

    def __init__(self):
        super().__init__()
        self.name = "Product Tools Pipeline"  # Updated name
        self.valves = self.Valves(
            **{
                **self.valves.model_dump(),
                "pipelines": ["*"],  # Connect to all pipelines
                "PRODUCT_API_KEY": os.getenv("PRODUCT_API_KEY", ""),  # Updated from SPACE_API_KEY
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
        logger.info("Inlet function called - Processing Request")
        logger.debug(f"Request body: {body}")
        logger.debug(f"User info: {user}")

        # Initialize a response message list
        response_messages = []

        # Check user role and perform actions
        if user.get("role", "unknown") in self.valves.target_user_roles:
            logger.info("User role verified")

            # Retrieve product data (no location filter needed unless applicable)
            api_data, image_path = await self.tools.get_product_data()  # No location filter
            logger.debug(f"API Data Retrieved: {api_data}")

            if api_data:
                response_message = f"Available Product Details:\n{api_data}"
                response_messages.append({
                    "role": "assistant",
                    "content": response_message
                })

                # If you want to handle images, you can iterate and download them
                # For simplicity, we're not downloading images here. If needed, adjust accordingly.

            else:
                response_messages.append({
                    "role": "assistant",
                    "content": "No available products found."
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
                "content": "Your role does not permit product data retrieval."
            })

        # Append the product data or error message as the assistant's response
        if response_messages:
            body["messages"].extend(response_messages)
            logger.debug(f"Final response being returned: {body['messages']}")

        return body
