import os
import requests
from typing import List, Optional, Union, Generator, Iterator
from datetime import datetime
from pydantic import BaseModel, HttpUrl, ValidationError
import logging
import re

# Define the Product model based on the API response
class Product(BaseModel):
    content: str
    description: str
    image_url: HttpUrl

# Enhanced Product model for structured data
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

    def get_current_time(self) -> str:
        """
        Get the current time.
        :return: The current time as a string.
        """
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        return f"Current Time = {current_time}"

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict
    ) -> Union[str, Generator, Iterator]:
        """
        Main pipeline method to process requests.
        :param user_message: The user's message.
        :param model_id: The model identifier.
        :param messages: List of messages in the conversation.
        :param body: The request body.
        :return: A string or generator to be sent back to the user.
        """
        self.logger.info("Pipe function called - Processing Request")
        self.logger.debug(f"user_message: {user_message}")
        self.logger.debug(f"model_id: {model_id}")
        self.logger.debug(f"messages: {messages}")
        self.logger.debug(f"body: {body}")

        # Retrieve product data
        api_data = self.get_product_data()
        self.logger.debug(f"API Data Retrieved: {api_data}")

        if api_data:
            response_message = f"{api_data}"
        else:
            response_message = "No available products found."

        # Adding current time to the response
        current_time = self.get_current_time()
        response_message += f"\n\n{current_time}"

        # Return the response message
        return response_message

    def get_product_data(self, product_ids: Optional[List[int]] = None) -> Optional[str]:
        """
        Retrieve product data from the external API.
        If product_ids are provided, it fetches them individually.
        :param product_ids: List of product IDs to retrieve (optional).
        :return: The product info string or None if error.
        """
        if not self.valves.BASE_API_URL:
            return "API URL not set, please set it up."

        if product_ids is None:
            product_ids = [1, 2, 3]  # Update as needed

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
                    return "No valid products found after processing."
            else:
                return "No products found or all retrievals failed."

        except Exception as e:
            self.logger.exception(f"An error occurred while retrieving product data: {str(e)}")
            return f"An error occurred while retrieving data: {str(e)}"

    def fetch_product(self, pid: int, base_url: str) -> Optional[dict]:
        """
        Fetch a single product by ID and return its raw data.
        :param pid: The product ID.
        :param base_url: The base API URL.
        :return: The raw product data as a dictionary or None if failed.
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
        :param product: The raw product data.
        :return: A StructuredProduct instance.
        """
        # Extract product name from description using regex
        name_match = re.search(r':\s*(.+)', product.description)
        name = name_match.group(1).strip() if name_match else "Unknown Product"

        # Assign the image URL directly
        image = product.image_url

        # Use content as a general category or tag (optional)
        description = product.content + " - " + product.description

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
        :param products: The list of StructuredProduct instances.
        :return: The formatted Markdown string.
        """
        markdown_output = "### Assistant Vente de Produits de Luxe\n\n**Rôle**:\n\nTon rôle est d’offrir une expérience utilisateur exceptionnelle en aidant les clients à découvrir et acheter des produits de luxe provenant de différentes marques prestigieuses.\n\n"

        # Add each product to the markdown output
        for idx, product in enumerate(products, start=1):
            markdown_output += f"{idx}. **{product.name}**:\n"
            markdown_output += f"   - **Description**: {product.description}\n"
            markdown_output += f"   - **Image principale**:\n     ![Image principale]({product.image})\n\n"

        # Append conversation instructions and examples
        markdown_output += (
            "**Instructions de Conversation**:\n\n"
            "- **Accueil** : Commence toujours par une salutation chaleureuse.\n"
            "- **Compréhension des Besoins** : Demande les critères de recherche de l'utilisateur (type de produit, marque, budget, etc.).\n"
            "- **Sélection des Produits** : Choisis les produits les plus proches des critères de l'utilisateur.\n"
            "- **Présentation Courte** : Fournis des informations succinctes sur les produits sélectionnés (nom, description) et affiche les **images** directement dans la conversation.\n"
            "- **Affichage de l'Image** :\n"
            "  - **Image principale** :\n"
            "    ![Image principale](lien_vers_l'image_principale_du_produit_sélectionné)\n"
            "- **Informations Supplémentaires** : Si l'utilisateur le demande, donne plus de détails.\n"
            "- **Confirmation d'Intérêt** : Demande à l'utilisateur s'il est intéressé par le(s) produit(s).\n"
            "- **Procédure de Commande** : Si l'utilisateur est intéressé, fournis le lien de paiement et les étapes pour commander.\n"
            "  - **Lien de paiement** : [Acheter maintenant](lien_de_paiement_du_produit_sélectionné)\n"
            "- **Clôture** : Remercie l'utilisateur et propose ton aide pour toute autre demande.\n\n"
            "**Exemple de Dialogue**:\n\n"
            "**Assistant**: Bonjour ! Comment puis-je vous aider aujourd'hui à trouver des produits de luxe ?\n\n"
            "**Utilisateur**: Je cherche un sac à main de luxe d'environ 1 200 €, disponible en plusieurs couleurs, de préférence de la marque ChicHandbags.\n\n"
            "**Assistant**: Parfait ! J'ai justement un sac à main qui correspond à vos critères.\n\n"
            "- **Nom du produit**: Collection de Sacs à Main Multicolores\n"
            "- **Description**: Luxury product N11 : Collection de Sacs à Main Multicolores\n\n"
            "**Image principale**:\n![Image principale](https://cdn.prod.website-files.com/64dbb284e8fd858cb428eb91/64dbb284e8fd858cb428f0ec_State-of-Luxury-Retail-2022.jpeg)\n\n"
            "Souhaitez-vous plus d'informations sur ce produit ?\n"
        )

        return markdown_output
