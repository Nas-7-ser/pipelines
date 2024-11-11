import os
import aiohttp
import asyncio
from typing import List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, HttpUrl, ValidationError
from blueprints.function_calling_blueprint import Pipeline as FunctionCallingBlueprint
import logging
import re

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

        async def get_product_data(self, product_ids: Optional[List[int]] = None) -> Tuple[str, Optional[str]]:
            """
            Retrieve product data from the external API.
            If product_ids are provided, it fetches them individually.
            :param product_ids: List of product IDs to retrieve (optional).
            :return: A tuple containing the product info string and an optional image path.
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
                    raw_products = await asyncio.gather(*tasks)

                # Filter out any None results due to failed requests or validation errors
                raw_products = [prod for prod in raw_products if prod is not None]

                if raw_products:
                    structured_products = []
                    for raw_product in raw_products:
                        try:
                            # Validate and parse the raw product data
                            product = Product(**raw_product)
                            structured_product = self.structure_product_data(product)
                            structured_products.append(structured_product)
                        except ValidationError as ve:
                            logger.error(f"Validation error: {ve}")
                            continue

                    if structured_products:
                        formatted_output = self.format_products_to_markdown(structured_products)
                        return formatted_output, None  # Image handling can be adjusted as needed
                    else:
                        return "No valid products found after processing.", None
                else:
                    return "No products found or all retrievals failed.", None

            except Exception as e:
                logger.exception(f"An error occurred while retrieving product data: {str(e)}")
                return f"An error occurred while retrieving data: {str(e)}", None

        async def fetch_product(self, session: aiohttp.ClientSession, pid: int, base_url: str) -> Optional[dict]:
            """
            Fetch a single product by ID and return its raw data.
            :param session: The aiohttp client session.
            :param pid: The product ID.
            :param base_url: The base API URL.
            :return: The raw product data as a dictionary or None if failed.
            """
            try:
                url = f"{base_url}{pid}"
                headers = {
                    "Authorization": f"Bearer {self.pipeline.valves.PRODUCT_API_KEY}"
                }
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    logger.info(f"Successfully retrieved product ID {pid}")
                    return data
            except aiohttp.ClientResponseError as e:
                logger.error(f"Failed to retrieve product ID {pid}: {e.status} {e.message}")
                return None
            except Exception as e:
                logger.error(f"Error retrieving product ID {pid}: {str(e)}")
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

            logger.debug(f"Structured product data: {structured_product}")
            return structured_product

        def format_products_to_markdown(self, products: List[StructuredProduct]) -> str:
            """
            Format the list of structured products into a Markdown string.
            :param products: The list of StructuredProduct instances.
            :return: The formatted Markdown string.
            """
            markdown_output = "### Assistant Vente de Produits de Luxe\n\n**Rôle**:\n\nTon rôle est d’offrir une expérience utilisateur exceptionnelle en aidant les clients à découvrir et acheter des produits de luxe provenant de différentes marques prestigieuses. Tu disposes d'une liste de 14 produits répartis sur plusieurs marques. Lorsque l'utilisateur te fournit des critères de recherche, tu dois :\n\n- **Analyser les critères de l'utilisateur**.\n- **Sélectionner les produits les plus pertinents** en fonction de ces critères.\n- **Présenter ces produits avec des informations courtes** (nom du produit, description).\n- **Affichage de l'Image** : Affiche l'image directement dans la conversation en utilisant la syntaxe Markdown pour que l'image apparaisse dans le chat.\n  - **Image principale** :\n    ![Image principale](https://beruehrungspunkte.de/fileadmin/_processed_/4/8/csm_Vorschaubild_63ca715dbc.jpg)\n- **Informations Supplémentaires** : Si l'utilisateur le demande, donne plus de détails.\n- **Confirmation d'Intérêt** : Demande à l'utilisateur s'il est intéressé par le(s) produit(s).\n- **Procédure de Commande** : Si l'utilisateur est intéressé, fournis le lien de paiement.\n- **Clôture** : Remercie l'utilisateur et propose ton aide pour toute autre demande.\n\n**Marques et Produits Disponibles**:\n"

            for idx, product in enumerate(products, start=1):
                markdown_output += f"\n{idx}. **{product.name}**:\n\n"
                markdown_output += f"   - **Description**: {product.description}\n"
                markdown_output += f"   - **Image principale**:\n     ![Image principale]({product.image})\n"
                # If you have payment links or other fields, you can add them here

            # Add conversation instructions at the end
            markdown_output += "\n**Instructions de Conversation**:\n\n- **Accueil** : Commence toujours par une salutation chaleureuse.\n- **Compréhension des Besoins** : Demande les critères de recherche de l'utilisateur (type de produit, marque, budget, etc.).\n- **Sélection des Produits** : Choisis les produits les plus proches des critères de l'utilisateur.\n- **Présentation Courte** : Fournis des informations succinctes sur les produits sélectionnés (nom, description) et affiche les **images** directement dans la conversation.\n- **Affichage de l'Image** :\n  - **Image principale** :\n    ![Image principale](lien_vers_l'image_principale_du_produit_sélectionné)\n- **Informations Supplémentaires** : Si l'utilisateur le demande, donne plus de détails.\n- **Confirmation d'Intérêt** : Demande à l'utilisateur s'il est intéressé par le(s) produit(s).\n- **Procédure de Commande** : Si l'utilisateur est intéressé, fournis le lien de paiement et les étapes pour commander.\n  - **Lien de paiement** : [Acheter maintenant](lien_de_paiement_du_produit_sélectionné)\n- **Clôture** : Remercie l'utilisateur et propose ton aide pour toute autre demande.\n\n**Exemple de Dialogue**:\n\n**Assistant**: Bonjour ! Comment puis-je vous aider aujourd'hui à trouver des produits de luxe ?\n\n**Utilisateur**: Je cherche un sac à main de luxe d'environ 1 200 €, disponible en plusieurs couleurs, de préférence de la marque ChicHandbags.\n\n**Assistant**: Parfait ! J'ai justement un sac à main qui correspond à vos critères.\n\n- **Nom du produit**: Collection de Sacs à Main Multicolores\n- **Description**: Luxury product N11 : Collection de Sacs à Main Multicolores\n\n**Image principale**:\n![Image principale](https://cdn.prod.website-files.com/64dbb284e8fd858cb428eb91/64dbb284e8fd858cb428f0ec_State-of-Luxury-Retail-2022.jpeg)\n\nSouhaitez-vous plus d'informations sur ce produit ?\n\n**Utilisateur**: Oui, pouvez-vous me donner plus de détails ?\n\n**Assistant**: Bien sûr !\n\n- **Description détaillée**: La Collection de Sacs à Main Multicolores de ChicHandbags offre une variété de styles et de couleurs pour s'adapter à toutes vos tenues. Chaque sac est confectionné avec des matériaux de haute qualité, garantissant durabilité et élégance.\n\nÊtes-vous intéressé par ce sac à main ?\n\n**Utilisateur**: Oui, je veux l'acheter. Comment faire ?\n\n**Assistant**: Je suis ravi que ce sac vous plaise ! Vous pouvez le commander en suivant ce lien sécurisé :\n\n- **Lien de paiement**: [Acheter maintenant](https://buy.stripe.com/chichandbags1)\n\nSi vous avez besoin d'aide supplémentaire, n'hésitez pas à me le faire savoir."
            
            return markdown_output

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
            api_data, _ = await self.tools.get_product_data()  # No location filter
            logger.debug(f"API Data Retrieved: {api_data}")

            if api_data:
                response_message = f"{api_data}"
                response_messages.append({
                    "role": "assistant",
                    "content": response_message
                })
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
                "content": "Votre rôle ne vous permet pas de récupérer les données des produits."
            })

        # Append the product data or error message as the assistant's response
        if response_messages:
            body["messages"].extend(response_messages)
            logger.debug(f"Final response being returned: {body['messages']}")

        return body
