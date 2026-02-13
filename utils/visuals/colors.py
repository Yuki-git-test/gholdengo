import random

def get_random_ghouldengo_color():
    """Returns a random pastel color inspired by Gholdengo or Gimmighoul."""
    # Pastel gold, yellow, and ghostly hues inspired by Gholdengo and Gimmighoul
    pastel_colors = [
        (255, 223, 120),  # Pastel gold
        (255, 236, 179),  # Light yellow
        (220, 210, 255),  # Soft lavender (ghostly)
        (255, 215, 230),  # Pinkish pastel
        (200, 255, 220),  # Mint pastel
        (255, 245, 200),  # Creamy yellow
        (210, 240, 255),  # Pale blue
        (255, 240, 220),  # Peach pastel
        (240, 255, 210),  # Light green
        (255, 220, 255),  # Pale magenta
    ]
    return random.choice(pastel_colors)
