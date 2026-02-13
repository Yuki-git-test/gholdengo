import random


def random_ga_thumbnail_url() -> str:
    """
    Returns one random thumbnail URL from a predefined list.
    """
    thumbnails = [
        "https://media.discordapp.net/attachments/1406782694423007316/1417844170202025994/image.png?ex=68cbf5c8&is=68caa448&hm=70727e95d18fad89719f8c9b214edc3b906176022f5842c45da4154de4fed584&=&format=webp&quality=lossless&width=576&height=576",
        "https://media.discordapp.net/attachments/1406782694423007316/1408018282174349383/image.png?ex=68cbcf36&is=68ca7db6&hm=30f86d3d979265d91dc40f4aef6ac29e9e0618bcaca73c9acc2117367f991d5c&=&format=webp&quality=lossless&width=576&height=576",
        "https://media.discordapp.net/attachments/1406782694423007316/1408018176381292595/image.png?ex=68cbcf1c&is=68ca7d9c&hm=eba3aec2db964b82886cdd7a64e0a3c4ca4511b03dfa485492e6eb8f81f2d2a8&=&format=webp&quality=lossless&width=576&height=576",
        "https://media.discordapp.net/attachments/1406782694423007316/1408018097696149584/image.png?ex=68cbcf0a&is=68ca7d8a&hm=a08e0969c63d85f78aecd077671c7323f69c0565c8a94314e44af21519d170c8&=&format=webp&quality=lossless&width=576&height=576",
        "https://media.discordapp.net/attachments/1406782694423007316/1406783300269375591/image.png?ex=68cbee4b&is=68ca9ccb&hm=61960f33d9b99ce7c535c4e9ad96f5d2de7c4017cbc6277930afc3267e6c1934&=&format=webp&quality=lossless&width=576&height=576",
        "https://media.discordapp.net/attachments/1406782694423007316/1406783240030654594/image.png?ex=68cbee3d&is=68ca9cbd&hm=6fef118c6ffc32090a1831a8e814f5743af636a1f0c9a3690420716e31561f24&=&format=webp&quality=lossless&width=576&height=576",
        "https://media.discordapp.net/attachments/1406782694423007316/1406783180815728680/image.png?ex=68cbee2f&is=68ca9caf&hm=f4f6c803c9262a20b0ad3416befdaba0f6cd9d0b18554073994dd531c053b86c&=&format=webp&quality=lossless&width=576&height=576",
        "https://media.discordapp.net/attachments/1406782694423007316/1406783136813023262/image.png?ex=68cbee24&is=68ca9ca4&hm=bd848b0de9429a8711cc1b7c74f4af20685b06ae74b2f6f99c06b5460b5d360f&=&format=webp&quality=lossless&width=576&height=576",
    ]
    return random.choice(thumbnails)
