"""Entry point for dreamscape Bot."""

import asyncio
import json
import os
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from discord import app_commands


WARNING_STORE_PATH = Path("warnings.json")
REMINDER_STORE_PATH = Path("reminders.json")
GAME_QUESTION_STORE_PATH = Path("game_questions.json")
GAME_CATEGORIES = ("truth", "dare", "paranoia", "nhie", "wouldyourather")
GAME_CATEGORY_CHOICES = [
    app_commands.Choice(name="Truth", value="truth"),
    app_commands.Choice(name="Dare", value="dare"),
    app_commands.Choice(name="Paranoia", value="paranoia"),
    app_commands.Choice(name="Never Have I Ever", value="nhie"),
    app_commands.Choice(name="Would You Rather", value="wouldyourather"),
]
GAME_CATEGORY_CHOICES_WITH_ALL = [
    app_commands.Choice(name="All games", value="all"),
    *GAME_CATEGORY_CHOICES,
]
EIGHT_BALL_RESPONSES = (
    "Yes.",
    "No.",
    "Definitely.",
    "Very likely.",
    "Ask again later.",
    "It is unclear.",
    "The outlook is good.",
    "The outlook is not good.",
)


def load_warning_store() -> dict[str, dict[str, list[dict[str, str]]]]:
    """Load persisted warning records, returning an empty store when none exist."""
    if not WARNING_STORE_PATH.exists():
        return {}

    try:
        data = json.loads(WARNING_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("Warning store could not be read; starting with an empty store.")
        return {}

    if not isinstance(data, dict):
        return {}
    return data


def save_warning_store(store: dict[str, dict[str, list[dict[str, str]]]]) -> None:
    """Persist warning records atomically so restarts do not lose saved warnings."""
    temporary_path = WARNING_STORE_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(store, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(WARNING_STORE_PATH)


def load_reminder_store() -> list[dict[str, str | int]]:
    """Load persisted reminders, returning an empty list when none exist."""
    if not REMINDER_STORE_PATH.exists():
        return []

    try:
        data = json.loads(REMINDER_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("Reminder store could not be read; starting with an empty store.")
        return []

    if not isinstance(data, list):
        return []
    return data


def save_reminder_store(store: list[dict[str, str | int]]) -> None:
    """Persist reminders atomically so they survive bot restarts."""
    temporary_path = REMINDER_STORE_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(store, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(REMINDER_STORE_PATH)


def parse_reminder_duration(duration: str) -> int | None:
    """Parse a reminder duration such as 30s, 10m, 2h, or 1d."""
    match = re.fullmatch(r"\s*(\d+)\s*([smhd]?)\s*", duration.lower())
    if match is None:
        return None

    amount = int(match.group(1))
    unit = match.group(2) or "m"
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    seconds = amount * multiplier
    if seconds < 1 or seconds > 365 * 86400:
        return None
    return seconds


def _make_seed_questions(
    category: str,
    prompts: list[str],
    contexts: list[str],
) -> list[dict[str, str]]:
    return [
        {
            "id": f"{category}-{index:03d}",
            "prompt": f"{prompt} {context}",
        }
        for index, (prompt, context) in enumerate(
            ((prompt, context) for prompt in prompts for context in contexts),
            start=1,
        )
    ]


def build_seed_question_store() -> dict[str, list[dict[str, str]]]:
    """Build five 200-item starter pools for the interactive games."""
    truth_prompts = [
        "What harmless secret have you never told this group?",
        "Which first impression of you is completely wrong?",
        "What ridiculous thing have you done to avoid an awkward conversation?",
        "Who here would you trust with an embarrassing story?",
        "What talent do you pretend not to have?",
        "What was the last thing you searched for online?",
        "Which fictional character would be your worst roommate?",
        "What small decision do you still overthink?",
        "What funny misunderstanding have you caused?",
        "What harmless rule have you broken?",
        "Which song would reveal too much about your mood?",
        "What is the pettiest reason you have been annoyed?",
        "What object would you save first in a silly emergency?",
        "What is the strangest compliment you have received?",
        "Which friend would survive longest in a mystery novel?",
        "What habit do you hope nobody notices?",
        "What food combination do you defend passionately?",
        "Which fictional world would you visit for one week?",
        "What is the most chaotic group chat moment you remember?",
        "What promise to yourself do you keep postponing?",
    ]
    dare_prompts = [
        "Give a dramatic weather report about the nearest object",
        "Speak like a movie villain for your next three messages",
        "Send a voice note in your most serious news-anchor voice",
        "Change your status to something mysteriously specific",
        "Describe your day using only three exaggerated sound effects",
        "Compliment the last person who sent a message",
        "Write a tiny poem about a snack",
        "Pretend an ordinary item is a priceless museum artifact",
        "Use an imaginary award speech to thank this group",
        "Type a sentence with your eyes closed and do not correct it",
        "Invent a new holiday and announce its strange tradition",
        "Explain a simple task as if it were an epic quest",
        "Give yourself a ridiculous but respectful stage name",
        "Make up a two-line theme song for this server",
        "Describe your outfit like a fashion critic",
        "Reply using only questions for the next three messages",
        "Create a slogan for the nearest object",
        "Tell a clean joke in the most dramatic way possible",
        "Write a fake headline about what happened today",
        "Narrate your next drink of water like a sports commentator",
    ]
    paranoia_prompts = [
        "Who would accidentally become the leader of a secret club?",
        "Who would be most suspiciously calm during a mystery?",
        "Who would survive longest if the lights went out?",
        "Who would start a rumor without realizing it?",
        "Who would be the first to befriend a strange creature?",
        "Who would turn a simple plan into a chaotic adventure?",
        "Who would keep a surprising secret the longest?",
        "Who would solve a puzzle by ignoring the instructions?",
        "Who would be most likely to disappear at a party?",
        "Who would make the best undercover detective?",
        "Who would accidentally become famous for something odd?",
        "Who would bring the strangest item to a road trip?",
        "Who would make a dramatic entrance for no reason?",
        "Who would be trusted with a mysterious old key?",
        "Who would turn a boring meeting into a story?",
        "Who would choose the suspicious door in a haunted house?",
        "Who would win an argument using only confidence?",
        "Who would have the most unexpected hidden hobby?",
        "Who would send a message to the wrong group chat?",
        "Who would volunteer first for a ridiculous experiment?",
    ]
    nhie_prompts = [
        "pretended to understand a conversation",
        "laughed at a joke a second too late",
        "forgot why you walked into a room",
        "made a playlist for a very specific mood",
        "rehearsed a conversation before having it",
        "waved back at someone who was not waving at you",
        "opened the fridge without knowing what you wanted",
        "given a nickname to an inanimate object",
        "taken a screenshot to remember something and forgotten it",
        "used a search engine to spell a simple word",
        "started a hobby and abandoned it within a week",
        "acted busy to avoid an awkward hello",
        "sent a message and immediately regretted the wording",
        "made a plan mainly because snacks were involved",
        "looked for your phone while holding it",
        "practiced an explanation that nobody asked for",
        "pretended to recognize someone you did not recognize",
        "stayed up late for a completely unimportant reason",
        "made a dramatic exit and had to come back",
        "named a file something you later could not find",
    ]
    would_you_rather_pairs = [
        ("always know when someone is lying", "always know when someone is hiding a surprise"),
        ("live in a library", "live in a cinema"),
        ("have a rewind button", "have a pause button"),
        ("talk to animals", "speak every human language"),
        ("be famous for talent", "be famous for kindness"),
        ("explore the deepest ocean", "explore the farthest desert"),
        ("never wait in a queue", "never sit in traffic"),
        ("have perfect memory", "have perfect timing"),
        ("own a tiny dragon", "own a giant friendly robot"),
        ("always find lost objects", "always find the perfect parking spot"),
        ("be the funniest person in every room", "be the wisest person in every room"),
        ("visit the past once", "visit the future once"),
        ("have breakfast for every meal", "have dessert for every meal"),
        ("be able to fly slowly", "be able to teleport once a day"),
        ("live without music", "live without movies"),
        ("have a personal chef", "have a personal travel guide"),
        ("win every board game", "win every argument"),
        ("always be five minutes early", "always be five minutes late"),
        ("control the weather nearby", "control the lights nearby"),
        ("have unlimited books", "have unlimited concert tickets"),
    ]
    truth_contexts = [
        "Give the first honest answer that comes to mind.",
        "Answer as if the group is filming a documentary.",
        "Explain the answer in one sentence.",
        "Answer without naming any private information.",
        "Give an answer that would surprise the group.",
        "Answer like you are writing a diary entry.",
        "Include the funniest detail you can remember.",
        "Answer before anyone can offer a guess.",
        "Give the answer with complete confidence.",
        "Explain what made the answer memorable.",
    ]
    dare_contexts = [
        "Keep it playful and complete it in the next minute.",
        "Do it with an exaggeratedly serious expression.",
        "Let the group choose the sound effect.",
        "Do it without leaving your current spot.",
        "Finish it before sending your next message.",
        "Give the result a dramatic title.",
        "Do it as though you are on a live stage.",
        "Make it understandable without extra explanation.",
        "Use only harmless objects nearby.",
        "Commit to the bit for at least thirty seconds.",
    ]
    paranoia_contexts = [
        "Pick one person and give a harmless reason.",
        "Answer quickly before the group overthinks it.",
        "Choose based only on the current conversation.",
        "Explain the choice like a detective.",
        "Give the most chaotic reasonable answer.",
        "Pick someone who would find the answer funny.",
        "Answer as if there were a plot twist.",
        "Choose a person without repeating a previous pick.",
        "Give a mysterious one-line explanation.",
        "Make the answer dramatic but friendly.",
    ]
    nhie_contexts = [
        "during a completely normal week.",
        "because you were more tired than you admitted.",
        "while trying to look completely confident.",
        "and then acted like it was intentional.",
        "in front of at least one other person.",
        "after promising yourself you would not.",
        "and only realized how funny it was later.",
        "while a friend was waiting for an answer.",
        "for a reason that still makes sense to you.",
        "and immediately told someone about it.",
    ]
    would_you_rather_contexts = [
        "for the next year.",
        "on your next big adventure.",
        "if everyone in the group had to follow your choice.",
        "during a completely unexpected vacation.",
        "if the choice came with one surprising bonus.",
        "when making a decision under pressure.",
        "if you had to defend the choice to the group.",
        "for a story you would tell for years.",
        "if both options were equally convenient.",
        "and explain your reasoning afterward.",
    ]
    store = {
        "truth": _make_seed_questions("truth", truth_prompts, truth_contexts),
        "dare": _make_seed_questions("dare", dare_prompts, dare_contexts),
        "paranoia": _make_seed_questions("paranoia", paranoia_prompts, paranoia_contexts),
        "nhie": _make_seed_questions("nhie", nhie_prompts, nhie_contexts),
    }
    would_you_rather_questions = []
    for index, (options, context) in enumerate(
        (
            (pair, context)
            for pair in would_you_rather_pairs
            for context in would_you_rather_contexts
        ),
        start=1,
    ):
        would_you_rather_questions.append(
            {
                "id": f"wouldyourather-{index:03d}",
                "prompt": f"Which would you choose {context}",
                "option_a": options[0],
                "option_b": options[1],
            }
        )
    store["wouldyourather"] = would_you_rather_questions
    return store


def load_game_question_store() -> dict[str, object]:
    """Load the persistent catalog and add any missing starter questions."""
    seed_store = build_seed_question_store()
    if GAME_QUESTION_STORE_PATH.exists():
        try:
            data = json.loads(GAME_QUESTION_STORE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            print("Game question store could not be read; rebuilding starter pools.")
            data = {}
    else:
        data = {}
    if not isinstance(data, dict):
        data = {}

    removed_ids = set(data.get("_removed_ids", []))
    data["_removed_ids"] = list(removed_ids)
    changed = False
    for category in GAME_CATEGORIES:
        questions = data.get(category)
        if not isinstance(questions, list):
            questions = []
            data[category] = questions
            changed = True
        existing_ids = {str(item.get("id")) for item in questions if isinstance(item, dict)}
        for seed_question in seed_store[category]:
            if seed_question["id"] not in existing_ids and seed_question["id"] not in removed_ids:
                questions.append(seed_question)
                changed = True

    if changed or not GAME_QUESTION_STORE_PATH.exists():
        try:
            save_game_question_store(data)
        except OSError:
            print("Game question store could not be written; using in-memory questions.")
    return data


def save_game_question_store(store: dict[str, object]) -> None:
    """Persist the game catalog atomically."""
    temporary_path = GAME_QUESTION_STORE_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(store, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(GAME_QUESTION_STORE_PATH)


def get_game_questions(store: dict[str, object], category: str) -> list[dict[str, str]]:
    questions = store.get(category, [])
    return questions if isinstance(questions, list) else []


def choose_game_question(
    store: dict[str, object],
    category: str,
    used_ids: set[str],
) -> dict[str, str] | None:
    questions = get_game_questions(store, category)
    if not questions:
        return None
    available = [question for question in questions if question.get("id") not in used_ids]
    if not available:
        used_ids.clear()
        available = questions
    question = random.choice(available)
    used_ids.add(question["id"])
    return question


def new_question_id(store: dict[str, object], category: str) -> str:
    existing_ids = {question.get("id") for question in get_game_questions(store, category)}
    removed_ids = store.get("_removed_ids", [])
    if isinstance(removed_ids, list):
        existing_ids.update(str(question_id) for question_id in removed_ids)
    index = 1
    while f"{category}-custom-{index:03d}" in existing_ids:
        index += 1
    return f"{category}-custom-{index:03d}"


def game_embed(title: str, description: str, owner_name: str) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple(),
    )
    embed.set_footer(text=f"Session started by {owner_name}")
    return embed


class GameSessionView(discord.ui.View):
    """Base view that keeps one interactive game session isolated."""

    def __init__(
        self,
        owner_id: int,
        owner_name: str,
        question_store: dict[str, object],
        active_sessions: dict[int, discord.ui.View],
        used_ids: dict[str, set[str]] | None = None,
    ) -> None:
        super().__init__(timeout=900)
        self.owner_id = owner_id
        self.owner_name = owner_name
        self.question_store = question_store
        self.active_sessions = active_sessions
        self.used_ids = used_ids or {category: set() for category in GAME_CATEGORIES}
        self.message: discord.Message | None = None
        self.game_title = "Game"

    def attach(self, message: discord.Message) -> None:
        self.message = message
        self.active_sessions[message.id] = self

    async def require_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only the person who started this game can use that button.",
                ephemeral=True,
            )
            return False
        return True

    def pick(self, category: str) -> dict[str, str] | None:
        return choose_game_question(self.question_store, category, self.used_ids[category])

    async def end_game(self, interaction: discord.Interaction) -> None:
        if not await self.require_owner(interaction):
            return
        self.stop()
        if self.message:
            self.active_sessions.pop(self.message.id, None)
        embed = game_embed(self.game_title, "Game ended.", self.owner_name)
        embed.set_footer(text=f"Session started by {self.owner_name} • Ended")
        await interaction.response.edit_message(embed=embed, view=None)

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message:
            self.active_sessions.pop(self.message.id, None)
            if self.message.embeds:
                embed = self.message.embeds[0].copy()
                embed.set_footer(text=f"Session started by {self.owner_name} • Expired")
                try:
                    await self.message.edit(embed=embed, view=self)
                except discord.HTTPException:
                    pass
        self.stop()


class TodStartView(GameSessionView):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.game_title = "Truth or Dare"

    async def _choose(self, interaction: discord.Interaction, category: str) -> None:
        if not await self.require_owner(interaction):
            return
        question = self.pick(category)
        if question is None:
            await interaction.response.send_message(
                f"There are no {category} prompts available right now.",
                ephemeral=True,
            )
            return
        next_view = TodPromptView(
            self.owner_id,
            self.owner_name,
            self.question_store,
            self.active_sessions,
            self.used_ids,
            category,
            question,
        )
        next_view.attach(interaction.message)
        self.stop()
        await interaction.response.edit_message(
            embed=game_embed(
                "Truth or Dare",
                f"**{category.title()}**\n\n{question['prompt']}",
                self.owner_name,
            ),
            view=next_view,
        )

    @discord.ui.button(label="Truth", style=discord.ButtonStyle.primary)
    async def truth_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self._choose(interaction, "truth")

    @discord.ui.button(label="Dare", style=discord.ButtonStyle.danger)
    async def dare_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self._choose(interaction, "dare")


class TodPromptView(GameSessionView):
    def __init__(
        self,
        owner_id: int,
        owner_name: str,
        question_store: dict[str, object],
        active_sessions: dict[int, discord.ui.View],
        used_ids: dict[str, set[str]],
        category: str,
        question: dict[str, str],
    ) -> None:
        super().__init__(
            owner_id,
            owner_name,
            question_store,
            active_sessions,
            used_ids,
        )
        self.game_title = "Truth or Dare"
        self.category = category
        self.question = question

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.require_owner(interaction):
            return
        question = self.pick(self.category)
        if question is None:
            await interaction.response.send_message(
                f"There are no {self.category} prompts available right now.",
                ephemeral=True,
            )
            return
        self.question = question
        await interaction.response.edit_message(
            embed=game_embed(
                "Truth or Dare",
                f"**{self.category.title()}**\n\n{question['prompt']}",
                self.owner_name,
            ),
            view=self,
        )

    @discord.ui.button(label="End Game", style=discord.ButtonStyle.secondary)
    async def end_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.end_game(interaction)


class ParanoiaView(GameSessionView):
    def __init__(
        self,
        owner_id: int,
        owner_name: str,
        question_store: dict[str, object],
        active_sessions: dict[int, discord.ui.View],
        question: dict[str, str],
        used_ids: dict[str, set[str]],
    ) -> None:
        super().__init__(
            owner_id,
            owner_name,
            question_store,
            active_sessions,
            used_ids,
        )
        self.game_title = "Paranoia"
        self.question = question

    @discord.ui.button(label="Next Question", style=discord.ButtonStyle.primary)
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.require_owner(interaction):
            return
        question = self.pick("paranoia")
        if question is None:
            await interaction.response.send_message(
                "There are no Paranoia questions available right now.",
                ephemeral=True,
            )
            return
        self.question = question
        await interaction.response.edit_message(
            embed=game_embed("Paranoia", question["prompt"], self.owner_name),
            view=self,
        )

    @discord.ui.button(label="End Game", style=discord.ButtonStyle.secondary)
    async def end_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.end_game(interaction)


class NhieView(GameSessionView):
    def __init__(
        self,
        owner_id: int,
        owner_name: str,
        question_store: dict[str, object],
        active_sessions: dict[int, discord.ui.View],
        question: dict[str, str],
        used_ids: dict[str, set[str]],
    ) -> None:
        super().__init__(
            owner_id,
            owner_name,
            question_store,
            active_sessions,
            used_ids,
        )
        self.game_title = "Never Have I Ever"
        self.question = question
        self.answers: dict[int, tuple[str, str]] = {}

    def render_embed(self) -> discord.Embed:
        description = f"Never have I ever {self.question['prompt']}"
        if self.answers:
            responses = "\n".join(
                f"• {name}: **{answer}**" for answer, name in self.answers.values()
            )
            description += f"\n\nResponses:\n{responses}"
        return game_embed("Never Have I Ever", description, self.owner_name)

    async def answer(self, interaction: discord.Interaction, answer: str) -> None:
        self.answers[interaction.user.id] = (answer, interaction.user.display_name)
        await interaction.response.edit_message(embed=self.render_embed(), view=self)

    @discord.ui.button(label="I Have", style=discord.ButtonStyle.primary)
    async def have_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.answer(interaction, "I Have")

    @discord.ui.button(label="Never", style=discord.ButtonStyle.secondary)
    async def never_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.answer(interaction, "Never")

    @discord.ui.button(label="Next", style=discord.ButtonStyle.success)
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.require_owner(interaction):
            return
        question = self.pick("nhie")
        if question is None:
            await interaction.response.send_message(
                "There are no Never Have I Ever statements available right now.",
                ephemeral=True,
            )
            return
        self.question = question
        self.answers.clear()
        await interaction.response.edit_message(embed=self.render_embed(), view=self)

    @discord.ui.button(label="End Game", style=discord.ButtonStyle.secondary)
    async def end_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.end_game(interaction)


class WouldYouRatherView(GameSessionView):
    def __init__(
        self,
        owner_id: int,
        owner_name: str,
        question_store: dict[str, object],
        active_sessions: dict[int, discord.ui.View],
        question: dict[str, str],
        used_ids: dict[str, set[str]],
    ) -> None:
        super().__init__(
            owner_id,
            owner_name,
            question_store,
            active_sessions,
            used_ids,
        )
        self.game_title = "Would You Rather"
        self.question = question
        self.votes: dict[int, tuple[str, str]] = {}
        self.children[0].label = f"A: {question.get('option_a', 'Option A')[:75]}"
        self.children[1].label = f"B: {question.get('option_b', 'Option B')[:75]}"

    def render_embed(self) -> discord.Embed:
        option_a = self.question.get("option_a", "Option A")
        option_b = self.question.get("option_b", "Option B")
        description = (
            f"{self.question['prompt']}\n\n"
            f"**A.** {option_a}\n"
            f"**B.** {option_b}"
        )
        if self.votes:
            a_names = [name for choice, name in self.votes.values() if choice == "A"]
            b_names = [name for choice, name in self.votes.values() if choice == "B"]
            description += (
                "\n\n**Choices so far**\n"
                f"A ({len(a_names)}): {', '.join(a_names) or '—'}\n"
                f"B ({len(b_names)}): {', '.join(b_names) or '—'}"
            )
        return game_embed("Would You Rather", description, self.owner_name)

    async def vote(self, interaction: discord.Interaction, choice: str) -> None:
        self.votes[interaction.user.id] = (choice, interaction.user.display_name)
        await interaction.response.edit_message(embed=self.render_embed(), view=self)

    @discord.ui.button(label="Option A", style=discord.ButtonStyle.primary)
    async def option_a_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.vote(interaction, "A")

    @discord.ui.button(label="Option B", style=discord.ButtonStyle.primary)
    async def option_b_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.vote(interaction, "B")

    @discord.ui.button(label="Next", style=discord.ButtonStyle.success)
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self.require_owner(interaction):
            return
        question = self.pick("wouldyourather")
        if question is None:
            await interaction.response.send_message(
                "There are no Would You Rather questions available right now.",
                ephemeral=True,
            )
            return
        self.question = question
        self.votes.clear()
        self.children[0].label = f"A: {question.get('option_a', 'Option A')[:75]}"
        self.children[1].label = f"B: {question.get('option_b', 'Option B')[:75]}"
        await interaction.response.edit_message(embed=self.render_embed(), view=self)

    @discord.ui.button(label="End Game", style=discord.ButtonStyle.secondary)
    async def end_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await self.end_game(interaction)


def main() -> None:
    """Connect the bot to Discord."""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set.")

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    command_tree = app_commands.CommandTree(client)
    warning_store = load_warning_store()
    reminder_store = load_reminder_store()
    question_store = load_game_question_store()
    active_sessions: dict[int, discord.ui.View] = {}
    reminder_task: asyncio.Task[None] | None = None

    async def reminder_worker() -> None:
        while not client.is_closed():
            now = datetime.now(timezone.utc)
            due_reminders: list[dict[str, str | int]] = []
            for reminder in list(reminder_store):
                try:
                    due_at = datetime.fromisoformat(str(reminder["due_at"]))
                    if due_at.tzinfo is None:
                        due_at = due_at.replace(tzinfo=timezone.utc)
                except (KeyError, TypeError, ValueError):
                    due_reminders.append(reminder)
                    continue
                if due_at <= now:
                    due_reminders.append(reminder)

            for reminder in due_reminders:
                try:
                    user_id = int(reminder["user_id"])
                    user = client.get_user(user_id) or await client.fetch_user(user_id)
                    await user.send(f"Reminder: {reminder['message']}")
                except (KeyError, TypeError, ValueError, discord.HTTPException):
                    print("A scheduled reminder could not be delivered.")
                finally:
                    if reminder in reminder_store:
                        reminder_store.remove(reminder)

            if due_reminders:
                try:
                    save_reminder_store(reminder_store)
                except OSError:
                    print("Reminder store could not be updated after delivery.")

            await asyncio.sleep(15)

    @command_tree.command(name="ping", description="Check whether the bot is responding.")
    async def ping(interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Pong! 🏓")

    @command_tree.command(name="tod", description="Start a Truth or Dare game.")
    async def tod(interaction: discord.Interaction) -> None:
        view = TodStartView(
            interaction.user.id,
            interaction.user.display_name,
            question_store,
            active_sessions,
        )
        await interaction.response.send_message(
            embed=game_embed(
                "Truth or Dare",
                "Choose Truth or Dare to begin your session.",
                interaction.user.display_name,
            ),
            view=view,
        )
        view.attach(await interaction.original_response())

    @command_tree.command(name="paranoia", description="Start a Paranoia game.")
    async def paranoia(interaction: discord.Interaction) -> None:
        used_ids = {category: set() for category in GAME_CATEGORIES}
        question = choose_game_question(question_store, "paranoia", used_ids["paranoia"])
        if question is None:
            await interaction.response.send_message(
                "There are no Paranoia questions available right now.",
                ephemeral=True,
            )
            return
        view = ParanoiaView(
            interaction.user.id,
            interaction.user.display_name,
            question_store,
            active_sessions,
            question,
            used_ids,
        )
        await interaction.response.send_message(
            embed=game_embed("Paranoia", question["prompt"], interaction.user.display_name),
            view=view,
        )
        view.attach(await interaction.original_response())

    @command_tree.command(name="nhie", description="Start a Never Have I Ever game.")
    async def nhie(interaction: discord.Interaction) -> None:
        used_ids = {category: set() for category in GAME_CATEGORIES}
        question = choose_game_question(question_store, "nhie", used_ids["nhie"])
        if question is None:
            await interaction.response.send_message(
                "There are no Never Have I Ever statements available right now.",
                ephemeral=True,
            )
            return
        view = NhieView(
            interaction.user.id,
            interaction.user.display_name,
            question_store,
            active_sessions,
            question,
            used_ids,
        )
        await interaction.response.send_message(
            embed=view.render_embed(),
            view=view,
        )
        view.attach(await interaction.original_response())

    @command_tree.command(name="wouldyourather", description="Start a Would You Rather game.")
    async def wouldyourather(interaction: discord.Interaction) -> None:
        used_ids = {category: set() for category in GAME_CATEGORIES}
        question = choose_game_question(
            question_store,
            "wouldyourather",
            used_ids["wouldyourather"],
        )
        if question is None:
            await interaction.response.send_message(
                "There are no Would You Rather questions available right now.",
                ephemeral=True,
            )
            return
        view = WouldYouRatherView(
            interaction.user.id,
            interaction.user.display_name,
            question_store,
            active_sessions,
            question,
            used_ids,
        )
        await interaction.response.send_message(
            embed=view.render_embed(),
            view=view,
        )
        view.attach(await interaction.original_response())

    @command_tree.command(name="gamequestions", description="Show question counts for every game.")
    async def gamequestions(interaction: discord.Interaction) -> None:
        embed = game_embed(
            "Game Question Library",
            "Available prompts in the persistent catalog:",
            interaction.user.display_name,
        )
        labels = {
            "truth": "Truth",
            "dare": "Dare",
            "paranoia": "Paranoia",
            "nhie": "Never Have I Ever",
            "wouldyourather": "Would You Rather",
        }
        for category in GAME_CATEGORIES:
            embed.add_field(
                name=labels[category],
                value=str(len(get_game_questions(question_store, category))),
                inline=True,
            )
        await interaction.response.send_message(embed=embed)

    @command_tree.command(name="addquestion", description="Add a custom game question.")
    @app_commands.describe(
        category="Game category",
        question="Question, statement, or prompt",
        option_a="Would You Rather option A",
        option_b="Would You Rather option B",
    )
    @app_commands.choices(category=GAME_CATEGORY_CHOICES)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def addquestion(
        interaction: discord.Interaction,
        category: app_commands.Choice[str],
        question: str,
        option_a: str | None = None,
        option_b: str | None = None,
    ) -> None:
        category_value = category.value
        question_text = question.strip()
        if not question_text or len(question_text) > 1000:
            await interaction.response.send_message(
                "The question must contain between 1 and 1,000 characters.",
                ephemeral=True,
            )
            return
        if category_value == "wouldyourather":
            if (
                not option_a
                or not option_b
                or not option_a.strip()
                or not option_b.strip()
                or len(option_a) > 300
                or len(option_b) > 300
            ):
                await interaction.response.send_message(
                    "Would You Rather questions require two non-empty options of 300 characters or fewer.",
                    ephemeral=True,
                )
                return
        elif option_a or option_b:
            await interaction.response.send_message(
                "Options are only used for Would You Rather questions.",
                ephemeral=True,
            )
            return

        record = {
            "id": new_question_id(question_store, category_value),
            "prompt": question_text,
        }
        if category_value == "wouldyourather":
            record["option_a"] = option_a.strip()
            record["option_b"] = option_b.strip()
        questions = get_game_questions(question_store, category_value)
        questions.append(record)
        try:
            save_game_question_store(question_store)
        except OSError:
            questions.pop()
            await interaction.response.send_message(
                "I couldn't save that question. Please try again.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"Added question `{record['id']}` to **{category.name}**."
        )

    @addquestion.error
    async def addquestion_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Manage Messages permission to add questions.",
                ephemeral=True,
            )

    @command_tree.command(name="removequestion", description="Remove a custom or starter question.")
    @app_commands.describe(question_id="Unique question ID to remove")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def removequestion(
        interaction: discord.Interaction,
        question_id: str,
    ) -> None:
        question_id = question_id.strip()
        found_category: str | None = None
        found_question: dict[str, str] | None = None
        for category in GAME_CATEGORIES:
            for question in get_game_questions(question_store, category):
                if question.get("id") == question_id:
                    found_category = category
                    found_question = question
                    break
            if found_question is not None:
                break
        if found_category is None or found_question is None:
            await interaction.response.send_message(
                "No question with that ID was found.",
                ephemeral=True,
            )
            return

        questions = get_game_questions(question_store, found_category)
        questions.remove(found_question)
        removed_ids = question_store.setdefault("_removed_ids", [])
        if isinstance(removed_ids, list):
            removed_ids.append(question_id)
        try:
            save_game_question_store(question_store)
        except OSError:
            questions.append(found_question)
            if isinstance(removed_ids, list) and question_id in removed_ids:
                removed_ids.remove(question_id)
            await interaction.response.send_message(
                "I couldn't save that removal. The question was not removed.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"Removed question `{question_id}` from **{found_category}**."
        )

    @removequestion.error
    async def removequestion_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Manage Messages permission to remove questions.",
                ephemeral=True,
            )

    @command_tree.command(name="listquestions", description="Browse game questions and IDs.")
    @app_commands.describe(category="Optional category filter", page="Page number")
    @app_commands.choices(category=GAME_CATEGORY_CHOICES_WITH_ALL)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def listquestions(
        interaction: discord.Interaction,
        category: app_commands.Choice[str] | None = None,
        page: int = 1,
    ) -> None:
        if page < 1:
            await interaction.response.send_message(
                "Page must be 1 or greater.",
                ephemeral=True,
            )
            return
        category_value = category.value if category else "all"
        categories = GAME_CATEGORIES if category_value == "all" else (category_value,)
        entries: list[tuple[str, dict[str, str]]] = []
        for selected_category in categories:
            entries.extend(
                (selected_category, question)
                for question in get_game_questions(question_store, selected_category)
            )
        page_size = 25
        start = (page - 1) * page_size
        page_entries = entries[start : start + page_size]
        if not page_entries:
            await interaction.response.send_message(
                "No questions are available on that page.",
                ephemeral=True,
            )
            return

        lines = []
        for selected_category, question in page_entries:
            prompt = question.get("prompt", "").replace("\n", " ")
            if len(prompt) > 130:
                prompt = prompt[:127] + "..."
            lines.append(f"`{question.get('id', 'unknown')}` · **{selected_category}** · {prompt}")
        embed = game_embed(
            "Game Questions",
            "\n".join(lines),
            interaction.user.display_name,
        )
        embed.set_footer(
            text=f"Page {page} • Showing {start + 1}-{start + len(page_entries)} of {len(entries)}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @listquestions.error
    async def listquestions_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Manage Messages permission to browse questions.",
                ephemeral=True,
            )

    @command_tree.command(name="avatar", description="Display a member's profile picture.")
    @app_commands.describe(member="Member whose profile picture you want to view")
    async def avatar(
        interaction: discord.Interaction,
        member: discord.Member | None = None,
    ) -> None:
        target = member or interaction.user
        display_name = getattr(target, "display_name", target.name)
        embed = discord.Embed(
            title=f"Avatar: {display_name}",
            color=discord.Color.blurple(),
        )
        embed.set_image(url=target.display_avatar.url)
        try:
            await interaction.response.send_message(embed=embed)
        except discord.HTTPException:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "I couldn't display that profile picture. Please try again.",
                    ephemeral=True,
                )

    @command_tree.command(name="role", description="Add or remove a role from a member.")
    @app_commands.describe(
        action="Choose whether to add or remove the role",
        member="Member to update",
        role="Role to add or remove",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Add role", value="add"),
            app_commands.Choice(name="Remove role", value="remove"),
        ]
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def role(
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        member: discord.Member,
        role: discord.Role,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "Roles can only be managed in a server.",
                ephemeral=True,
            )
            return

        bot_member = guild.me or (client.user and guild.get_member(client.user.id))
        if bot_member is None:
            await interaction.response.send_message(
                "I couldn't verify the bot's role hierarchy.",
                ephemeral=True,
            )
            return
        if role.is_default() or role >= bot_member.top_role:
            await interaction.response.send_message(
                "I can't modify that role because it is equal to or higher than my highest role.",
                ephemeral=True,
            )
            return
        if member == guild.owner or member.top_role >= bot_member.top_role:
            await interaction.response.send_message(
                "I can't modify a member whose highest role is equal to or higher than mine.",
                ephemeral=True,
            )
            return

        try:
            if action.value == "add":
                if role in member.roles:
                    await interaction.response.send_message(
                        f"{member.mention} already has {role.mention}.",
                        ephemeral=True,
                    )
                    return
                await member.add_roles(role, reason="Role added by moderator command")
                confirmation = f"Added {role.mention} to {member.mention}."
            elif action.value == "remove":
                if role not in member.roles:
                    await interaction.response.send_message(
                        f"{member.mention} does not have {role.mention}.",
                        ephemeral=True,
                    )
                    return
                await member.remove_roles(role, reason="Role removed by moderator command")
                confirmation = f"Removed {role.mention} from {member.mention}."
            else:
                await interaction.response.send_message(
                    "Choose either Add role or Remove role.",
                    ephemeral=True,
                )
                return
        except discord.Forbidden:
            await interaction.response.send_message(
                "Discord denied the role change. Check my Manage Roles permission and role hierarchy.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord rejected the role change. Please try again.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(confirmation)

    @role.error
    async def role_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Manage Roles permission to use this command.",
                ephemeral=True,
            )

    @command_tree.command(name="nick", description="Change a member's server nickname.")
    @app_commands.describe(
        member="Member whose nickname you want to change",
        nickname="New nickname; leave blank to clear it",
    )
    @app_commands.checks.has_permissions(manage_nicknames=True)
    async def nick(
        interaction: discord.Interaction,
        member: discord.Member,
        nickname: str | None = None,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "Nicknames can only be changed in a server.",
                ephemeral=True,
            )
            return

        new_nickname = nickname.strip() if nickname and nickname.strip() else None
        if new_nickname is not None and len(new_nickname) > 32:
            await interaction.response.send_message(
                "Nicknames must be 32 characters or fewer.",
                ephemeral=True,
            )
            return

        bot_member = guild.me or (client.user and guild.get_member(client.user.id))
        if bot_member is None:
            await interaction.response.send_message(
                "I couldn't verify the bot's role hierarchy.",
                ephemeral=True,
            )
            return
        if member == guild.owner or member.top_role >= bot_member.top_role:
            await interaction.response.send_message(
                "I can't change the nickname of a member whose role is equal to or higher than mine.",
                ephemeral=True,
            )
            return

        try:
            await member.edit(nick=new_nickname, reason="Nickname changed by moderator command")
        except discord.Forbidden:
            await interaction.response.send_message(
                "Discord denied the nickname change. Check my Manage Nicknames permission and role hierarchy.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord rejected the nickname change. Please try again.",
                ephemeral=True,
            )
            return

        confirmation = (
            f"Cleared {member.mention}'s server nickname."
            if new_nickname is None
            else f"Changed {member.mention}'s server nickname to **{new_nickname}**."
        )
        await interaction.response.send_message(confirmation)

    @nick.error
    async def nick_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Manage Nicknames permission to use this command.",
                ephemeral=True,
            )

    @command_tree.command(name="whois", description="Display information about a server member.")
    @app_commands.describe(member="Member whose information you want to view")
    async def whois(
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Member information is only available inside a server.",
                ephemeral=True,
            )
            return

        highest_role = (
            member.top_role.mention if not member.top_role.is_default() else "@everyone"
        )
        embed = discord.Embed(
            title=f"Whois: {member.display_name}",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=member.name, inline=True)
        embed.add_field(name="Display Name", value=member.display_name, inline=True)
        embed.add_field(name="User ID", value=str(member.id), inline=True)
        embed.add_field(
            name="Account Created",
            value=discord.utils.format_dt(member.created_at, style="F"),
            inline=False,
        )
        embed.add_field(
            name="Joined Server",
            value=(
                discord.utils.format_dt(member.joined_at, style="F")
                if member.joined_at
                else "Unknown"
            ),
            inline=False,
        )
        embed.add_field(name="Highest Role", value=highest_role, inline=False)

        try:
            await interaction.response.send_message(embed=embed)
        except discord.HTTPException:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "I couldn't display that member's information. Please try again.",
                    ephemeral=True,
                )

    @command_tree.command(name="remind", description="Set a DM reminder for yourself.")
    @app_commands.describe(
        duration="Duration such as 30s, 10m, 2h, or 1d; numbers are minutes",
        message="Reminder message",
    )
    async def remind(
        interaction: discord.Interaction,
        duration: str,
        message: str,
    ) -> None:
        seconds = parse_reminder_duration(duration)
        if seconds is None:
            await interaction.response.send_message(
                "Use a positive duration such as 30s, 10m, 2h, or 1d. "
                "A number without a unit is treated as minutes, up to 365 days.",
                ephemeral=True,
            )
            return
        if not message.strip() or len(message) > 1000:
            await interaction.response.send_message(
                "The reminder message must contain between 1 and 1,000 characters.",
                ephemeral=True,
            )
            return

        due_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        reminder = {
            "user_id": interaction.user.id,
            "message": message.strip(),
            "due_at": due_at.isoformat(timespec="seconds"),
        }
        reminder_store.append(reminder)
        try:
            save_reminder_store(reminder_store)
        except OSError:
            reminder_store.pop()
            await interaction.response.send_message(
                "I couldn't save that reminder. Please try again.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Reminder set for {discord.utils.format_dt(due_at, style='R')}.",
            ephemeral=True,
        )

    @command_tree.command(name="8ball", description="Ask the magic 8-ball a question.")
    @app_commands.describe(question="Question for the magic 8-ball")
    async def eight_ball(
        interaction: discord.Interaction,
        question: str,
    ) -> None:
        if not question.strip() or len(question) > 500:
            await interaction.response.send_message(
                "The question must contain between 1 and 500 characters.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Magic 8-Ball",
            description=f"**Question:** {question}\n\n**Answer:** {random.choice(EIGHT_BALL_RESPONSES)}",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed)

    @command_tree.command(name="roll", description="Roll a number between 1 and a maximum.")
    @app_commands.describe(maximum="Maximum number, default 100")
    async def roll(
        interaction: discord.Interaction,
        maximum: int | None = None,
    ) -> None:
        max_value = 100 if maximum is None else maximum
        if max_value < 1 or max_value > 1_000_000:
            await interaction.response.send_message(
                "The maximum must be between 1 and 1,000,000.",
                ephemeral=True,
            )
            return

        result = random.randint(1, max_value)
        embed = discord.Embed(
            title="Roll",
            description=f"You rolled **{result}** (1–{max_value}).",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed)

    @command_tree.command(name="coinflip", description="Flip a coin.")
    async def coinflip(interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Coin Flip",
            description=f"**{random.choice(('Heads', 'Tails'))}**",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed)

    @command_tree.command(name="warn", description="Issue a formal verbal warning to a member.")
    @app_commands.describe(member="Member to warn", reason="Reason for the warning")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Warnings can only be issued in a server.",
                ephemeral=True,
            )
            return

        guild_key = str(interaction.guild.id)
        member_key = str(member.id)
        guild_warnings = warning_store.setdefault(guild_key, {})
        member_warnings = guild_warnings.setdefault(member_key, [])
        member_warnings.append(
            {
                "reason": reason,
                "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )
        try:
            save_warning_store(warning_store)
        except OSError:
            member_warnings.pop()
            if not member_warnings:
                guild_warnings.pop(member_key, None)
            await interaction.response.send_message(
                "I couldn't save this warning. No warning was issued.",
                ephemeral=True,
            )
            return

        server_name = interaction.guild.name if interaction.guild else "this server"
        warning_message = (
            f"You have received a formal verbal warning from the moderators of {server_name}.\n\n"
            f"Reason: {reason}\n\n"
            "Please review the server rules and ensure this behavior does not continue."
        )

        dm_delivered = True
        try:
            await member.send(warning_message)
        except (discord.Forbidden, discord.HTTPException):
            dm_delivered = False

        if dm_delivered:
            confirmation = (
                f"Warned {member.mention}. The member was notified by DM.\n"
                f"Reason: {reason}"
            )
        else:
            confirmation = (
                f"Warned {member.mention}, but their DM could not be delivered "
                "(their DMs may be disabled).\n"
                f"Reason: {reason}"
            )

        await interaction.response.send_message(confirmation)

    @command_tree.command(name="warnings", description="View a member's previous warnings.")
    @app_commands.describe(member="Member whose warnings you want to view")
    async def warnings(
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Warnings can only be viewed in a server.",
                ephemeral=True,
            )
            return

        guild_warnings = warning_store.get(str(interaction.guild.id), {})
        member_warnings = guild_warnings.get(str(member.id), [])
        if not member_warnings:
            await interaction.response.send_message(
                f"{member.mention} has no recorded warnings.",
                ephemeral=True,
            )
            return

        warning_lines = [f"Warnings for {member.mention}:"]
        for number, warning in enumerate(member_warnings, start=1):
            warning_lines.append(
                f"{number}. {warning.get('date', 'Unknown date')} — "
                f"{warning.get('reason', 'No reason provided')}"
            )

        response = "\n".join(warning_lines)
        if len(response) > 2000:
            response = response[:1997] + "..."
        await interaction.response.send_message(response, ephemeral=True)

    @command_tree.command(name="unwarn", description="Remove a specific warning from a member.")
    @app_commands.describe(
        member="Member whose warning you want to remove",
        warning_number="Warning number to remove",
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unwarn(
        interaction: discord.Interaction,
        member: discord.Member,
        warning_number: int,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Warnings can only be removed in a server.",
                ephemeral=True,
            )
            return

        guild_warnings = warning_store.get(str(interaction.guild.id), {})
        member_key = str(member.id)
        member_warnings = guild_warnings.get(member_key, [])
        if warning_number < 1 or warning_number > len(member_warnings):
            await interaction.response.send_message(
                f"Warning number must be between 1 and {len(member_warnings)}.",
                ephemeral=True,
            )
            return

        removed_warning = member_warnings.pop(warning_number - 1)
        if not member_warnings:
            guild_warnings.pop(member_key, None)
        try:
            save_warning_store(warning_store)
        except OSError:
            if member_warnings:
                member_warnings.insert(warning_number - 1, removed_warning)
            else:
                guild_warnings[member_key] = [removed_warning]
            await interaction.response.send_message(
                "I couldn't save the warning removal. The warning was not removed.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Removed warning {warning_number} from {member.mention}.\n"
            f"Reason: {removed_warning.get('reason', 'No reason provided')}\n"
            f"Date: {removed_warning.get('date', 'Unknown date')}"
        )

    @unwarn.error
    async def unwarn_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Moderate Members permission to use this command.",
                ephemeral=True,
            )

    @command_tree.command(name="lock", description="Lock the current text channel.")
    @app_commands.describe(reason="Reason for locking the channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(
        interaction: discord.Interaction,
        reason: str,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Channels can only be locked in a server.",
                ephemeral=True,
            )
            return
        if not reason.strip():
            await interaction.response.send_message(
                "A reason is required to lock the channel.",
                ephemeral=True,
            )
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Only text channels can be locked.",
                ephemeral=True,
            )
            return

        try:
            await channel.set_permissions(
                interaction.guild.default_role,
                send_messages=False,
                reason=reason,
            )
            for role in interaction.guild.roles:
                if role.is_default():
                    continue
                if role.permissions.manage_channels or role.permissions.administrator:
                    await channel.set_permissions(
                        role,
                        send_messages=True,
                        reason=reason,
                    )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't lock this channel. Check that I have the Manage Channels "
                "permission.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord rejected the channel lock request. Please try again.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Locked {channel.mention}. Regular members can no longer send messages.\n"
            f"Reason: {reason}"
        )

    @lock.error
    async def lock_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Manage Channels permission to use this command.",
                ephemeral=True,
            )

    @command_tree.command(name="unlock", description="Unlock the current text channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Channels can only be unlocked in a server.",
                ephemeral=True,
            )
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Only text channels can be unlocked.",
                ephemeral=True,
            )
            return

        try:
            await channel.set_permissions(
                interaction.guild.default_role,
                send_messages=None,
                reason="Channel unlocked by command",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't unlock this channel. Check that I have the Manage Channels "
                "permission.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord rejected the channel unlock request. Please try again.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Unlocked {channel.mention}. Regular members can send messages again."
        )

    @unlock.error
    async def unlock_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Manage Channels permission to use this command.",
                ephemeral=True,
            )

    @command_tree.command(name="slowmode", description="Set the current text channel's slowmode.")
    @app_commands.describe(
        delay="Slowmode delay in seconds (0-21600)",
        reason="Optional reason for changing slowmode",
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(
        interaction: discord.Interaction,
        delay: int,
        reason: str | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Slowmode can only be changed in a server.",
                ephemeral=True,
            )
            return
        if delay < 0 or delay > 21600:
            await interaction.response.send_message(
                "Delay must be between 0 and 21,600 seconds.",
                ephemeral=True,
            )
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Slowmode can only be changed in a text channel.",
                ephemeral=True,
            )
            return

        reason_text = reason.strip() if reason and reason.strip() else "No reason provided."
        try:
            await channel.edit(slowmode_delay=delay, reason=reason_text)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't change slowmode. Check that I have the Manage Channels "
                "permission.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord rejected the slowmode request. Please try again.",
                ephemeral=True,
            )
            return

        setting = "disabled" if delay == 0 else f"set to {delay} second(s)"
        await interaction.response.send_message(
            f"Slowmode {setting} in {channel.mention}.\nReason: {reason_text}"
        )

    @slowmode.error
    async def slowmode_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Manage Channels permission to use this command.",
                ephemeral=True,
            )

    @command_tree.command(
        name="serverinfo",
        description="Display information about the current Discord server.",
    )
    async def serverinfo(interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "Server information is only available inside a server.",
                ephemeral=True,
            )
            return

        owner = guild.owner.mention if guild.owner else f"<@{guild.owner_id}>"
        member_count = guild.member_count if guild.member_count is not None else len(guild.members)
        profile_picture = "Available" if guild.icon else "Not set"
        embed = discord.Embed(
            title=guild.name,
            color=discord.Color.blurple(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=owner, inline=True)
        embed.add_field(name="Profile Picture", value=profile_picture, inline=True)
        embed.add_field(name="Members", value=str(member_count), inline=True)
        embed.add_field(name="Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(
            name="Created",
            value=discord.utils.format_dt(guild.created_at, style="F"),
            inline=False,
        )

        try:
            await interaction.response.send_message(embed=embed)
        except discord.HTTPException:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "I couldn't display the server information. Please try again.",
                    ephemeral=True,
                )

    @command_tree.command(name="announce", description="Post an announcement in the current channel.")
    @app_commands.describe(message="Announcement message to post")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def announce(
        interaction: discord.Interaction,
        message: str,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Announcements can only be posted in a server.",
                ephemeral=True,
            )
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "Announcements can only be posted in a text channel.",
                ephemeral=True,
            )
            return
        if not message.strip() or len(message) > 4096:
            await interaction.response.send_message(
                "The announcement must contain between 1 and 4,096 characters.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Announcement",
            description=message,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Posted by {interaction.user.display_name}")
        try:
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "I couldn't post the announcement because Discord denied the request.",
                    ephemeral=True,
                )
        except discord.HTTPException:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Discord rejected the announcement. Please try again.",
                    ephemeral=True,
                )

    @announce.error
    async def announce_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Manage Messages permission to use this command.",
                ephemeral=True,
            )

    @command_tree.command(name="poll", description="Create a reaction poll.")
    @app_commands.describe(
        question="Poll question",
        choice1="First answer choice",
        choice2="Second answer choice",
        choice3="Optional third answer choice",
        choice4="Optional fourth answer choice",
    )
    async def poll(
        interaction: discord.Interaction,
        question: str,
        choice1: str,
        choice2: str,
        choice3: str | None = None,
        choice4: str | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Polls can only be created in a server.",
                ephemeral=True,
            )
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "Polls can only be created in a text channel.",
                ephemeral=True,
            )
            return
        if not question.strip() or len(question) > 256:
            await interaction.response.send_message(
                "The poll question must contain between 1 and 256 characters.",
                ephemeral=True,
            )
            return

        raw_choices = [choice1, choice2, choice3, choice4]
        choices = [choice.strip() for choice in raw_choices if choice is not None]
        if len(choices) < 2 or any(not choice or len(choice) > 200 for choice in choices):
            await interaction.response.send_message(
                "Provide 2–4 non-empty choices, each no longer than 200 characters.",
                ephemeral=True,
            )
            return
        if len({choice.casefold() for choice in choices}) != len(choices):
            await interaction.response.send_message(
                "Poll choices must be unique.",
                ephemeral=True,
            )
            return

        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        choice_lines = [
            f"{emoji} {choice}" for emoji, choice in zip(number_emojis, choices)
        ]
        embed = discord.Embed(
            title=question,
            description="\n".join(choice_lines),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Poll by {interaction.user.display_name}")

        try:
            await interaction.response.send_message(embed=embed)
            poll_message = await interaction.original_response()
            for emoji in number_emojis[: len(choices)]:
                await poll_message.add_reaction(emoji)
        except discord.Forbidden:
            if interaction.response.is_done():
                await interaction.followup.send(
                    "The poll was posted, but I couldn't add all voting reactions.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "I couldn't create the poll because Discord denied the request.",
                    ephemeral=True,
                )
        except discord.HTTPException:
            if interaction.response.is_done():
                await interaction.followup.send(
                    "The poll was posted, but Discord rejected one of the voting reactions.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "Discord rejected the poll. Please try again.",
                    ephemeral=True,
                )

    @command_tree.command(name="userinfo", description="Display information about a server member.")
    @app_commands.describe(member="Member whose information you want to view")
    async def userinfo(
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "User information is only available inside a server.",
                ephemeral=True,
            )
            return

        roles = [role.mention for role in member.roles if not role.is_default()]
        role_text = ", ".join(roles) if roles else "No roles"
        if len(role_text) > 1024:
            role_text = role_text[:1021] + "..."
        joined_at = (
            discord.utils.format_dt(member.joined_at, style="F")
            if member.joined_at
            else "Unknown"
        )
        embed = discord.Embed(
            title=f"User info: {member.display_name}",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=member.name, inline=True)
        embed.add_field(name="Display Name", value=member.display_name, inline=True)
        embed.add_field(
            name="Account Created",
            value=discord.utils.format_dt(member.created_at, style="F"),
            inline=False,
        )
        embed.add_field(name="Joined Server", value=joined_at, inline=False)
        embed.add_field(name="Roles", value=role_text, inline=False)

        try:
            await interaction.response.send_message(embed=embed)
        except discord.HTTPException:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "I couldn't display that member's information. Please try again.",
                    ephemeral=True,
                )

    @command_tree.command(name="timeout", description="Timeout a member for a specified duration.")
    @app_commands.describe(
        member="Member to timeout",
        duration="Timeout duration in minutes",
        reason="Reason for the timeout",
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(
        interaction: discord.Interaction,
        member: discord.Member,
        duration: int,
        reason: str,
    ) -> None:
        max_duration_minutes = 28 * 24 * 60
        if duration < 1 or duration > max_duration_minutes:
            await interaction.response.send_message(
                "Duration must be between 1 minute and 28 days (40,320 minutes).",
                ephemeral=True,
            )
            return

        try:
            await member.timeout(timedelta(minutes=duration), reason=reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't timeout that member. Check that I have the Moderate Members "
                "permission and that my role is above the member's role.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord rejected the timeout request. Please try again.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Timed out {member.mention} for {duration} minute(s).\n"
            f"Reason: {reason}"
        )

    @command_tree.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(member="Member to kick", reason="Reason for the kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ) -> None:
        if not reason.strip():
            await interaction.response.send_message(
                "A reason is required for the kick.",
                ephemeral=True,
            )
            return

        try:
            await member.kick(reason=reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't kick that member. Check that I have the Kick Members "
                "permission and that my role is above the member's role.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord rejected the kick request. Please try again.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Kicked {member.mention}.\nReason: {reason}"
        )

    @kick.error
    async def kick_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Kick Members permission to use this command.",
                ephemeral=True,
            )

    @command_tree.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(member="Member to ban", reason="Reason for the ban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ) -> None:
        if not reason.strip():
            await interaction.response.send_message(
                "A reason is required for the ban.",
                ephemeral=True,
            )
            return

        try:
            await member.ban(reason=reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't ban that member. Check that I have the Ban Members "
                "permission and that my role is above the member's role.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord rejected the ban request. Please try again.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Banned {member.mention}.\nReason: {reason}"
        )

    @ban.error
    async def ban_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Ban Members permission to use this command.",
                ephemeral=True,
            )

    @command_tree.command(name="clear", description="Delete recent messages from this channel.")
    @app_commands.describe(amount="Number of recent messages to delete (1-100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(
        interaction: discord.Interaction,
        amount: int,
    ) -> None:
        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                "Amount must be between 1 and 100 messages.",
                ephemeral=True,
            )
            return

        channel = interaction.channel
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            await interaction.response.send_message(
                "Messages can only be cleared from a text channel.",
                ephemeral=True,
            )
            return

        try:
            removed_messages = await channel.purge(limit=amount)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't delete messages. Check that I have the Manage Messages "
                "permission in this channel.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord rejected the message deletion request. Please try again.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Removed {len(removed_messages)} message(s)."
        )

    @clear.error
    async def clear_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You need the Manage Messages permission to use this command.",
                ephemeral=True,
            )

    @client.event
    async def setup_hook() -> None:
        await command_tree.sync()

    @client.event
    async def on_ready() -> None:
        nonlocal reminder_task
        if reminder_task is None or reminder_task.done():
            reminder_task = asyncio.create_task(reminder_worker())
        for guild in client.guilds:
            command_tree.copy_global_to(guild=guild)
            await command_tree.sync(guild=guild)
        print(f"Connected to Discord as {client.user}.")

    client.run(token)


if __name__ == "__main__":
    main()