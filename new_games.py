"""Additional interactive Discord games for dreamscape Bot.

The original bot keeps its existing game and moderation implementation in
``main.py``.  This module owns the newer multiplayer games so their session
state and content catalog stay isolated from the existing systems.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Awaitable, Callable

import discord
from discord import app_commands


CONTENT_STORE_PATH = Path("game_content.json")
CONTENT_GAME_KEYS = (
    "mostlikelyto",
    "twotruthsonelie",
    "hotseat",
    "emojidecode",
    "guesstheplayer",
    "trivia",
    "memebattle",
    "captionthis",
)
CONTENT_GAME_LABELS = {
    "mostlikelyto": "Most Likely To",
    "twotruthsonelie": "Two Truths and One Lie",
    "hotseat": "Hot Seat",
    "emojidecode": "Emoji Decode",
    "guesstheplayer": "Guess The Player",
    "trivia": "Trivia",
    "memebattle": "Meme Battle",
    "captionthis": "Caption This",
}
CATALOG_GAME_KEYS = (
    "mostlikelyto",
    "hotseat",
    "emojidecode",
    "trivia",
    "memebattle",
    "captionthis",
)
CATALOG_GAME_CHOICES = [
    app_commands.Choice(name=CONTENT_GAME_LABELS[key], value=key)
    for key in CATALOG_GAME_KEYS
]


def _combination_records(
    category: str,
    stems: list[str],
    endings: list[str],
    template: str,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for stem in stems:
        for ending in endings:
            records.append(
                {
                    "id": f"{category}-{len(records) + 1:03d}",
                    "prompt": template.format(stem=stem, ending=ending),
                }
            )
    return records


def _build_seed_content() -> dict[str, list[dict[str, object]]]:
    most_likely_stems = [
        "bring a suspiciously specific snack to a meeting",
        "turn a five-minute plan into a three-hour adventure",
        "become friends with a stranger in a queue",
        "accidentally start a group tradition",
        "win an argument using only confidence",
        "forget why they opened the fridge",
        "make a spreadsheet for a completely unnecessary decision",
        "laugh at the exact wrong dramatic moment",
        "have the best excuse for being late",
        "adopt a fictional character as a role model",
        "send a message to the wrong chat and survive it",
        "challenge the rules of a board game",
        "discover a shortcut that makes everything longer",
        "bring a tiny trophy to celebrate a normal achievement",
        "turn a quiet hangout into a tournament",
        "make a playlist for a situation that lasts two minutes",
        "remember every detail except the important one",
        "be trusted with the group secret",
        "make a rival team laugh",
        "choose the chaotic dialogue option",
        "become famous for an oddly useful skill",
        "name an inanimate object and defend the name",
        "accidentally volunteer the whole group",
        "solve a puzzle by ignoring the instructions",
        "have a legendary school or gaming story",
    ]
    most_likely_endings = [
        "during a totally normal Tuesday",
        "before the first snack break",
        "if the group had one hour to prepare",
        "when nobody else expected it",
        "in a server-wide challenge",
        "while trying to look responsible",
        "after saying they had a simple plan",
        "on a school trip or gaming night",
        "and insist it was intentional",
        "then explain it with a straight face",
    ]
    hotseat_stems = [
        "the small thing that instantly improves your mood",
        "a fictional world you would visit for one week",
        "the game mechanic you would add to real life",
        "a food opinion you will defend forever",
        "your funniest harmless misunderstanding",
        "the best advice you have actually used",
        "a skill you would download instantly",
        "a school subject you would redesign",
        "the most underrated everyday object",
        "a team role you naturally take",
        "a tiny achievement you are proud of",
        "the most chaotic group project idea",
        "a song that belongs in your personal trailer",
        "the fictional character you would invite to dinner",
        "a rule you would make for a perfect weekend",
        "the most useful thing you know about technology",
        "a hobby you would try with unlimited time",
        "the best way to spend an unexpected day off",
        "a mystery you would love to solve",
        "the most memorable username you have seen",
        "an invention that should already exist",
        "a harmless challenge you would give the group",
        "the funniest thing to put on a trophy",
        "a place you would explore with a trusted team",
        "the most surprising compliment you have received",
    ]
    hotseat_endings = [
        "and give the first answer that comes to mind",
        "without naming any private information",
        "as if you were explaining it to a documentary crew",
        "in one sentence and one sound effect",
        "with the most honest harmless answer",
        "as a friendly debate topic",
        "like you are pitching it to the group",
        "and include one oddly specific detail",
        "with a completely unnecessary dramatic backstory",
        "then let the group ask one follow-up",
    ]
    meme_stems = [
        "the moment the group project says it is due in ten minutes",
        "when the game tutorial explains the same button for the fourth time",
        "your brain opening one more tab at midnight",
        "the friend who says they know a shortcut",
        "when the snack bag is mysteriously empty",
        "a loading screen that has become part of the family",
        "the server member who volunteers before hearing the plan",
        "when your perfectly organized notes become abstract art",
        "the final boss of a completely ordinary errand",
        "the face you make when the Wi-Fi reconnects",
        "a character entering the chat with no context",
        "when someone says the meeting will be quick",
        "the dramatic reveal of a missing pencil",
        "the teammate who says trust me",
        "when the playlist reaches the one song everyone knows",
        "your last brain cell during a quiz",
        "the friend who brings a spreadsheet to a casual vote",
        "when the harmless prank becomes a team tradition",
        "the moment the group discovers a new inside joke",
        "an NPC trying to understand the group chat",
        "when the alarm says five more minutes",
        "the first day after learning a new shortcut",
        "the face of someone who chose the dialogue option",
        "a tiny problem receiving a cinematic soundtrack",
        "the group chat after somebody says I have an idea",
    ]
    meme_endings = [
        "Write the caption that belongs under this scene.",
        "Give it a clean one-line reaction.",
        "Add the most dramatic harmless explanation.",
        "Caption it like a nature documentary.",
        "Write the response that would make the group quote it later.",
        "Give it a gaming achievement-style caption.",
        "Make it sound like a breaking-news headline.",
        "Write the caption with maximum deadpan energy.",
        "Turn it into a school-safe reaction image caption.",
        "Give the scene a title nobody can forget.",
    ]
    caption_stems = [
        "A penguin confidently presenting a tiny clipboard",
        "A cat staring at a laptop like it just found a bug",
        "A wizard holding a receipt and looking betrayed",
        "A robot waiting patiently beside a snack machine",
        "A frog wearing an oversized crown",
        "A dragon trying to fold a fitted sheet",
        "A raccoon guarding one very important sandwich",
        "A space explorer discovering a lost sock",
        "A knight entering a room carrying too many bags",
        "A duck conducting an extremely serious meeting",
        "A sleepy owl opening a group project document",
        "A tiny astronaut pointing at a giant sandwich",
        "A dog wearing sunglasses beside a whiteboard",
        "A squirrel presenting a suspiciously neat checklist",
        "A pirate finding a map to the snack drawer",
        "A bear attempting a very small skateboard trick",
        "A fox holding a trophy labeled almost",
        "A mushroom waiting for its turn to speak",
        "A cloud shaped like it has a brilliant idea",
        "A turtle speed-running a simple chore",
        "A superhero protecting the last cookie",
        "A ghost trying to use a vending machine",
        "A wizard accidentally summoning a balloon",
        "A penguin giving a motivational speech to a plant",
        "A robot discovering that the meeting was cancelled",
    ]
    caption_endings = [
        "Write the funniest safe caption you can.",
        "Give this image a caption that belongs in the group chat.",
        "Caption the exact thought happening here.",
        "Write a short caption with a surprising twist.",
        "Give it a title worthy of a tiny documentary.",
        "Caption it as a completely serious news report.",
        "Write the line that makes the picture make sense.",
        "Give it a clean caption with chaotic energy.",
        "Caption it like a game achievement unlocked.",
        "Write the quote this character would definitely say.",
    ]

    emoji_bases = [
        ("🐱👤", "cat person", ["catperson", "cat person"]),
        ("🌧️☕📖", "rainy day reading", ["rainy day", "reading in the rain"]),
        ("🚀🌕", "moon mission", ["moon mission", "trip to the moon"]),
        ("🧙‍♂️💍🌋", "the lord of the rings", ["lord of the rings", "rings"]),
        ("🦁👑", "the lion king", ["lion king", "the lion king"]),
        ("🕷️👨", "spiderman", ["spider man", "spiderman"]),
        ("🧊👸", "frozen", ["frozen"]),
        ("🧠💡", "bright idea", ["good idea", "bright idea"]),
        ("🐟🔎", "finding nemo", ["finding nemo", "nemo"]),
        ("🦖🏞️", "jurassic park", ["jurassic park", "dinosaur park"]),
        ("👻🏠", "haunted house", ["haunted house", "ghost house"]),
        ("🍕🌙", "midnight pizza", ["midnight pizza", "late night pizza"]),
        ("🎮🏆", "video game champion", ["gaming champion", "game champion"]),
        ("📚🐛", "bookworm", ["book worm", "bookworm"]),
        ("🌊🔱", "aquaman", ["aquaman"]),
        ("🧑‍🚀🌌", "space explorer", ["space explorer", "astronaut"]),
        ("🦸‍♀️🏙️", "superhero city", ["superhero", "city superhero"]),
        ("🍎👩‍🏫", "teacher's apple", ["apple for teacher", "teacher apple"]),
        ("🐝🍯", "honey bee", ["honeybee", "honey bee"]),
        ("🌵🏜️", "desert", ["desert"]),
        ("🎸🔥", "rock star", ["rockstar", "rock star"]),
        ("🧩✅", "piece of the puzzle", ["puzzle piece", "piece of puzzle"]),
        ("🧤❄️", "winter gloves", ["gloves", "winter gloves"]),
        ("🛸👽", "alien spaceship", ["ufo", "alien spaceship"]),
        ("🍿🎬", "movie night", ["movie night", "cinema night"]),
        ("🧭🗺️", "treasure map", ["treasure map"]),
        ("🐉🏰", "dragon castle", ["dragon castle"]),
        ("🎤🌟", "singing star", ["pop star", "singing star"]),
        ("🧪⚡", "science experiment", ["experiment", "science experiment"]),
        ("🚂🕰️", "time train", ["time train"]),
        ("🌈🌧️", "rainbow", ["rainbow"]),
        ("🦉🌙", "night owl", ["night owl"]),
        ("🍪👀", "stolen cookie", ["cookie thief", "stolen cookie"]),
        ("🏹🌲", "forest archer", ["archer", "forest archer"]),
        ("🧱🧱🧱", "brick wall", ["wall", "brick wall"]),
        ("🎲🎲", "double dice", ["double dice", "dice"]),
        ("🧹✨", "magic cleaning", ["magic broom", "cleaning magic"]),
        ("💻🐛", "computer bug", ["software bug", "computer bug"]),
        ("🧊🧊🧊", "ice cubes", ["ice cubes", "ice"]),
        ("🦜🏴‍☠️", "pirate parrot", ["pirate parrot"]),
        ("🌋🔥", "volcano", ["volcano"]),
        ("🪐💍", "saturn", ["planet saturn", "saturn"]),
        ("🍔👑", "burger king", ["burger king"]),
        ("🐢⚡", "fast turtle", ["speedy turtle", "fast turtle"]),
        ("🕵️‍♀️🔍", "detective", ["detective"]),
        ("🎃🌙", "halloween night", ["halloween", "halloween night"]),
        ("🌱☀️", "growing plant", ["plant growth", "growing plant"]),
        ("🏹❤️", "love arrow", ["cupid", "love arrow"]),
        ("🧲🪙", "magnet", ["magnet"]),
        ("🧁🎂", "birthday cake", ["cake", "birthday cake"]),
    ]
    emoji_styles = ["🧩", "🔐", "🕵️", "🎯", "✨"]
    emoji_records: list[dict[str, object]] = []
    for emoji, answer, alternatives in emoji_bases:
        for style in emoji_styles:
            emoji_records.append(
                {
                    "id": f"emojidecode-{len(emoji_records) + 1:03d}",
                    "prompt": f"{style}  Decode: {emoji}",
                    "answer": answer,
                    "alternatives": alternatives,
                }
            )

    trivia_facts: list[tuple[str, str, str, list[str]]] = [
        ("General Knowledge", "What is the largest ocean on Earth?", "Pacific Ocean", ["Atlantic Ocean", "Indian Ocean", "Arctic Ocean"]),
        ("General Knowledge", "Who wrote Romeo and Juliet?", "William Shakespeare", ["Charles Dickens", "Jane Austen", "Mark Twain"]),
        ("General Knowledge", "What is the currency of Japan?", "Yen", ["Won", "Dollar", "Rupee"]),
        ("General Knowledge", "What is the chemical symbol for gold?", "Au", ["Ag", "Gd", "Go"]),
        ("General Knowledge", "What language is primarily spoken in Brazil?", "Portuguese", ["Spanish", "French", "Italian"]),
        ("General Knowledge", "How many pieces does a chess set start with?", "32", ["16", "24", "64"]),
        ("General Knowledge", "How many colors are traditionally named in a rainbow?", "Seven", ["Five", "Six", "Eight"]),
        ("General Knowledge", "Which continent contains Egypt?", "Africa", ["Asia", "Europe", "South America"]),
        ("General Knowledge", "What is the hardest natural mineral?", "Diamond", ["Quartz", "Iron", "Granite"]),
        ("General Knowledge", "What instrument usually has 88 keys?", "Piano", ["Violin", "Trumpet", "Flute"]),
        ("Science", "What is H2O commonly called?", "Water", ["Oxygen", "Hydrogen", "Salt"]),
        ("Science", "What force pulls objects toward Earth?", "Gravity", ["Friction", "Magnetism", "Pressure"]),
        ("Science", "What gas do plants absorb during photosynthesis?", "Carbon dioxide", ["Oxygen", "Nitrogen", "Helium"]),
        ("Science", "What is the center of an atom called?", "Nucleus", ["Electron", "Cell", "Orbit"]),
        ("Science", "Which organ pumps blood around the body?", "Heart", ["Liver", "Lung", "Kidney"]),
        ("Science", "What is the boiling point of water at sea level in Celsius?", "100", ["50", "90", "212"]),
        ("Science", "What kind of animal is a frog?", "Amphibian", ["Reptile", "Mammal", "Insect"]),
        ("Science", "What do bees collect from flowers?", "Nectar", ["Bark", "Sand", "Dew"]),
        ("Science", "What is the process of a caterpillar becoming a butterfly?", "Metamorphosis", ["Evaporation", "Erosion", "Fermentation"]),
        ("Science", "Which simple machine is a ramp?", "Inclined plane", ["Pulley", "Lever", "Wheel"]),
        ("History", "Who was the first person to walk on the Moon?", "Neil Armstrong", ["Buzz Aldrin", "Yuri Gagarin", "John Glenn"]),
        ("History", "Which ancient civilization built the pyramids at Giza?", "Ancient Egyptians", ["Romans", "Vikings", "Maya"]),
        ("History", "The Renaissance began in which country?", "Italy", ["Greece", "France", "Spain"]),
        ("History", "What document begins with We the People?", "The United States Constitution", ["The Magna Carta", "The Odyssey", "The Code of Hammurabi"]),
        ("History", "Which city was buried by Mount Vesuvius?", "Pompeii", ["Athens", "Carthage", "Sparta"]),
        ("History", "Who was known as the Maid of Orléans?", "Joan of Arc", ["Cleopatra", "Boudica", "Marie Curie"]),
        ("History", "Which empire used roads centered on Rome?", "Roman Empire", ["Ottoman Empire", "Mali Empire", "Mongol Empire"]),
        ("History", "What ship carried the Pilgrims to North America in 1620?", "Mayflower", ["Endeavour", "Beagle", "Santa Maria"]),
        ("History", "Which wall divided a European city during the Cold War?", "Berlin Wall", ["Hadrian's Wall", "Great Wall", "Wailing Wall"]),
        ("History", "Who developed the movable-type printing press in Europe?", "Johannes Gutenberg", ["Galileo Galilei", "Leonardo da Vinci", "Isaac Newton"]),
        ("Geography", "What is the capital of France?", "Paris", ["Rome", "Madrid", "Lisbon"]),
        ("Geography", "Which country is shaped like a boot?", "Italy", ["Greece", "Chile", "India"]),
        ("Geography", "What is the longest river in South America?", "Amazon River", ["Nile River", "Danube", "Mekong"]),
        ("Geography", "Which desert covers much of North Africa?", "Sahara", ["Gobi", "Kalahari", "Atacama"]),
        ("Geography", "What is the capital of Canada?", "Ottawa", ["Toronto", "Vancouver", "Montreal"]),
        ("Geography", "Which mountain range includes Mount Everest?", "Himalayas", ["Andes", "Alps", "Rockies"]),
        ("Geography", "Which country has the city of Kyoto?", "Japan", ["China", "Thailand", "Vietnam"]),
        ("Geography", "What is the smallest continent by land area?", "Australia", ["Europe", "Antarctica", "South America"]),
        ("Geography", "Which ocean lies between Africa and Australia?", "Indian Ocean", ["Atlantic Ocean", "Pacific Ocean", "Arctic Ocean"]),
        ("Geography", "What is the capital of Kenya?", "Nairobi", ["Lagos", "Accra", "Kampala"]),
        ("Gaming", "What color is the ghost Blinky in Pac-Man?", "Red", ["Blue", "Green", "Yellow"]),
        ("Gaming", "Which game features the island of Hyrule?", "The Legend of Zelda", ["Final Fantasy", "Halo", "Portal"]),
        ("Gaming", "What is Mario's brother's name?", "Luigi", ["Wario", "Toad", "Yoshi"]),
        ("Gaming", "Which game is known for building with blocks?", "Minecraft", ["Tetris", "Overwatch", "Rocket League"]),
        ("Gaming", "What type of creature is Kirby?", "A round pink hero", ["A blue hedgehog", "A mushroom", "A turtle"]),
        ("Gaming", "Which series includes the character Master Chief?", "Halo", ["Destiny", "Doom", "Metroid"]),
        ("Gaming", "What does a Poké Ball help a trainer catch?", "Pokémon", ["Chocobos", "Digimon only", "Slimes"]),
        ("Gaming", "Which game has a battle bus?", "Fortnite", ["Apex Legends", "Valorant", "Stardew Valley"]),
        ("Gaming", "What is the name of the plumber hero in the Mushroom Kingdom?", "Mario", ["Link", "Sonic", "Kirby"]),
        ("Gaming", "Which puzzle game uses falling tetrominoes?", "Tetris", ["Portal", "Celeste", "Splatoon"]),
        ("Technology", "What does CPU stand for?", "Central Processing Unit", ["Computer Power Utility", "Core Program User", "Central Pixel Unit"]),
        ("Technology", "What does URL stand for?", "Uniform Resource Locator", ["Universal Reading Link", "User Route List", "United Resource Line"]),
        ("Technology", "Which language is commonly used to style web pages?", "CSS", ["SQL", "Python", "Bash"]),
        ("Technology", "What does Wi-Fi provide?", "Wireless network access", ["Printed documents", "Battery power", "Camera focus"]),
        ("Technology", "Which device routes data between networks?", "Router", ["Monitor", "Keyboard", "Printer"]),
        ("Technology", "What does USB commonly connect?", "Devices and peripherals", ["Only satellites", "Only televisions", "Only batteries"]),
        ("Technology", "What is a strong password best described as?", "Long and unique", ["Short and reused", "A first name", "Only numbers"]),
        ("Technology", "What does AI commonly stand for?", "Artificial intelligence", ["Automatic internet", "Applied indexing", "Analog input"]),
        ("Technology", "Which format is commonly used for structured data?", "JSON", ["MP3", "PNG", "EXE"]),
        ("Technology", "What does a web browser display?", "Web pages", ["Only spreadsheets", "Only phone calls", "Only game controllers"]),
        ("Sports", "How many players are on the court for one basketball team?", "Five", ["Four", "Six", "Seven"]),
        ("Sports", "In soccer, what body part may a goalkeeper use in the penalty area?", "Hands", ["Only knees", "Only head", "No body part"]),
        ("Sports", "What sport uses a shuttlecock?", "Badminton", ["Baseball", "Rugby", "Swimming"]),
        ("Sports", "How many rings are on the Olympic symbol?", "Five", ["Four", "Six", "Seven"]),
        ("Sports", "What sport is played at Wimbledon?", "Tennis", ["Cricket", "Golf", "Hockey"]),
        ("Sports", "In baseball, how many strikes usually make an out?", "Three", ["Two", "Four", "Five"]),
        ("Sports", "What color jersey traditionally identifies the leader of the Tour de France?", "Yellow", ["Green", "Blue", "White"]),
        ("Sports", "What sport includes a scrum?", "Rugby", ["Tennis", "Archery", "Volleyball"]),
        ("Sports", "How many points is a touchdown worth before any extra attempt?", "Six", ["Three", "Five", "Seven"]),
        ("Sports", "What piece is hit in table tennis?", "Ball", ["Puck", "Shuttlecock", "Disc"]),
        ("Movies and TV", "Which film features the character Simba?", "The Lion King", ["Toy Story", "Shrek", "Cars"]),
        ("Movies and TV", "What is the name of the wizarding school in Harry Potter?", "Hogwarts", ["Rivendell", "Narnia", "Starfleet"]),
        ("Movies and TV", "Which animated film features a snowman named Olaf?", "Frozen", ["Moana", "Up", "Coco"]),
        ("Movies and TV", "What is the fictional city protected by Batman?", "Gotham City", ["Metropolis", "Emerald City", "Hill Valley"]),
        ("Movies and TV", "Which series follows a group called the Avengers?", "Marvel", ["Pixar", "Studio Ghibli", "The Muppets"]),
        ("Movies and TV", "What color is Shrek?", "Green", ["Purple", "Orange", "Silver"]),
        ("Movies and TV", "Which movie has the quote To infinity and beyond?", "Toy Story", ["The Incredibles", "Finding Nemo", "Wall-E"]),
        ("Movies and TV", "What kind of animal is Paddington?", "Bear", ["Rabbit", "Fox", "Penguin"]),
        ("Movies and TV", "Which series features a time machine called a TARDIS?", "Doctor Who", ["Star Trek", "Lost", "The Expanse"]),
        ("Movies and TV", "What is the name of the cowboy in Toy Story?", "Woody", ["Buzz", "Andy", "Rex"]),
        ("Animals", "What is the largest land animal?", "African elephant", ["Giraffe", "Hippopotamus", "Rhinoceros"]),
        ("Animals", "Which mammal can fly using wings?", "Bat", ["Squirrel", "Otter", "Rabbit"]),
        ("Animals", "What do pandas mostly eat?", "Bamboo", ["Grass seeds", "Fish", "Berries only"]),
        ("Animals", "What is a baby dog called?", "Puppy", ["Calf", "Kitten", "Foal"]),
        ("Animals", "Which animal is known for changing its colors?", "Chameleon", ["Zebra", "Elephant", "Penguin"]),
        ("Animals", "How many legs does a spider have?", "Eight", ["Six", "Ten", "Twelve"]),
        ("Animals", "Which bird is famous for mimicking speech?", "Parrot", ["Eagle", "Penguin", "Ostrich"]),
        ("Animals", "What is a group of lions called?", "Pride", ["Pack", "Herd", "School"]),
        ("Animals", "Which animal carries its baby in a pouch?", "Kangaroo", ["Dolphin", "Tiger", "Moose"]),
        ("Animals", "What kind of animal is a blue whale?", "Mammal", ["Fish", "Reptile", "Amphibian"]),
        ("Space", "What is the closest star to Earth?", "The Sun", ["Sirius", "Polaris", "Betelgeuse"]),
        ("Space", "Which planet is known as the Red Planet?", "Mars", ["Venus", "Jupiter", "Mercury"]),
        ("Space", "What is Earth's natural satellite?", "The Moon", ["The Sun", "Phobos", "Europa"]),
        ("Space", "Which planet has a prominent ring system?", "Saturn", ["Mars", "Earth", "Mercury"]),
        ("Space", "What galaxy contains our Solar System?", "Milky Way", ["Andromeda", "Whirlpool", "Sombrero"]),
        ("Space", "What is a rock from space that reaches the ground called?", "Meteorite", ["Asteroid", "Comet tail", "Nebula"]),
        ("Space", "Which planet is the largest in our Solar System?", "Jupiter", ["Saturn", "Neptune", "Earth"]),
        ("Space", "What tool do astronomers use to observe distant objects?", "Telescope", ["Microscope", "Periscope", "Stethoscope"]),
        ("Space", "What is the name of the path an object takes around another object?", "Orbit", ["Axis", "Horizon", "Equator"]),
        ("Space", "Which planet is famous for being tilted on its side?", "Uranus", ["Venus", "Mars", "Mercury"]),
    ]
    trivia_prefixes = [
        "Quick quiz: ",
        "Challenge round: ",
        "Community quiz: ",
        "Fast facts: ",
        "Final-boss quiz: ",
    ]
    trivia_records: list[dict[str, object]] = []
    for category, question, answer, wrongs in trivia_facts:
        for prefix in trivia_prefixes:
            trivia_records.append(
                {
                    "id": f"trivia-{len(trivia_records) + 1:03d}",
                    "category": category,
                    "prompt": prefix + question,
                    "answer": answer,
                    "options": [answer, *wrongs],
                }
            )

    return {
        "mostlikelyto": _combination_records(
            "mostlikelyto",
            most_likely_stems,
            most_likely_endings,
            "Who is most likely to {stem} {ending}?",
        ),
        "twotruthsonelie": [],
        "hotseat": _combination_records(
            "hotseat",
            hotseat_stems,
            hotseat_endings,
            "Hot Seat: What is your take on {stem} {ending}?",
        ),
        "emojidecode": emoji_records,
        "guesstheplayer": [],
        "trivia": trivia_records,
        "memebattle": _combination_records(
            "memebattle",
            meme_stems,
            meme_endings,
            "{stem} {ending}",
        ),
        "captionthis": _combination_records(
            "captionthis",
            caption_stems,
            caption_endings,
            "{stem}. {ending}",
        ),
    }


def _save_json(path: Path, data: dict[str, object]) -> None:
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def load_content_store() -> dict[str, object]:
    """Load custom content and backfill the built-in catalog without losing removals."""
    seeds = _build_seed_content()
    if CONTENT_STORE_PATH.exists():
        try:
            raw_data = json.loads(CONTENT_STORE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw_data = {}
    else:
        raw_data = {}
    data: dict[str, object] = raw_data if isinstance(raw_data, dict) else {}
    removed_ids = data.get("_removed_ids", [])
    if not isinstance(removed_ids, list):
        removed_ids = []
    removed_set = {str(item) for item in removed_ids}
    data["_removed_ids"] = list(removed_set)
    changed = False

    for game_key in CONTENT_GAME_KEYS:
        records = data.get(game_key)
        if not isinstance(records, list):
            records = []
            data[game_key] = records
            changed = True
        existing_ids = {
            str(record.get("id"))
            for record in records
            if isinstance(record, dict)
        }
        for seed in seeds.get(game_key, []):
            seed_id = str(seed["id"])
            if seed_id not in existing_ids and seed_id not in removed_set:
                records.append(seed)
                changed = True

    if changed or not CONTENT_STORE_PATH.exists():
        try:
            _save_json(CONTENT_STORE_PATH, data)
        except OSError:
            print("Game content catalog could not be saved; using in-memory content.")
    return data


def content_records(store: dict[str, object], game_key: str) -> list[dict[str, object]]:
    records = store.get(game_key, [])
    return records if isinstance(records, list) else []


def choose_content(
    store: dict[str, object],
    game_key: str,
    used_ids: set[str],
) -> dict[str, object] | None:
    records = content_records(store, game_key)
    if not records:
        return None
    available = [
        record for record in records if str(record.get("id")) not in used_ids
    ]
    if not available:
        used_ids.clear()
        available = records
    chosen = random.choice(available)
    used_ids.add(str(chosen.get("id")))
    return chosen


def new_content_id(store: dict[str, object], game_key: str) -> str:
    used = {
        str(record.get("id"))
        for record in content_records(store, game_key)
        if isinstance(record, dict)
    }
    removed = store.get("_removed_ids", [])
    if isinstance(removed, list):
        used.update(str(item) for item in removed)
    index = 1
    while f"{game_key}-custom-{index:03d}" in used:
        index += 1
    return f"{game_key}-custom-{index:03d}"


def content_counts(store: dict[str, object]) -> dict[str, int]:
    return {
        key: len(content_records(store, key))
        for key in CONTENT_GAME_KEYS
    }


def _game_embed(title: str, description: str, owner_name: str) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple(),
    )
    embed.set_footer(text=f"Session started by {owner_name}")
    return embed


async def _ephemeral(interaction: discord.Interaction, content: str) -> None:
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=True)
        else:
            await interaction.response.send_message(content, ephemeral=True)
    except discord.HTTPException:
        pass


async def _post_game(
    interaction: discord.Interaction,
    view: "NewGameView",
    embed: discord.Embed,
) -> None:
    try:
        await interaction.response.send_message(embed=embed, view=view)
        view.attach(await interaction.original_response())
    except discord.HTTPException:
        await _ephemeral(interaction, "Discord could not start this game. Please try again.")


async def _eligible_members(guild: discord.Guild) -> list[discord.Member]:
    try:
        fetched = [member async for member in guild.fetch_members(limit=None)]
    except (discord.Forbidden, discord.HTTPException):
        fetched = list(guild.members)
    members = [member for member in fetched if not member.bot]
    return members


def _clean_user_text(value: str, limit: int = 1000) -> str:
    return discord.utils.escape_mentions(value.strip())[:limit]


def _normalise(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


class NewGameView(discord.ui.View):
    """Base session view with owner controls and channel/message isolation."""

    game_title = "Game"

    def __init__(
        self,
        owner_id: int,
        owner_name: str,
        content_store: dict[str, object],
        active_sessions: dict[int, discord.ui.View],
        channel_id: int,
    ) -> None:
        super().__init__(timeout=900)
        self.owner_id = owner_id
        self.owner_name = owner_name
        self.content_store = content_store
        self.active_sessions = active_sessions
        self.channel_id = channel_id
        self.message: discord.Message | None = None
        self.used_ids: set[str] = set()

    def attach(self, message: discord.Message) -> None:
        self.message = message
        self.active_sessions[message.id] = self

    async def owner_only(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await _ephemeral(
                interaction,
                "Only the person who started this game can use that control.",
            )
            return False
        if interaction.channel_id != self.channel_id:
            await _ephemeral(interaction, "This game belongs to another channel.")
            return False
        return True

    async def participant_only(self, interaction: discord.Interaction) -> bool:
        if interaction.channel_id != self.channel_id:
            await _ephemeral(interaction, "This game belongs to another channel.")
            return False
        return True

    async def edit_game(
        self,
        interaction: discord.Interaction,
        embed: discord.Embed,
    ) -> None:
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.InteractionResponded:
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except discord.HTTPException:
                    pass
        except discord.HTTPException:
            await _ephemeral(interaction, "Discord could not update this game message.")

    def disable_buttons(self) -> None:
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True

    async def finish(self, interaction: discord.Interaction, answer: str | None = None) -> None:
        if not await self.owner_only(interaction):
            return
        self.stop()
        if self.message:
            self.active_sessions.pop(self.message.id, None)
        description = "Game ended."
        if answer:
            description += f"\n\n**Answer:** {answer}"
        embed = _game_embed(self.game_title, description, self.owner_name)
        embed.set_footer(text=f"Session started by {self.owner_name} • Ended")
        self.disable_buttons()
        await self.edit_game(interaction, embed)

    async def on_timeout(self) -> None:
        self.disable_buttons()
        if self.message:
            self.active_sessions.pop(self.message.id, None)
            try:
                embed = self.message.embeds[0].copy() if self.message.embeds else _game_embed(
                    self.game_title,
                    "This game expired.",
                    self.owner_name,
                )
                embed.set_footer(text=f"Session started by {self.owner_name} • Expired")
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass
        self.stop()

    async def next_round(self, interaction: discord.Interaction) -> None:
        await _ephemeral(interaction, "This game does not have another round.")

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.primary, row=4)
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.next_round(interaction)

    @discord.ui.button(label="🛑 End Game", style=discord.ButtonStyle.secondary, row=4)
    async def end_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.finish(interaction)


class MostLikelyToView(NewGameView):
    game_title = "Most Likely To"

    def __init__(self, *args: object, question: dict[str, object], **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.question = question
        self.selected_member: discord.Member | None = None
        self.member_picker = discord.ui.UserSelect(
            placeholder="Choose a server player",
            min_values=1,
            max_values=1,
            row=1,
            disabled=True,
        )
        self.member_picker.callback = self.select_member
        self.add_item(self.member_picker)

    def render(self) -> discord.Embed:
        selected = (
            self.selected_member.mention
            if self.selected_member
            else "No player selected yet."
        )
        return _game_embed(
            self.game_title,
            f"{self.question.get('prompt', 'Who is most likely to...?')}\n\n"
            f"**Selected player:** {selected}",
            self.owner_name,
        )

    async def select_member(self, interaction: discord.Interaction) -> None:
        if not await self.owner_only(interaction):
            return
        if not self.member_picker.values:
            await _ephemeral(interaction, "Choose a server member first.")
            return
        selected = self.member_picker.values[0]
        if not isinstance(selected, discord.Member) or selected.bot:
            await _ephemeral(interaction, "Choose a non-bot server member.")
            return
        self.selected_member = selected
        self.member_picker.disabled = True
        await self.edit_game(interaction, self.render())

    @discord.ui.button(
        label="👤 Choose Player",
        style=discord.ButtonStyle.success,
        row=0,
    )
    async def choose_player(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.owner_only(interaction):
            return
        members = await _eligible_members(interaction.guild) if interaction.guild else []
        if not members:
            await _ephemeral(interaction, "No eligible server members are available.")
            return
        self.member_picker.disabled = False
        await self.edit_game(interaction, self.render())

    async def next_round(self, interaction: discord.Interaction) -> None:
        if not await self.owner_only(interaction):
            return
        question = choose_content(self.content_store, "mostlikelyto", self.used_ids)
        if question is None:
            await _ephemeral(interaction, "There are no Most Likely To prompts available.")
            return
        self.question = question
        self.selected_member = None
        self.member_picker.disabled = True
        await self.edit_game(interaction, self.render())


class TwoTruthsModal(discord.ui.Modal):
    def __init__(
        self,
        content_store: dict[str, object],
        active_sessions: dict[int, discord.ui.View],
        owner_id: int,
        owner_name: str,
        channel_id: int,
        existing_view: "TwoTruthsView | None" = None,
    ) -> None:
        super().__init__(title="Two Truths and One Lie")
        self.content_store = content_store
        self.active_sessions = active_sessions
        self.owner_id = owner_id
        self.owner_name = owner_name
        self.channel_id = channel_id
        self.existing_view = existing_view
        self.statement_one = discord.ui.TextInput(
            label="Statement 1",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True,
        )
        self.statement_two = discord.ui.TextInput(
            label="Statement 2",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True,
        )
        self.statement_three = discord.ui.TextInput(
            label="Statement 3",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True,
        )
        self.lie_number = discord.ui.TextInput(
            label="Which number is the lie? (1, 2, or 3)",
            max_length=1,
            required=True,
        )
        for field in (
            self.statement_one,
            self.statement_two,
            self.statement_three,
            self.lie_number,
        ):
            self.add_item(field)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        statements = [
            _clean_user_text(str(self.statement_one.value), 500),
            _clean_user_text(str(self.statement_two.value), 500),
            _clean_user_text(str(self.statement_three.value), 500),
        ]
        lie_value = str(self.lie_number.value).strip()
        if any(not statement for statement in statements):
            await _ephemeral(interaction, "All three statements are required.")
            return
        if len(set(statement.casefold() for statement in statements)) != 3:
            await _ephemeral(interaction, "The three statements must be different.")
            return
        if lie_value not in {"1", "2", "3"}:
            await _ephemeral(interaction, "The lie number must be 1, 2, or 3.")
            return

        if self.existing_view is not None:
            view = self.existing_view
            view.load_round(statements, int(lie_value))
            await interaction.response.defer(ephemeral=True)
            if view.message:
                try:
                    await view.message.edit(embed=view.render(), view=view)
                except discord.HTTPException:
                    pass
            await interaction.followup.send("New round ready.", ephemeral=True)
            return

        view = TwoTruthsView(
            self.owner_id,
            self.owner_name,
            self.content_store,
            self.active_sessions,
            self.channel_id,
            statements=statements,
            lie_number=int(lie_value),
        )
        await _post_game(interaction, view, view.render())


class TwoTruthsView(NewGameView):
    game_title = "Two Truths, One Lie"

    def __init__(
        self,
        owner_id: int,
        owner_name: str,
        content_store: dict[str, object],
        active_sessions: dict[int, discord.ui.View],
        channel_id: int,
        *,
        statements: list[str],
        lie_number: int,
    ) -> None:
        super().__init__(
            owner_id,
            owner_name,
            content_store,
            active_sessions,
            channel_id,
        )
        self.statements = statements
        self.lie_number = lie_number
        self.votes: dict[int, int] = {}
        self.revealed = False
        self.next_button.label = "➡️ Next Round"

    def render(self) -> discord.Embed:
        lines = "\n".join(
            f"**{index}.** {statement}"
            for index, statement in enumerate(self.statements, start=1)
        )
        description = (
            "One statement is a lie. Vote anonymously by number.\n\n"
            f"{lines}\n\n"
            f"**Votes received:** {len(self.votes)}"
        )
        if self.revealed:
            counts = [sum(value == index for value in self.votes.values()) for index in (1, 2, 3)]
            description += (
                f"\n\n**The lie was:** Statement {self.lie_number}\n"
                f"**Results:** 1 · {counts[0]}  |  2 · {counts[1]}  |  3 · {counts[2]}"
            )
        return _game_embed(self.game_title, description, self.owner_name)

    def load_round(self, statements: list[str], lie_number: int) -> None:
        self.statements = statements
        self.lie_number = lie_number
        self.votes.clear()
        self.revealed = False
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = False

    async def vote(self, interaction: discord.Interaction, number: int) -> None:
        if not await self.participant_only(interaction):
            return
        if self.revealed:
            await _ephemeral(interaction, "The answer has already been revealed.")
            return
        if interaction.user.id in self.votes:
            await _ephemeral(interaction, "You have already voted in this round.")
            return
        self.votes[interaction.user.id] = number
        await self.edit_game(interaction, self.render())

    @discord.ui.button(label="1", style=discord.ButtonStyle.primary, row=0)
    async def vote_one(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.vote(interaction, 1)

    @discord.ui.button(label="2", style=discord.ButtonStyle.primary, row=0)
    async def vote_two(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.vote(interaction, 2)

    @discord.ui.button(label="3", style=discord.ButtonStyle.primary, row=0)
    async def vote_three(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.vote(interaction, 3)

    @discord.ui.button(label="Reveal Answer", style=discord.ButtonStyle.success, row=1)
    async def reveal_answer(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.owner_only(interaction):
            return
        self.revealed = True
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label in {"1", "2", "3"}:
                child.disabled = True
        await self.edit_game(interaction, self.render())

    async def next_round(self, interaction: discord.Interaction) -> None:
        if not await self.owner_only(interaction):
            return
        await interaction.response.send_modal(
            TwoTruthsModal(
                self.content_store,
                self.active_sessions,
                self.owner_id,
                self.owner_name,
                self.channel_id,
                existing_view=self,
            )
        )


class HotseatQuestionModal(discord.ui.Modal):
    def __init__(self, view: "HotSeatView") -> None:
        super().__init__(title="Ask the Hot Seat")
        self.view_ref = view
        self.question = discord.ui.TextInput(
            label="Your safe question",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True,
        )
        self.add_item(self.question)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await self.view_ref.participant_only(interaction):
            return
        if interaction.user.id == self.view_ref.hotseat_id:
            await _ephemeral(interaction, "The Hot Seat player answers this round.")
            return
        question = _clean_user_text(str(self.question.value), 500)
        if not question:
            await _ephemeral(interaction, "Enter a non-empty question.")
            return
        if len(self.view_ref.submitted_questions) >= 20:
            await _ephemeral(interaction, "The question queue is full for this round.")
            return
        self.view_ref.submitted_questions.append((interaction.user.id, question))
        await interaction.response.send_message(
            "Your question was added to the Hot Seat queue.",
            ephemeral=True,
        )
        if self.view_ref.message:
            try:
                await self.view_ref.message.edit(embed=self.view_ref.render(), view=self.view_ref)
            except discord.HTTPException:
                pass


class HotseatAnswerModal(discord.ui.Modal):
    def __init__(self, view: "HotSeatView") -> None:
        super().__init__(title="Answer the Hot Seat")
        self.view_ref = view
        self.answer = discord.ui.TextInput(
            label="Your answer",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True,
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await self.view_ref.participant_only(interaction):
            return
        if interaction.user.id != self.view_ref.hotseat_id:
            await _ephemeral(interaction, "Only the current Hot Seat player can answer.")
            return
        answer = _clean_user_text(str(self.answer.value), 1000)
        if not answer:
            await _ephemeral(interaction, "Enter a non-empty answer.")
            return
        self.view_ref.current_answer = answer
        await interaction.response.defer(ephemeral=True)
        if self.view_ref.message:
            try:
                await self.view_ref.message.edit(
                    embed=self.view_ref.render(),
                    view=self.view_ref,
                )
            except discord.HTTPException:
                pass
        await interaction.followup.send("Answer posted.", ephemeral=True)


class HotSeatView(NewGameView):
    game_title = "Hot Seat"

    def __init__(
        self,
        *args: object,
        hotseat: discord.Member,
        question: dict[str, object],
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.hotseat_id = hotseat.id
        self.hotseat_name = hotseat.display_name
        self.question = question
        self.current_answer: str | None = None
        self.submitted_questions: list[tuple[int, str]] = []
        self.next_button.label = "➡️ Next Question"

    def render(self) -> discord.Embed:
        answer = self.current_answer or "Waiting for the Hot Seat player to answer."
        queue_note = (
            f"\n**Submitted questions waiting:** {len(self.submitted_questions)}"
            if self.submitted_questions
            else ""
        )
        return _game_embed(
            self.game_title,
            f"**Hot Seat:** {self.hotseat_name}\n\n"
            f"{self.question.get('prompt', 'Ask anything safe and fun.')}\n\n"
            f"**Answer:** {answer}{queue_note}",
            self.owner_name,
        )

    async def next_round(self, interaction: discord.Interaction) -> None:
        if not await self.owner_only(interaction):
            return
        question = choose_content(self.content_store, "hotseat", self.used_ids)
        if question is None:
            await _ephemeral(interaction, "There are no Hot Seat questions available.")
            return
        if self.submitted_questions:
            _, submitted = self.submitted_questions.pop(0)
            question = {"id": f"submitted-{random.randint(1000, 999999)}", "prompt": submitted}
        self.question = question
        self.current_answer = None
        await self.edit_game(interaction, self.render())

    @discord.ui.button(label="❓ Ask Question", style=discord.ButtonStyle.primary, row=0)
    async def ask_question(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.participant_only(interaction):
            return
        await interaction.response.send_modal(HotseatQuestionModal(self))

    @discord.ui.button(label="💬 Answer Current", style=discord.ButtonStyle.success, row=0)
    async def answer_current(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.participant_only(interaction):
            return
        if interaction.user.id != self.hotseat_id:
            await _ephemeral(interaction, "Only the current Hot Seat player can answer.")
            return
        await interaction.response.send_modal(HotseatAnswerModal(self))

    @discord.ui.button(label="🎲 Random Player", style=discord.ButtonStyle.secondary, row=1)
    async def random_player(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.owner_only(interaction):
            return
        if not interaction.guild:
            await _ephemeral(interaction, "This game must run in a server.")
            return
        members = await _eligible_members(interaction.guild)
        if len(members) < 1:
            await _ephemeral(interaction, "No eligible server members are available.")
            return
        candidates = [member for member in members if member.id != self.hotseat_id] or members
        chosen = random.choice(candidates)
        self.hotseat_id = chosen.id
        self.hotseat_name = chosen.display_name
        self.current_answer = None
        await self.edit_game(interaction, self.render())


class EmojiGuessModal(discord.ui.Modal):
    def __init__(self, view: "EmojiDecodeView") -> None:
        super().__init__(title="Guess the Emoji Decode")
        self.view_ref = view
        self.guess = discord.ui.TextInput(
            label="Your guess",
            max_length=200,
            required=True,
        )
        self.add_item(self.guess)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.view_ref.handle_guess(interaction, str(self.guess.value))


class EmojiDecodeView(NewGameView):
    game_title = "Emoji Decode"

    def __init__(self, *args: object, puzzle: dict[str, object], **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.puzzle = puzzle
        self.solved = False
        self.winner: str | None = None

    def render(self) -> discord.Embed:
        description = (
            f"{self.puzzle.get('prompt', '🧩 Decode this puzzle')}\n\n"
            "Submit a guess. The first correct answer wins."
        )
        if self.solved and self.winner:
            description += (
                f"\n\n🏆 **{self.winner}** solved it!\n"
                f"**Answer:** {self.puzzle.get('answer', 'Unknown')}"
            )
        return _game_embed(self.game_title, description, self.owner_name)

    async def handle_guess(self, interaction: discord.Interaction, raw_guess: str) -> None:
        if not await self.participant_only(interaction):
            return
        if self.solved:
            await _ephemeral(interaction, "This puzzle is already solved.")
            return
        guess = _normalise(raw_guess)
        accepted = {
            _normalise(str(self.puzzle.get("answer", ""))),
            *(_normalise(str(value)) for value in self.puzzle.get("alternatives", [])),
        }
        if guess and guess in accepted:
            self.solved = True
            self.winner = interaction.user.display_name
            for child in self.children:
                if isinstance(child, discord.ui.Button) and child.label.startswith("🧩"):
                    child.disabled = True
            await self.edit_game(interaction, self.render())
        else:
            await _ephemeral(interaction, "Not quite. Keep trying.")

    @discord.ui.button(label="🧩 Submit Guess", style=discord.ButtonStyle.success, row=0)
    async def submit_guess(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.participant_only(interaction):
            return
        await interaction.response.send_modal(EmojiGuessModal(self))

    async def next_round(self, interaction: discord.Interaction) -> None:
        if not await self.owner_only(interaction):
            return
        puzzle = choose_content(self.content_store, "emojidecode", self.used_ids)
        if puzzle is None:
            await _ephemeral(interaction, "There are no Emoji Decode puzzles available.")
            return
        self.puzzle = puzzle
        self.solved = False
        self.winner = None
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = False
        await self.edit_game(interaction, self.render())

    async def finish(self, interaction: discord.Interaction, answer: str | None = None) -> None:
        await super().finish(interaction, str(self.puzzle.get("answer", "Unknown")))


class PlayerGuessModal(discord.ui.Modal):
    def __init__(self, view: "GuessThePlayerView") -> None:
        super().__init__(title="Guess the Player")
        self.view_ref = view
        self.guess = discord.ui.TextInput(
            label="Display name or username",
            max_length=100,
            required=True,
        )
        self.add_item(self.guess)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.view_ref.handle_guess(interaction, str(self.guess.value))


class GuessThePlayerView(NewGameView):
    game_title = "Guess The Player"

    def __init__(
        self,
        *args: object,
        target: discord.Member,
        clues: list[str],
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.target_id = target.id
        self.target_name = target.display_name
        self.clues = clues
        self.clue_index = 0
        self.solved = False
        self.winner: str | None = None

    def render(self) -> discord.Embed:
        clue = self.clues[min(self.clue_index, len(self.clues) - 1)]
        description = (
            f"**Clue {self.clue_index + 1}/{len(self.clues)}:** {clue}\n\n"
            "Use **Guess Player**. A wrong guess reveals the next clue."
        )
        if self.solved and self.winner:
            description += f"\n\n🏆 **{self.winner}** guessed **{self.target_name}**!"
        return _game_embed(self.game_title, description, self.owner_name)

    async def handle_guess(self, interaction: discord.Interaction, raw_guess: str) -> None:
        if not await self.participant_only(interaction):
            return
        if self.solved:
            await _ephemeral(interaction, "This round is already solved.")
            return
        guess = _normalise(raw_guess)
        target_names = {_normalise(self.target_name)}
        if interaction.guild:
            target = interaction.guild.get_member(self.target_id)
            if target:
                target_names.update({_normalise(target.name), _normalise(target.display_name)})
        if guess in target_names:
            self.solved = True
            self.winner = interaction.user.display_name
            for child in self.children:
                if isinstance(child, discord.ui.Button) and child.label.startswith("🧠"):
                    child.disabled = True
            await self.edit_game(interaction, self.render())
        else:
            if self.clue_index < len(self.clues) - 1:
                self.clue_index += 1
            await _ephemeral(interaction, "Not that player. A new clue is now available.")
            if self.message:
                try:
                    await self.message.edit(embed=self.render(), view=self)
                except discord.HTTPException:
                    pass

    @discord.ui.button(label="🧠 Guess Player", style=discord.ButtonStyle.success, row=0)
    async def guess_player(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.participant_only(interaction):
            return
        await interaction.response.send_modal(PlayerGuessModal(self))

    @discord.ui.button(label="🔎 Next Clue", style=discord.ButtonStyle.primary, row=0)
    async def next_clue(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.participant_only(interaction):
            return
        if self.clue_index < len(self.clues) - 1:
            self.clue_index += 1
        await self.edit_game(interaction, self.render())

    async def next_round(self, interaction: discord.Interaction) -> None:
        if not await self.owner_only(interaction):
            return
        if not interaction.guild:
            await _ephemeral(interaction, "This game must run in a server.")
            return
        target, clues = await _pick_player_with_clues(interaction.guild, self.target_id)
        if target is None:
            await _ephemeral(interaction, "No eligible server members are available.")
            return
        self.target_id = target.id
        self.target_name = target.display_name
        self.clues = clues
        self.clue_index = 0
        self.solved = False
        self.winner = None
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = False
        await self.edit_game(interaction, self.render())

    async def finish(self, interaction: discord.Interaction, answer: str | None = None) -> None:
        await super().finish(interaction, self.target_name)


async def _pick_player_with_clues(
    guild: discord.Guild,
    previous_id: int | None = None,
) -> tuple[discord.Member | None, list[str]]:
    members = await _eligible_members(guild)
    if previous_id is not None and len(members) > 1:
        members = [member for member in members if member.id != previous_id] or members
    if not members:
        return None, []
    target = random.choice(members)
    role_names = [
        role.name
        for role in target.roles
        if not role.is_default() and role.name
    ]
    role_summary = ", ".join(role_names[:3]) if role_names else "no special roles"
    joined = (
        discord.utils.format_dt(target.joined_at, style="D")
        if target.joined_at
        else "an unknown date"
    )
    account = discord.utils.format_dt(target.created_at, style="D")
    clues = [
        f"They joined this server on {joined}.",
        f"Their Discord account was created on {account}.",
        f"They currently have {len(role_names)} visible non-default role(s).",
        f"Some visible roles include: {role_summary}.",
        f"Their display name has {len(target.display_name)} characters.",
    ]
    return target, clues


class TriviaView(NewGameView):
    game_title = "Trivia"

    def __init__(self, *args: object, question: dict[str, object], **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.question = question
        self.options = list(question.get("options", []))
        random.shuffle(self.options)
        self.answer = str(question.get("answer", ""))
        self.incorrect_users: set[int] = set()
        self.solved = False
        self.winner: str | None = None
        self.scores: dict[int, tuple[str, int]] = {}
        self.answer_buttons: list[discord.ui.Button] = []
        self._add_answer_buttons()

    def _add_answer_buttons(self) -> None:
        for index, option in enumerate(self.options[:4]):
            label = f"{chr(65 + index)} · {str(option)[:70]}"
            button = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.primary,
                row=0 if index < 2 else 1,
            )
            button.callback = self._make_answer_callback(str(option))
            self.answer_buttons.append(button)
            self.add_item(button)

    def render(self) -> discord.Embed:
        option_lines = "\n".join(
            f"**{chr(65 + index)}.** {option}"
            for index, option in enumerate(self.options[:4])
        )
        description = f"{self.question.get('prompt', 'Trivia question')}\n\n{option_lines}"
        if self.solved and self.winner:
            description += (
                f"\n\n🏆 **{self.winner}** got it first!\n"
                f"**Correct answer:** {self.answer}"
            )
        leaderboard = sorted(
            self.scores.values(),
            key=lambda item: item[1],
            reverse=True,
        )[:5]
        if leaderboard:
            description += "\n\n**Leaderboard**\n" + "\n".join(
                f"{index}. {name} — {score}"
                for index, (name, score) in enumerate(leaderboard, start=1)
            )
        return _game_embed(self.game_title, description, self.owner_name)

    def _make_answer_callback(
        self,
        option: str,
    ) -> Callable[[discord.Interaction], Awaitable[None]]:
        async def callback(interaction: discord.Interaction) -> None:
            if not await self.participant_only(interaction):
                return
            if self.solved:
                await _ephemeral(interaction, "This round is already over.")
                return
            if interaction.user.id in self.incorrect_users:
                await _ephemeral(interaction, "You already missed this round.")
                return
            if option != self.answer:
                self.incorrect_users.add(interaction.user.id)
                await _ephemeral(interaction, "Not quite. Other players can still answer.")
                return
            self.solved = True
            self.winner = interaction.user.display_name
            name, score = self.scores.get(interaction.user.id, (interaction.user.display_name, 0))
            self.scores[interaction.user.id] = (name, score + 1)
            for answer_button in self.answer_buttons:
                answer_button.disabled = True
            await self.edit_game(interaction, self.render())

        return callback

    async def next_round(self, interaction: discord.Interaction) -> None:
        if not await self.owner_only(interaction):
            return
        question = choose_content(self.content_store, "trivia", self.used_ids)
        if question is None:
            await _ephemeral(interaction, "There are no Trivia questions available.")
            return
        self.question = question
        self.options = list(question.get("options", []))
        random.shuffle(self.options)
        self.answer = str(question.get("answer", ""))
        self.incorrect_users.clear()
        self.solved = False
        self.winner = None
        for answer_button in self.answer_buttons:
            self.remove_item(answer_button)
        self.answer_buttons.clear()
        self._add_answer_buttons()
        await self.edit_game(interaction, self.render())


class SubmissionModal(discord.ui.Modal):
    def __init__(self, view: "SubmissionGameView") -> None:
        super().__init__(title="Submit Your Response")
        self.view_ref = view
        self.response_text = discord.ui.TextInput(
            label="Your caption or response",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True,
        )
        self.add_item(self.response_text)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await self.view_ref.participant_only(interaction):
            return
        if self.view_ref.phase != "submitting":
            await _ephemeral(interaction, "Submissions are closed for this round.")
            return
        if (
            interaction.user.id not in self.view_ref.submissions
            and len(self.view_ref.submissions) >= 14
        ):
            await _ephemeral(interaction, "The response queue is full for this round.")
            return
        response = _clean_user_text(str(self.response_text.value), 500)
        if not response:
            await _ephemeral(interaction, "Enter a non-empty response.")
            return
        self.view_ref.submissions[interaction.user.id] = (
            interaction.user.display_name,
            response,
        )
        await interaction.response.send_message(
            "Your response was submitted.",
            ephemeral=True,
        )
        if self.view_ref.message:
            try:
                await self.view_ref.message.edit(embed=self.view_ref.render(), view=self.view_ref)
            except discord.HTTPException:
                pass


class SubmissionGameView(NewGameView):
    """Shared submit-close-vote flow for Meme Battle and Caption This."""

    content_key = "memebattle"
    game_title = "Meme Battle"
    submit_label = "✍️ Submit Response"

    def __init__(self, *args: object, prompt: dict[str, object], **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.prompt = prompt
        self.phase = "submitting"
        self.submissions: dict[int, tuple[str, str]] = {}
        self.votes: dict[int, int] = {}
        self.winner_id: int | None = None
        self.vote_buttons: list[discord.ui.Button] = []
        self.finish_voting_button: discord.ui.Button | None = None
        self.submit_response.label = self.submit_label
        self.next_button.label = "➡️ Next Round"

    def render(self) -> discord.Embed:
        prompt = str(self.prompt.get("prompt", "Create the funniest response."))
        if self.phase == "submitting":
            description = (
                f"{prompt}\n\n"
                f"Submit a safe response. **Responses submitted:** {len(self.submissions)}"
            )
        elif self.phase == "voting":
            description = (
                f"{prompt}\n\n"
                f"**Voting is open.** Votes received: {len(self.votes)}"
            )
        else:
            winner = self.submissions.get(self.winner_id or -1)
            winner_text = winner[1] if winner else "No winning response."
            winner_name = winner[0] if winner else "No winner"
            description = (
                f"{prompt}\n\n🏆 **Winner:** {winner_name}\n"
                f"**Score:** {sum(value == self.winner_id for value in self.votes.values())}\n"
                f"**Response:** {winner_text}"
            )
        return _game_embed(self.game_title, description, self.owner_name)

    @discord.ui.button(label="✍️ Submit Response", style=discord.ButtonStyle.primary, row=0)
    async def submit_response(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.participant_only(interaction):
            return
        if self.phase != "submitting":
            await _ephemeral(interaction, "Submissions are closed for this round.")
            return
        await interaction.response.send_modal(SubmissionModal(self))

    @discord.ui.button(label="🔒 Close Submissions", style=discord.ButtonStyle.secondary, row=0)
    async def close_submissions(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.owner_only(interaction):
            return
        if len(self.submissions) < 2:
            await _ephemeral(interaction, "At least two responses are needed before voting.")
            return
        self.phase = "voting"
        button.disabled = True
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label == self.submit_label:
                child.disabled = True
        self._add_vote_buttons()
        await self.edit_game(interaction, self.render())

    def _add_vote_buttons(self) -> None:
        for index, submission_id in enumerate(self.submissions):
            if index >= 14:
                break
            button = discord.ui.Button(
                label=f"Vote {chr(65 + index)}",
                style=discord.ButtonStyle.primary,
                custom_id=f"vote:{submission_id}",
                row=1 + (index // 5),
            )
            button.callback = self._make_vote_callback(submission_id)
            self.vote_buttons.append(button)
            self.add_item(button)
        self.finish_voting_button = discord.ui.Button(
            label="✅ Finish Voting",
            style=discord.ButtonStyle.success,
            row=4,
            disabled=False,
        )
        self.finish_voting_button.callback = self.finish_voting
        self.add_item(self.finish_voting_button)

    def _make_vote_callback(
        self,
        submission_id: int,
    ) -> Callable[[discord.Interaction], Awaitable[None]]:
        async def callback(interaction: discord.Interaction) -> None:
            if not await self.participant_only(interaction):
                return
            if self.phase != "voting":
                await _ephemeral(interaction, "Voting is not open.")
                return
            if interaction.user.id == submission_id:
                await _ephemeral(interaction, "You cannot vote for your own response.")
                return
            if interaction.user.id in self.votes:
                await _ephemeral(interaction, "You have already voted in this round.")
                return
            self.votes[interaction.user.id] = submission_id
            await self.edit_game(interaction, self.render())

        return callback

    async def finish_voting(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not await self.owner_only(interaction):
            return
        if self.phase != "voting":
            await _ephemeral(interaction, "Voting is not open.")
            return
        if not self.votes:
            await _ephemeral(interaction, "At least one vote is needed to finish.")
            return
        scores = {
            submission_id: sum(value == submission_id for value in self.votes.values())
            for submission_id in self.submissions
        }
        highest = max(scores.values())
        winners = [submission_id for submission_id, score in scores.items() if score == highest]
        self.winner_id = random.choice(winners)
        self.phase = "finished"
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child is not self.next_button and child is not self.end_button:
                    child.disabled = True
        await self.edit_game(interaction, self.render())

    async def next_round(self, interaction: discord.Interaction) -> None:
        if not await self.owner_only(interaction):
            return
        prompt = choose_content(self.content_store, self.content_key, self.used_ids)
        if prompt is None:
            await _ephemeral(interaction, "There is no more content available for this game.")
            return
        self.prompt = prompt
        self.phase = "submitting"
        self.submissions.clear()
        self.votes.clear()
        self.winner_id = None
        for button in self.vote_buttons:
            self.remove_item(button)
        self.vote_buttons.clear()
        if self.finish_voting_button:
            self.remove_item(self.finish_voting_button)
            self.finish_voting_button = None
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = False
        await self.edit_game(interaction, self.render())


class MemeBattleView(SubmissionGameView):
    content_key = "memebattle"
    game_title = "Meme Battle"
    submit_label = "✍️ Submit Response"


class CaptionThisView(SubmissionGameView):
    content_key = "captionthis"
    game_title = "Caption This"
    submit_label = "✍️ Submit Caption"


def _game_key(choice: app_commands.Choice[str] | None) -> str:
    return choice.value if choice else ""


def _permission_error_text(error: app_commands.AppCommandError, action: str) -> str | None:
    if isinstance(error, app_commands.errors.MissingPermissions):
        return f"You need the Manage Messages permission to {action}."
    return None


def register_new_game_commands(
    command_tree: app_commands.CommandTree,
    client: discord.Client,
    content_store: dict[str, object],
    active_sessions: dict[int, discord.ui.View],
) -> None:
    """Register all new slash commands on the existing command tree."""

    @command_tree.command(
        name="mostlikelyto",
        description="Start a Most Likely To game.",
    )
    async def mostlikelyto(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This game can only be played in a server.",
                ephemeral=True,
            )
            return
        question = choose_content(content_store, "mostlikelyto", set())
        if question is None:
            await interaction.response.send_message(
                "There are no Most Likely To prompts available.",
                ephemeral=True,
            )
            return
        view = MostLikelyToView(
            interaction.user.id,
            interaction.user.display_name,
            content_store,
            active_sessions,
            interaction.channel_id,
            question=question,
        )
        view.used_ids.add(str(question.get("id")))
        await _post_game(interaction, view, view.render())

    @command_tree.command(
        name="twotruthsonelie",
        description="Start a Two Truths and One Lie game.",
    )
    async def twotruthsonelie(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This game can only be played in a server.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(
            TwoTruthsModal(
                content_store,
                active_sessions,
                interaction.user.id,
                interaction.user.display_name,
                interaction.channel_id,
            )
        )

    @command_tree.command(name="hotseat", description="Start a Hot Seat game.")
    async def hotseat(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This game can only be played in a server.",
                ephemeral=True,
            )
            return
        members = await _eligible_members(interaction.guild)
        question = choose_content(content_store, "hotseat", set())
        if not members or question is None:
            await interaction.response.send_message(
                "I need an eligible server member and a Hot Seat question to start.",
                ephemeral=True,
            )
            return
        view = HotSeatView(
            interaction.user.id,
            interaction.user.display_name,
            content_store,
            active_sessions,
            interaction.channel_id,
            hotseat=random.choice(members),
            question=question,
        )
        view.used_ids.add(str(question.get("id")))
        await _post_game(interaction, view, view.render())

    @command_tree.command(
        name="emojidecode",
        description="Start an Emoji Decode game.",
    )
    async def emojidecode(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This game can only be played in a server.",
                ephemeral=True,
            )
            return
        puzzle = choose_content(content_store, "emojidecode", set())
        if puzzle is None:
            await interaction.response.send_message(
                "There are no Emoji Decode puzzles available.",
                ephemeral=True,
            )
            return
        view = EmojiDecodeView(
            interaction.user.id,
            interaction.user.display_name,
            content_store,
            active_sessions,
            interaction.channel_id,
            puzzle=puzzle,
        )
        view.used_ids.add(str(puzzle.get("id")))
        await _post_game(interaction, view, view.render())

    @command_tree.command(
        name="guesstheplayer",
        description="Start a Guess The Player game.",
    )
    async def guesstheplayer(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This game can only be played in a server.",
                ephemeral=True,
            )
            return
        target, clues = await _pick_player_with_clues(interaction.guild)
        if target is None:
            await interaction.response.send_message(
                "No eligible server members are available for this game.",
                ephemeral=True,
            )
            return
        view = GuessThePlayerView(
            interaction.user.id,
            interaction.user.display_name,
            content_store,
            active_sessions,
            interaction.channel_id,
            target=target,
            clues=clues,
        )
        await _post_game(interaction, view, view.render())

    @command_tree.command(name="trivia", description="Start a multiplayer trivia game.")
    async def trivia(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This game can only be played in a server.",
                ephemeral=True,
            )
            return
        question = choose_content(content_store, "trivia", set())
        if question is None:
            await interaction.response.send_message(
                "There are no Trivia questions available.",
                ephemeral=True,
            )
            return
        view = TriviaView(
            interaction.user.id,
            interaction.user.display_name,
            content_store,
            active_sessions,
            interaction.channel_id,
            question=question,
        )
        view.used_ids.add(str(question.get("id")))
        await _post_game(interaction, view, view.render())

    @command_tree.command(name="memebattle", description="Start a Meme Battle game.")
    async def memebattle(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This game can only be played in a server.",
                ephemeral=True,
            )
            return
        prompt = choose_content(content_store, "memebattle", set())
        if prompt is None:
            await interaction.response.send_message(
                "There are no Meme Battle scenarios available.",
                ephemeral=True,
            )
            return
        view = MemeBattleView(
            interaction.user.id,
            interaction.user.display_name,
            content_store,
            active_sessions,
            interaction.channel_id,
            prompt=prompt,
        )
        view.used_ids.add(str(prompt.get("id")))
        await _post_game(interaction, view, view.render())

    @command_tree.command(name="captionthis", description="Start a Caption This game.")
    async def captionthis(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This game can only be played in a server.",
                ephemeral=True,
            )
            return
        prompt = choose_content(content_store, "captionthis", set())
        if prompt is None:
            await interaction.response.send_message(
                "There are no Caption This prompts available.",
                ephemeral=True,
            )
            return
        view = CaptionThisView(
            interaction.user.id,
            interaction.user.display_name,
            content_store,
            active_sessions,
            interaction.channel_id,
            prompt=prompt,
        )
        view.used_ids.add(str(prompt.get("id")))
        await _post_game(interaction, view, view.render())

    @command_tree.command(
        name="addgamecontent",
        description="Add custom content to a new game.",
    )
    @app_commands.describe(
        game="Game that should use this content",
        prompt="Prompt, scenario, emoji sequence, or trivia question",
        answer="Correct answer for Emoji Decode or Trivia",
        alternatives="Comma-separated emoji alternatives, or trivia wrong answers separated by |",
    )
    @app_commands.choices(game=CATALOG_GAME_CHOICES)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def addgamecontent(
        interaction: discord.Interaction,
        game: app_commands.Choice[str],
        prompt: str,
        answer: str | None = None,
        alternatives: str | None = None,
    ) -> None:
        game_key = _game_key(game)
        prompt_text = _clean_user_text(prompt, 800)
        answer_text = _clean_user_text(answer or "", 300)
        if not prompt_text:
            await interaction.response.send_message(
                "Prompt content cannot be empty.",
                ephemeral=True,
            )
            return
        record: dict[str, object] = {
            "id": new_content_id(content_store, game_key),
            "prompt": prompt_text,
            "custom": True,
        }
        if game_key == "emojidecode":
            if not answer_text:
                await interaction.response.send_message(
                    "Emoji Decode content requires an answer.",
                    ephemeral=True,
                )
                return
            record["answer"] = answer_text
            record["alternatives"] = [
                _clean_user_text(item, 100)
                for item in (alternatives or "").split(",")
                if item.strip()
            ]
        elif game_key == "trivia":
            wrongs = [
                _clean_user_text(item, 200)
                for item in (alternatives or "").split("|")
                if item.strip()
            ]
            if not answer_text or len(wrongs) != 3 or len({answer_text.casefold(), *(item.casefold() for item in wrongs)}) != 4:
                await interaction.response.send_message(
                    "Trivia requires one correct answer and exactly three unique wrong answers separated by `|`.",
                    ephemeral=True,
                )
                return
            record["answer"] = answer_text
            record["options"] = [answer_text, *wrongs]
            record["category"] = "Custom"
        else:
            if answer or alternatives:
                await interaction.response.send_message(
                    "This game only accepts prompt content; leave answer fields empty.",
                    ephemeral=True,
                )
                return
        records = content_records(content_store, game_key)
        records.append(record)
        try:
            _save_json(CONTENT_STORE_PATH, content_store)
        except OSError:
            records.pop()
            await interaction.response.send_message(
                "I couldn't save that content. Please try again.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"Added `{record['id']}` to **{CONTENT_GAME_LABELS[game_key]}**."
        )

    @addgamecontent.error
    async def addgamecontent_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        message = _permission_error_text(error, "add game content")
        if message:
            await _ephemeral(interaction, message)

    @command_tree.command(
        name="removegamecontent",
        description="Remove custom or built-in content by ID.",
    )
    @app_commands.describe(content_id="Unique game content ID")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def removegamecontent(
        interaction: discord.Interaction,
        content_id: str,
    ) -> None:
        wanted_id = content_id.strip()
        found_key: str | None = None
        found_record: dict[str, object] | None = None
        for game_key in CATALOG_GAME_KEYS:
            for record in content_records(content_store, game_key):
                if str(record.get("id")) == wanted_id:
                    found_key = game_key
                    found_record = record
                    break
            if found_record:
                break
        if not found_key or not found_record:
            await interaction.response.send_message(
                "No new-game content with that ID was found.",
                ephemeral=True,
            )
            return
        records = content_records(content_store, found_key)
        records.remove(found_record)
        removed = content_store.setdefault("_removed_ids", [])
        if isinstance(removed, list):
            removed.append(wanted_id)
        try:
            _save_json(CONTENT_STORE_PATH, content_store)
        except OSError:
            records.append(found_record)
            if isinstance(removed, list) and wanted_id in removed:
                removed.remove(wanted_id)
            await interaction.response.send_message(
                "I couldn't save that removal. The content was kept.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"Removed `{wanted_id}` from **{CONTENT_GAME_LABELS[found_key]}**."
        )

    @removegamecontent.error
    async def removegamecontent_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        message = _permission_error_text(error, "remove game content")
        if message:
            await _ephemeral(interaction, message)

    @command_tree.command(
        name="listgamecontent",
        description="Browse new-game content and IDs.",
    )
    @app_commands.describe(game="Game to browse", page="Page number")
    @app_commands.choices(game=CATALOG_GAME_CHOICES)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def listgamecontent(
        interaction: discord.Interaction,
        game: app_commands.Choice[str],
        page: int = 1,
    ) -> None:
        if page < 1:
            await interaction.response.send_message(
                "Page must be 1 or greater.",
                ephemeral=True,
            )
            return
        game_key = _game_key(game)
        records = content_records(content_store, game_key)
        page_size = 20
        start = (page - 1) * page_size
        page_records = records[start : start + page_size]
        if not page_records:
            await interaction.response.send_message(
                "No content is available on that page.",
                ephemeral=True,
            )
            return
        lines: list[str] = []
        for record in page_records:
            prompt_text = str(record.get("prompt", "")).replace("\n", " ")
            if len(prompt_text) > 120:
                prompt_text = prompt_text[:117] + "..."
            lines.append(f"`{record.get('id', 'unknown')}` · {prompt_text}")
        embed = _game_embed(
            f"{CONTENT_GAME_LABELS[game_key]} Content",
            "\n".join(lines),
            interaction.user.display_name,
        )
        embed.set_footer(
            text=f"Page {page} • Showing {start + 1}-{start + len(page_records)} of {len(records)}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @listgamecontent.error
    async def listgamecontent_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        message = _permission_error_text(error, "browse game content")
        if message:
            await _ephemeral(interaction, message)