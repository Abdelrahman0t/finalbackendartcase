from gradio_client import Client


    # Define categories (keeping the same categories for reference)
CATEGORIES = [
        "Anime & Manga",
        "TV Shows & Movies",
        "Video Games",
        "Cartoons & Animated Characters",
        "Pop Culture & Music",
        "K-Pop & Idol Groups",
        "Celebrities & Influencers",
        "Floral & Botanical",
        "Scenery & Landscapes",
        "Abstract & Minimalist",
        "Cats & Dogs",
        "Wildlife & Exotic Animals",
        "Fantasy Creatures",
        "Football & Basketball",
        "Extreme Sports",
        "Fitness & Gym",
        "Motivational & Inspirational",
        "Funny & Meme-Based",
        "Dark & Gothic",
        "Cyberpunk & Sci-Fi",
        "Glitch & Vaporwave",   
        "AI & Robotics",
        "Flags & National Pride",
        "Traditional Art",
        "Astrology & Zodiac Signs"
]

def classify_design(design):
    """
    Classifies a design into a category and extracts top 3 colors using the Hugging Face Space API.
    Args:
        design (Design): A Design instance containing an image URL.
    Returns:
        dict: {'category': ..., 'color1': ..., 'color2': ..., 'color3': ...}
    """
    try:
        # Initialize the Gradio client
        client = Client("https://abdelrahmanasdlf-artcase22.hf.space")
        print("Sending request to API with URL:", design.image_url)
        # Make the prediction using the client
        result = client.predict(
            design.image_url,  # The image URL
            api_name="/predict"  # The API endpoint name
        )
        print("API Response:", result)
        # Expecting result to be a list: [category, color1, color2, color3]
        if result and isinstance(result, (list, tuple)) and len(result) >= 4:
            return {
                'category': result[0],
                'color1': result[1],
                'color2': result[2],
                'color3': result[3],
            }
        else:
            print("Unexpected result format from API:", result)
            return {
                'category': 'unknown',
                'color1': '',
                'color2': '',
                'color3': '',
            }
    except Exception as e:
        print(f"Error in classifying design: {e}")
        import traceback
        print("Full error traceback:")
        print(traceback.format_exc())
        return {
            'category': 'unknown',
            'color1': '',
            'color2': '',
            'color3': '',
        }
