import os
import requests
from typing import List, Optional, Union, Generator, Iterator
from datetime import datetime
from pydantic import BaseModel, HttpUrl, ValidationError
import logging
import re

# Import the language model function
# Adjust the import based on your Open WebUI setup
# from openai_conversation import generate_assistant_reply

class Product(BaseModel):
    content: str
    description: str
    image_url: HttpUrl

class StructuredProduct(BaseModel):
    name: str
    description: str
    image: HttpUrl

class Pipeline:
    class Valves(BaseModel):
        BASE_API_URL: str = "https://8b33b8d0-de52-4c5c-a799-f440d0d6112a-00-1eqvns0ze6d2x.picard.replit.dev/data/"  # Replace with your actual API URL

    def __init__(self):
        self.name = "Product Tools Pipeline"
        self.valves = self.Valves(
            BASE_API_URL=os.getenv("BASE_API_URL", "https://8b33b8d0-de52-4c5c-a799-f440d0d6112a-00-1eqvns0ze6d2x.picard.replit.dev/data/")
        )

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("pipeline.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(self.name)

    def on_startup(self):
        # This function is called when the server is started.
        self.logger.info(f"on_startup: {__name__}")

    def on_shutdown(self):
        # This function is called when the server is stopped.
        self.logger.info(f"on_shutdown: {__name__}")

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict
    ) -> Union[str, Generator, Iterator]:
        """
        Main pipeline method to process requests.
        """
        self.logger.info("Pipe function called - Processing Request")
        self.logger.debug(f"user_message: {user_message}")
        self.logger.debug(f"model_id: {model_id}")
        self.logger.debug(f"messages: {messages}")
        self.logger.debug(f"body: {body}")

        # Retrieve product data
        product_data_markdown = self.get_product_data()
        self.logger.debug(f"Product Data Retrieved: {product_data_markdown}")

        if product_data_markdown:
            # Construct the assistant context with role, instructions, and product data in Markdown
            assistant_context = f"""
You are an assistant helping customers discover and purchase luxury products from prestigious brands.

Use the following product data to assist the user:

{product_data_markdown}

Remember to follow the instructions and provide responses in a conversational manner.

"""

            # Add the assistant context as a system message
            conversation = [
                {"role": "system", "content": assistant_context}
            ]

            # Add the previous messages to the conversation
            conversation.extend(messages)

            # Call the language model to generate the assistant's reply
            assistant_reply = self.generate_assistant_reply(conversation)
        else:
            assistant_reply = "I'm sorry, but I couldn't retrieve product information at this time."

        # Return the assistant's reply
        return assistant_reply

    def get_product_data(self, product_ids: Optional[List[int]] = None) -> Optional[str]:
        """
        Retrieve product data from the external API.
        """
        if not self.valves.BASE_API_URL:
            return None

        if product_ids is None:
            product_ids = [1, 2]  # Update as needed

        base_api_url = self.valves.BASE_API_URL

        try:
            raw_products = []
            for pid in product_ids:
                raw_product = self.fetch_product(pid, base_api_url)
                if raw_product is not None:
                    raw_products.append(raw_product)

            if raw_products:
                structured_products = []
                for raw_product in raw_products:
                    try:
                        # Validate and parse the raw product data
                        product = Product(**raw_product)
                        structured_product = self.structure_product_data(product)
                        structured_products.append(structured_product)
                    except ValidationError as ve:
                        self.logger.error(f"Validation error: {ve}")
                        continue

                if structured_products:
                    formatted_output = self.format_products_to_markdown(structured_products)
                    return formatted_output
                else:
                    return None
            else:
                return None

        except Exception as e:
            self.logger.exception(f"An error occurred while retrieving product data: {str(e)}")
            return None

    def fetch_product(self, pid: int, base_url: str) -> Optional[dict]:
        """
        Fetch a single product by ID and return its raw data.
        """
        try:
            url = f"{base_url}{pid}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"Successfully retrieved product ID {pid}")
            return data
        except requests.HTTPError as e:
            self.logger.error(f"Failed to retrieve product ID {pid}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving product ID {pid}: {str(e)}")
            return None

    def structure_product_data(self, product: Product) -> StructuredProduct:
        """
        Transform raw product data into structured product data.
        """
        # Extract product name from description using regex
        name_match = re.search(r':\s*(.+)', product.description)
        name = name_match.group(1).strip() if name_match else "Unknown Product"

        # Assign the image URL directly
        image = product.image_url

        # Use content as a general category or tag (optional)
        description = f"{product.content} - {product.description}"

        # Construct the StructuredProduct
        structured_product = StructuredProduct(
            name=name,
            description=description,
            image=image
        )

        self.logger.debug(f"Structured product data: {structured_product}")
        return structured_product

    def format_products_to_markdown(self, products: List[StructuredProduct]) -> str:
        """
        Format the list of structured products into a Markdown string.
        """
        markdown_output = "### Product Catalog\n\n"

        # Add each product to the markdown output
        for idx, product in enumerate(products, start=1):
            markdown_output += f"**{idx}. {product.name}**\n"
            markdown_output += f"- **Description**: {product.description}\n"
            markdown_output += f"- **Image**:\n\n  ![Image]({product.image})\n\n"

        return markdown_output

    def generate_assistant_reply(self, conversation: List[dict]) -> str:
        """
        Generate the assistant's reply using the language model.
        """
        # This function should call the language model API provided by Open WebUI
        # Adjust the function call based on your Open WebUI setup
        # For example, if using the 'completion' function:

        # Import the completion function from Open WebUI
        from completion import openai_completion  # Adjust the import as needed

        # Call the completion function with the conversation
        assistant_reply = openai_completion(
            messages=conversation,
            model="gpt-3.5-turbo",  # Replace with your model ID
            max_tokens=500,
            temperature=0.7,
        )

        return assistant_reply
