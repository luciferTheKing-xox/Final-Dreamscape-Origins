"""Offline regression and stability tests for the Discord bot.

These tests deliberately use fakes for Discord interactions. They validate the
bot's local state machines, persistence, command registration, and error paths
without connecting to Discord or requiring a real token.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import discord
from discord import app_commands

import main
import new_games


class FakeResponse:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.done = False
        self.raise_error: Exception | None = None

    def is_done(self) -> bool:
        return self.done

    async def send_message(self, content: str | None = None, **kwargs: object) -> None:
        if self.raise_error:
            error = self.raise_error
            self.raise_error = None
            raise error
        self.done = True
        self.calls.append({"method": "send_message", "content": content, **kwargs})

    async def edit_message(self, **kwargs: object) -> None:
        if self.raise_error:
            error = self.raise_error
            self.raise_error = None
            raise error
        self.done = True
        self.calls.append({"method": "edit_message", **kwargs})

    async def defer(self, **kwargs: object) -> None:
        self.done = True
        self.calls.append({"method": "defer", **kwargs})


class FakeFollowup:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def send(self, content: str | None = None, **kwargs: object) -> None:
        self.calls.append({"content": content, **kwargs})


class FakeMessage:
    def __init__(self, message_id: int = 1, embed: discord.Embed | None = None) -> None:
        self.id = message_id
        self.embeds = [embed] if embed else []
        self.view: discord.ui.View | None = None
        self.edits: list[dict[str, object]] = []
        self.reactions: list[str] = []

    async def edit(
        self,
        *,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
    ) -> None:
        if embed is not None:
            self.embeds = [embed]
        self.view = view
        self.edits.append({"embed": embed, "view": view})

    async def add_reaction(self, emoji: str) -> None:
        self.reactions.append(emoji)


class FakeUser:
    def __init__(self, user_id: int, name: str | None = None, *, bot: bool = False) -> None:
        self.id = user_id
        self.name = name or f"user-{user_id}"
        self.display_name = self.name
        self.mention = f"<@{user_id}>"
        self.bot = bot
        self.display_avatar = SimpleNamespace(url=f"https://cdn.example/{user_id}.png")
        self.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.joined_at = datetime(2021, 1, 1, tzinfo=timezone.utc)
        self.roles: list[FakeRole] = []
        self.sent_messages: list[str] = []
        self.kicked = False
        self.banned = False
        self.timed_out_for: object | None = None
        self.edits: list[dict[str, object]] = []

    async def send(self, content: str) -> None:
        self.sent_messages.append(content)

    async def kick(self, *, reason: str) -> None:
        self.kicked = True

    async def ban(self, *, reason: str) -> None:
        self.banned = True

    async def timeout(self, duration: object, *, reason: str) -> None:
        self.timed_out_for = duration

    async def edit(self, *, nick: str | None, reason: str) -> None:
        self.display_name = nick or self.name
        self.edits.append({"nick": nick, "reason": reason})


class FakeRole:
    def __init__(
        self,
        name: str,
        role_id: int,
        *,
        default: bool = False,
        position: int = 1,
        manage_channels: bool = False,
        administrator: bool = False,
    ) -> None:
        self.name = name
        self.id = role_id
        self.position = position
        self.permissions = SimpleNamespace(
            manage_channels=manage_channels,
            administrator=administrator,
        )
        self.mention = f"<@&{role_id}>"
        self._default = default

    def is_default(self) -> bool:
        return self._default

    def __ge__(self, other: object) -> bool:
        return self.position >= getattr(other, "position", 0)


class FakeGuild:
    def __init__(self, guild_id: int = 99) -> None:
        self.id = guild_id
        self.name = "Regression Server"
        self.owner_id = 1
        self.owner = None
        self.members: list[FakeUser] = []
        self.member_count = 0
        self.channels: list[object] = []
        self.roles: list[FakeRole] = []
        self.default_role = FakeRole("@everyone", 0, default=True, position=0)
        self.me = None
        self.icon = None
        self.created_at = datetime(2019, 1, 1, tzinfo=timezone.utc)

    def get_member(self, member_id: int) -> FakeUser | None:
        return next((member for member in self.members if member.id == member_id), None)


class FakeChannel:
    mention = "#regression"


class FakeInteraction:
    def __init__(
        self,
        user: FakeUser | None = None,
        *,
        channel_id: int = 123,
        guild: FakeGuild | None = None,
        message: FakeMessage | None = None,
    ) -> None:
        self.user = user or FakeUser(1, "Owner")
        self.channel_id = channel_id
        self.guild = guild
        self.channel = FakeChannel()
        self.message = message or FakeMessage()
        self.response = FakeResponse()
        self.followup = FakeFollowup()

    async def original_response(self) -> FakeMessage:
        return self.message


def button(view: discord.ui.View, label: str) -> discord.ui.Button:
    for child in view.children:
        if isinstance(child, discord.ui.Button) and child.label == label:
            return child
    raise AssertionError(f"Button not found: {label}")


def response_text(interaction: FakeInteraction) -> str:
    if not interaction.response.calls:
        return ""
    return str(interaction.response.calls[-1].get("content", ""))


class CommandRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        root = Path(cls.tempdir.name)
        cls.warning_path = root / "warnings.json"
        cls.reminder_path = root / "reminders.json"
        cls.questions_path = root / "game_questions.json"
        cls.content_path = root / "game_content.json"
        cls.captured: dict[str, object] = {}

        original_tree = main.app_commands.CommandTree

        class CapturingTree(original_tree):
            def __init__(self, client: discord.Client) -> None:
                super().__init__(client)
                CommandRegistrationTests.captured["tree"] = self

        def fake_run(client: discord.Client, token: str) -> None:
            CommandRegistrationTests.captured["client"] = client
            CommandRegistrationTests.captured["token"] = token

        with (
            patch.object(main.app_commands, "CommandTree", CapturingTree),
            patch.object(discord.Client, "run", fake_run),
            patch.object(main, "WARNING_STORE_PATH", cls.warning_path),
            patch.object(main, "REMINDER_STORE_PATH", cls.reminder_path),
            patch.object(main, "GAME_QUESTION_STORE_PATH", cls.questions_path),
            patch.object(new_games, "CONTENT_STORE_PATH", cls.content_path),
            patch.dict(os.environ, {"DISCORD_TOKEN": "offline-test-token"}, clear=False),
        ):
            main.main()

        cls.tree = cls.captured["tree"]
        cls.client = cls.captured["client"]
        cls.commands = {command.name: command for command in cls.tree.get_commands()}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def test_all_commands_register(self) -> None:
        expected = {
            "ping",
            "tod",
            "paranoia",
            "nhie",
            "wouldyourather",
            "gamequestions",
            "addquestion",
            "removequestion",
            "listquestions",
            "avatar",
            "role",
            "nick",
            "whois",
            "remind",
            "8ball",
            "roll",
            "coinflip",
            "warn",
            "warnings",
            "unwarn",
            "lock",
            "unlock",
            "slowmode",
            "serverinfo",
            "announce",
            "poll",
            "userinfo",
            "timeout",
            "kick",
            "ban",
            "clear",
            "mostlikelyto",
            "twotruthsonelie",
            "hotseat",
            "emojidecode",
            "guesstheplayer",
            "trivia",
            "memebattle",
            "captionthis",
            "addgamecontent",
            "removegamecontent",
            "listgamecontent",
        }
        self.assertEqual(set(self.commands), expected)
        self.assertTrue(self.client.intents.members)

    def test_moderation_commands_have_permission_checks(self) -> None:
        expected_permissions = {
            "addquestion",
            "removequestion",
            "listquestions",
            "role",
            "nick",
            "warn",
            "unwarn",
            "lock",
            "unlock",
            "slowmode",
            "announce",
            "timeout",
            "kick",
            "ban",
            "clear",
            "addgamecontent",
            "removegamecontent",
            "listgamecontent",
        }
        for name in expected_permissions:
            self.assertTrue(self.commands[name].checks, name)

    def test_content_management_choices_exclude_live_member_games(self) -> None:
        values = {choice.value for choice in new_games.CATALOG_GAME_CHOICES}
        self.assertEqual(
            values,
            {"mostlikelyto", "hotseat", "emojidecode", "trivia", "memebattle", "captionthis"},
        )


class PersistenceTests(unittest.TestCase):
    def test_duration_parser_and_json_round_trips(self) -> None:
        self.assertEqual(main.parse_reminder_duration("30s"), 30)
        self.assertEqual(main.parse_reminder_duration("10m"), 600)
        self.assertEqual(main.parse_reminder_duration("2h"), 7200)
        self.assertEqual(main.parse_reminder_duration("1d"), 86400)
        self.assertIsNone(main.parse_reminder_duration("0s"))
        self.assertIsNone(main.parse_reminder_duration("366d"))
        self.assertIsNone(main.parse_reminder_duration("nonsense"))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            warning_path = root / "warnings.json"
            reminder_path = root / "reminders.json"
            question_path = root / "questions.json"
            content_path = root / "content.json"

            warnings = {"9": {"5": [{"reason": "test", "date": "2026-01-01"}]}}
            reminders = [{"user_id": 5, "message": "test", "due_at": "2026-01-01T00:00:00+00:00"}]
            with patch.object(main, "WARNING_STORE_PATH", warning_path):
                main.save_warning_store(warnings)
                self.assertEqual(main.load_warning_store(), warnings)
            with patch.object(main, "REMINDER_STORE_PATH", reminder_path):
                main.save_reminder_store(reminders)
                self.assertEqual(main.load_reminder_store(), reminders)
            with patch.object(main, "GAME_QUESTION_STORE_PATH", question_path):
                question_store = main.load_game_question_store()
                self.assertTrue(question_path.exists())
                question_store["truth"].append({"id": "truth-custom-001", "prompt": "test"})
                main.save_game_question_store(question_store)
                self.assertEqual(json.loads(question_path.read_text())["truth"][-1]["id"], "truth-custom-001")
            with patch.object(new_games, "CONTENT_STORE_PATH", content_path):
                content_store = new_games.load_content_store()
                self.assertTrue(content_path.exists())
                content_store["memebattle"].append({"id": "memebattle-custom-001", "prompt": "test"})
                new_games._save_json(content_path, content_store)
                reloaded = new_games.load_content_store()
                self.assertIn(
                    "memebattle-custom-001",
                    {str(record["id"]) for record in reloaded["memebattle"]},
                )

            self.assertIsInstance(json.loads(question_path.read_text()), dict)
            self.assertIsInstance(json.loads(content_path.read_text()), dict)

    def test_invalid_json_rebuilds_valid_catalogs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            question_path = root / "questions.json"
            content_path = root / "content.json"
            question_path.write_text("{not json", encoding="utf-8")
            content_path.write_text("[not an object]", encoding="utf-8")
            with patch.object(main, "GAME_QUESTION_STORE_PATH", question_path):
                question_store = main.load_game_question_store()
            with patch.object(new_games, "CONTENT_STORE_PATH", content_path):
                content_store = new_games.load_content_store()
            self.assertIn("truth", question_store)
            self.assertIn("trivia", content_store)
            self.assertIsInstance(json.loads(question_path.read_text()), dict)
            self.assertIsInstance(json.loads(content_path.read_text()), dict)

    def test_malformed_records_are_ignored_without_breaking_writes(self) -> None:
        malformed_questions: dict[str, object] = {"truth": ["bad", {"id": "good", "prompt": "Good"}]}
        questions = main.get_game_questions(malformed_questions, "truth")
        self.assertEqual([question["id"] for question in questions], ["good"])
        questions.append({"id": "new", "prompt": "New"})
        self.assertEqual(malformed_questions["truth"][-1]["id"], "new")

        malformed_content: dict[str, object] = {"trivia": ["bad", {"id": "good"}]}
        records = new_games.content_records(malformed_content, "trivia")
        self.assertEqual([record["id"] for record in records], ["good"])
        records.append({"id": "new"})
        self.assertEqual(malformed_content["trivia"][-1]["id"], "new")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            warning_path = root / "warnings.json"
            reminder_path = root / "reminders.json"
            warning_path.write_text(
                json.dumps({"guild": "bad", "good": {"member": [{"reason": "ok"}]}}),
                encoding="utf-8",
            )
            reminder_path.write_text(
                json.dumps(["bad", {"user_id": 1, "message": "ok"}]),
                encoding="utf-8",
            )
            with patch.object(main, "WARNING_STORE_PATH", warning_path):
                self.assertEqual(main.load_warning_store(), {"good": {"member": [{"reason": "ok"}]}})
            with patch.object(main, "REMINDER_STORE_PATH", reminder_path):
                self.assertEqual(main.load_reminder_store(), [{"user_id": 1, "message": "ok"}])

    def test_selection_randomization_no_repeat_and_empty_pools(self) -> None:
        questions = {"truth": [{"id": "a", "prompt": "A"}, {"id": "b", "prompt": "B"}]}
        used_questions: set[str] = set()
        first = main.choose_game_question(questions, "truth", used_questions)
        second = main.choose_game_question(questions, "truth", used_questions)
        self.assertNotEqual(first["id"], second["id"])
        self.assertIsNotNone(main.choose_game_question(questions, "truth", used_questions))
        self.assertIsNone(main.choose_game_question({}, "truth", set()))

        content = {"trivia": [{"id": "a"}, {"id": "b"}]}
        used_content: set[str] = set()
        first_content = new_games.choose_content(content, "trivia", used_content)
        second_content = new_games.choose_content(content, "trivia", used_content)
        self.assertNotEqual(first_content["id"], second_content["id"])
        self.assertIsNotNone(new_games.choose_content(content, "trivia", used_content))
        self.assertIsNone(new_games.choose_content({}, "trivia", set()))
        self.assertIsNone(main.choose_game_question({"truth": ["malformed"]}, "truth", set()))
        self.assertIsNone(new_games.choose_content({"trivia": ["malformed"]}, "trivia", set()))


class InteractionAndGameTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.active: dict[int, discord.ui.View] = {}
        self.question_store = main.build_seed_question_store()
        self.content_store = {
            "mostlikelyto": [{"id": "mlt-1", "prompt": "Who plans the snack run?"}, {"id": "mlt-2", "prompt": "Who solves the puzzle?"}],
            "hotseat": [{"id": "hot-1", "prompt": "What is your favorite harmless hobby?"}, {"id": "hot-2", "prompt": "What would you learn instantly?"}],
            "emojidecode": [{"id": "emoji-1", "prompt": "🍎📱", "answer": "Apple", "alternatives": ["Apple Inc"]}],
            "trivia": [{"id": "trivia-1", "prompt": "Two plus two?", "answer": "4", "options": ["4", "3", "5", "6"]}, {"id": "trivia-2", "prompt": "Sky color?", "answer": "Blue", "options": ["Blue", "Red", "Green", "Black"]}],
            "memebattle": [{"id": "meme-1", "prompt": "Caption scene one"}, {"id": "meme-2", "prompt": "Caption scene two"}],
            "captionthis": [{"id": "caption-1", "prompt": "Caption image one"}, {"id": "caption-2", "prompt": "Caption image two"}],
            "twotruthsonelie": [],
            "guesstheplayer": [],
        }
        self.owner = FakeUser(1, "Owner")
        self.other = FakeUser(2, "Other")

    async def test_existing_game_buttons_and_session_lifecycle(self) -> None:
        start = main.TodStartView(self.owner.id, self.owner.display_name, self.question_store, self.active)
        message = FakeMessage(100, start.render_embed() if hasattr(start, "render_embed") else None)
        start.attach(message)
        interaction = FakeInteraction(self.owner, message=message)
        await button(start, "Truth").callback(interaction)
        self.assertIsInstance(interaction.response.calls[-1]["view"], main.TodPromptView)
        prompt_view = interaction.response.calls[-1]["view"]
        self.assertIn("truth", prompt_view.used_ids)
        await button(prompt_view, "Next").callback(FakeInteraction(self.owner, message=message))
        self.assertEqual(len(prompt_view.used_ids["truth"]), 2)

        paranoia_question = self.question_store["paranoia"][0]
        paranoia = main.ParanoiaView(
            self.owner.id,
            self.owner.display_name,
            self.question_store,
            self.active,
            paranoia_question,
            {"paranoia": {paranoia_question["id"]}},
        )
        paranoia.attach(FakeMessage(101, main.game_embed("Paranoia", paranoia_question["prompt"], "Owner")))
        await button(paranoia, "Next Question").callback(FakeInteraction(self.owner, message=paranoia.message))
        self.assertNotEqual(paranoia.question["id"], paranoia_question["id"])

        nhie_question = self.question_store["nhie"][0]
        nhie = main.NhieView(
            self.owner.id,
            self.owner.display_name,
            self.question_store,
            self.active,
            nhie_question,
            {"nhie": set()},
        )
        await button(nhie, "I Have").callback(FakeInteraction(self.other))
        await button(nhie, "Never").callback(FakeInteraction(self.other))
        self.assertEqual(len(nhie.answers), 1)

        wyr_question = self.question_store["wouldyourather"][0]
        wyr = main.WouldYouRatherView(
            self.owner.id,
            self.owner.display_name,
            self.question_store,
            self.active,
            wyr_question,
            {"wouldyourather": set()},
        )
        await wyr.children[0].callback(FakeInteraction(self.other))
        await wyr.children[1].callback(FakeInteraction(self.other))
        self.assertEqual(len(wyr.votes), 1)

        end_message = FakeMessage(102, wyr.render_embed())
        wyr.attach(end_message)
        await button(wyr, "End Game").callback(FakeInteraction(self.owner, message=end_message))
        self.assertNotIn(end_message.id, self.active)
        self.assertTrue(wyr.is_finished())

    async def test_new_games_callbacks_isolation_and_empty_pools(self) -> None:
        question = self.content_store["mostlikelyto"][0]
        most = new_games.MostLikelyToView(
            self.owner.id,
            self.owner.display_name,
            self.content_store,
            self.active,
            10,
            question=question,
        )
        other_channel = FakeInteraction(self.owner, channel_id=11)
        await button(most, "👤 Choose Player").callback(other_channel)
        self.assertIn("another channel", response_text(other_channel))

        second = new_games.MostLikelyToView(
            self.owner.id,
            self.owner.display_name,
            self.content_store,
            self.active,
            20,
            question=self.content_store["mostlikelyto"][1],
        )
        first_message = FakeMessage(201, most.render())
        second_message = FakeMessage(202, second.render())
        most.attach(first_message)
        second.attach(second_message)
        self.assertIs(self.active[201], most)
        self.assertIs(self.active[202], second)

        owner_wrong = FakeInteraction(self.other, channel_id=10)
        await button(most, "🛑 End Game").callback(owner_wrong)
        self.assertIn("Only the person", response_text(owner_wrong))

        emoji = new_games.EmojiDecodeView(
            self.owner.id,
            self.owner.display_name,
            self.content_store,
            self.active,
            10,
            puzzle=self.content_store["emojidecode"][0],
        )
        guesser = FakeInteraction(self.other, channel_id=10)
        await emoji.handle_guess(guesser, "wrong")
        self.assertFalse(emoji.solved)
        await emoji.handle_guess(guesser, "apple inc")
        self.assertTrue(emoji.solved)
        solved_again = FakeInteraction(self.owner, channel_id=10)
        await emoji.handle_guess(solved_again, "apple")
        self.assertIn("already solved", response_text(solved_again))

        target = FakeUser(7, "Target")
        guild = FakeGuild()
        guild.members = [target]
        guess = new_games.GuessThePlayerView(
            self.owner.id,
            self.owner.display_name,
            self.content_store,
            self.active,
            10,
            target=target,
            clues=["clue one", "clue two"],
        )
        guild.members.clear()  # simulate the target leaving during the game
        solved_interaction = FakeInteraction(self.other, channel_id=10, guild=guild)
        await guess.handle_guess(solved_interaction, "Target")
        self.assertTrue(guess.solved)

        empty_store = {key: [] for key in self.content_store}
        empty_view = new_games.TriviaView(
            self.owner.id,
            self.owner.display_name,
            empty_store,
            self.active,
            10,
            question={"id": "only", "prompt": "Only", "answer": "yes", "options": ["yes", "no"]},
        )
        empty_next = FakeInteraction(self.owner, channel_id=10)
        await empty_view.next_round(empty_next)
        self.assertIn("no trivia questions", response_text(empty_next).lower())

    async def test_new_games_multiplayer_votes_and_rounds(self) -> None:
        truths = new_games.TwoTruthsView(
            self.owner.id,
            self.owner.display_name,
            self.content_store,
            self.active,
            10,
            statements=["one", "two", "three"],
            lie_number=2,
        )
        vote = FakeInteraction(self.other, channel_id=10)
        await button(truths, "1").callback(vote)
        duplicate = FakeInteraction(self.other, channel_id=10)
        await button(truths, "2").callback(duplicate)
        self.assertEqual(truths.votes, {self.other.id: 1})
        self.assertIn("already voted", response_text(duplicate))
        await button(truths, "Reveal Answer").callback(FakeInteraction(self.owner, channel_id=10))
        self.assertTrue(truths.revealed)
        self.assertTrue(all(child.disabled for child in truths.children if isinstance(child, discord.ui.Button) and child.label in {"1", "2", "3"}))

        trivia = new_games.TriviaView(
            self.owner.id,
            self.owner.display_name,
            self.content_store,
            self.active,
            10,
            question=self.content_store["trivia"][0],
        )
        wrong = FakeInteraction(self.other, channel_id=10)
        wrong_button = next(child for child in trivia.answer_buttons if child.label.endswith("3"))
        await wrong_button.callback(wrong)
        duplicate_wrong = FakeInteraction(self.other, channel_id=10)
        await wrong_button.callback(duplicate_wrong)
        self.assertEqual(trivia.incorrect_users, {self.other.id})
        self.assertIn("already missed", response_text(duplicate_wrong))

        meme = new_games.MemeBattleView(
            self.owner.id,
            self.owner.display_name,
            self.content_store,
            self.active,
            10,
            prompt=self.content_store["memebattle"][0],
        )
        self.assertEqual(meme.submit_response.label, "✍️ Submit Response")
        meme.submissions = {index: (f"Player {index}", f"Response {index}") for index in range(14)}
        meme.phase = "voting"
        meme._add_vote_buttons()
        row_counts: dict[int | None, int] = {}
        for child in meme.children:
            row = getattr(child, "row", None)
            row_counts[row] = row_counts.get(row, 0) + 1
        self.assertLessEqual(max(row_counts.values()), 5)
        self.assertLessEqual(len(meme.children), 25)

        voter = FakeInteraction(self.other, channel_id=10)
        await meme.vote_buttons[0].callback(voter)
        duplicate_vote = FakeInteraction(self.other, channel_id=10)
        await meme.vote_buttons[1].callback(duplicate_vote)
        self.assertEqual(len(meme.votes), 1)
        self.assertIn("already voted", response_text(duplicate_vote))

        caption = new_games.CaptionThisView(
            self.owner.id,
            self.owner.display_name,
            self.content_store,
            self.active,
            10,
            prompt=self.content_store["captionthis"][0],
        )
        self.assertEqual(caption.submit_response.label, "✍️ Submit Caption")

    async def test_timeout_and_http_error_paths(self) -> None:
        view = new_games.TriviaView(
            self.owner.id,
            self.owner.display_name,
            self.content_store,
            self.active,
            10,
            question=self.content_store["trivia"][0],
        )
        message = FakeMessage(300, view.render())
        view.attach(message)
        await view.on_timeout()
        self.assertTrue(all(child.disabled for child in view.children if isinstance(child, discord.ui.Button)))
        self.assertNotIn(message.id, self.active)
        self.assertIn("Expired", message.embeds[0].footer.text)

        interaction = FakeInteraction(self.other, channel_id=10)
        interaction.response.raise_error = discord.HTTPException(
            SimpleNamespace(status=500, reason="test"),
            "test",
        )
        await new_games._ephemeral(interaction, "ignored")
        self.assertEqual(interaction.response.calls, [])

    async def test_button_row_limits_for_every_view(self) -> None:
        old_views: list[discord.ui.View] = [
            main.TodStartView(1, "Owner", self.question_store, self.active),
            main.ParanoiaView(1, "Owner", self.question_store, self.active, self.question_store["paranoia"][0], {"paranoia": set()}),
            main.NhieView(1, "Owner", self.question_store, self.active, self.question_store["nhie"][0], {"nhie": set()}),
            main.WouldYouRatherView(1, "Owner", self.question_store, self.active, self.question_store["wouldyourather"][0], {"wouldyourather": set()}),
        ]
        hotseat = FakeUser(8, "Hot Seat")
        new_views: list[discord.ui.View] = [
            new_games.MostLikelyToView(1, "Owner", self.content_store, self.active, 1, question=self.content_store["mostlikelyto"][0]),
            new_games.TwoTruthsView(1, "Owner", self.content_store, self.active, 1, statements=["a", "b", "c"], lie_number=1),
            new_games.HotSeatView(1, "Owner", self.content_store, self.active, 1, hotseat=hotseat, question=self.content_store["hotseat"][0]),
            new_games.EmojiDecodeView(1, "Owner", self.content_store, self.active, 1, puzzle=self.content_store["emojidecode"][0]),
            new_games.GuessThePlayerView(1, "Owner", self.content_store, self.active, 1, target=hotseat, clues=["one"]),
            new_games.TriviaView(1, "Owner", self.content_store, self.active, 1, question=self.content_store["trivia"][0]),
            new_games.MemeBattleView(1, "Owner", self.content_store, self.active, 1, prompt=self.content_store["memebattle"][0]),
            new_games.CaptionThisView(1, "Owner", self.content_store, self.active, 1, prompt=self.content_store["captionthis"][0]),
        ]
        for view in old_views + new_views:
            rows: dict[int | None, int] = {}
            for child in view.children:
                row = getattr(child, "row", None)
                rows[row] = rows.get(row, 0) + 1
            self.assertLessEqual(max(rows.values()), 5, (type(view).__name__, rows))
            self.assertLessEqual(len(view.children), 25, type(view).__name__)


class CommandBehaviorTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not hasattr(CommandRegistrationTests, "tree"):
            CommandRegistrationTests.setUpClass()
        cls.tree = CommandRegistrationTests.tree
        cls.tempdir = CommandRegistrationTests.tempdir
        cls.warning_path = CommandRegistrationTests.warning_path
        cls.reminder_path = CommandRegistrationTests.reminder_path
        cls.questions_path = CommandRegistrationTests.questions_path
        cls.content_path = CommandRegistrationTests.content_path

    def command(self, name: str):
        return {command.name: command for command in self.tree.get_commands()}[name].callback

    async def test_warning_and_reminder_persistence(self) -> None:
        guild = FakeGuild(77)
        member = FakeUser(22, "Member")
        interaction = FakeInteraction(FakeUser(1, "Moderator"), guild=guild)
        with patch.object(main, "WARNING_STORE_PATH", self.warning_path):
            await self.command("warn")(interaction, member, "Repeated spam")
            self.assertEqual(len(json.loads(self.warning_path.read_text())["77"]["22"]), 1)
            warnings_interaction = FakeInteraction(FakeUser(1, "Moderator"), guild=guild)
            await self.command("warnings")(warnings_interaction, member)
            self.assertIn("Repeated spam", response_text(warnings_interaction))
            unwarn_interaction = FakeInteraction(FakeUser(1, "Moderator"), guild=guild)
            await self.command("unwarn")(unwarn_interaction, member, 1)
            self.assertNotIn("22", json.loads(self.warning_path.read_text())["77"])

        reminder_interaction = FakeInteraction(FakeUser(33, "Reminder User"))
        with patch.object(main, "REMINDER_STORE_PATH", self.reminder_path):
            await self.command("remind")(reminder_interaction, "10m", "check the game")
        reminders = json.loads(self.reminder_path.read_text())
        self.assertEqual(reminders[0]["user_id"], 33)
        self.assertEqual(reminders[0]["message"], "check the game")

    async def test_question_and_content_management_persistence(self) -> None:
        guild = FakeGuild(88)
        moderator = FakeInteraction(FakeUser(1, "Moderator"), guild=guild)
        category = app_commands.Choice(name="Truth", value="truth")
        with patch.object(main, "GAME_QUESTION_STORE_PATH", self.questions_path):
            await self.command("addquestion")(moderator, category, "A custom regression prompt")
            data = json.loads(self.questions_path.read_text())
            custom = next(item for item in data["truth"] if item["prompt"] == "A custom regression prompt")
            remove_interaction = FakeInteraction(FakeUser(1, "Moderator"), guild=guild)
            await self.command("removequestion")(remove_interaction, custom["id"])
            updated = json.loads(self.questions_path.read_text())
            self.assertNotIn(custom["id"], {item["id"] for item in updated["truth"]})

        content_choice = app_commands.Choice(name="Trivia", value="trivia")
        with patch.object(new_games, "CONTENT_STORE_PATH", self.content_path):
            await self.command("addgamecontent")(
                moderator,
                content_choice,
                "Custom test question",
                "Correct",
                "Wrong one|Wrong two|Wrong three",
            )
            data = json.loads(self.content_path.read_text())
            self.assertTrue(any(item["prompt"] == "Custom test question" for item in data["trivia"]))

    async def test_invalid_inputs_and_permission_errors_are_handled(self) -> None:
        invalid_duration = FakeInteraction()
        await self.command("remind")(invalid_duration, "0s", "message")
        self.assertIn("positive duration", response_text(invalid_duration))

        invalid_question = FakeInteraction()
        await self.command("8ball")(invalid_question, "")
        self.assertIn("between 1 and 500", response_text(invalid_question))

        invalid_roll = FakeInteraction()
        await self.command("roll")(invalid_roll, 0)
        self.assertIn("between 1 and 1,000,000", response_text(invalid_roll))

        invalid_clear = FakeInteraction()
        await self.command("clear")(invalid_clear, 101)
        self.assertIn("between 1 and 100", response_text(invalid_clear))

        invalid_timeout = FakeInteraction()
        await self.command("timeout")(invalid_timeout, FakeUser(4, "Member"), 0, "bad duration")
        self.assertIn("between 1 minute", response_text(invalid_timeout))

        invalid_kick = FakeInteraction()
        await self.command("kick")(invalid_kick, FakeUser(4, "Member"), " ")
        self.assertIn("required for the kick", response_text(invalid_kick))

        invalid_ban = FakeInteraction()
        await self.command("ban")(invalid_ban, FakeUser(4, "Member"), " ")
        self.assertIn("required for the ban", response_text(invalid_ban))

        invalid_lock = FakeInteraction(guild=FakeGuild())
        await self.command("lock")(invalid_lock, " ")
        self.assertIn("reason is required", response_text(invalid_lock).lower())

        invalid_slowmode = FakeInteraction(guild=FakeGuild())
        await self.command("slowmode")(invalid_slowmode, 21601, None)
        self.assertIn("between 0 and 21,600", response_text(invalid_slowmode))

        bad_game_content = FakeInteraction(guild=FakeGuild())
        with patch.object(new_games, "CONTENT_STORE_PATH", self.content_path):
            await self.command("addgamecontent")(
                bad_game_content,
                app_commands.Choice(name="Trivia", value="trivia"),
                "prompt",
                "answer",
                "wrong|wrong|wrong",
            )
        self.assertIn("exactly three unique", response_text(bad_game_content))

        self.assertIn(
            "Manage Messages",
            new_games._permission_error_text(
                app_commands.errors.MissingPermissions(["manage_messages"]),
                "add game content",
            ),
        )


if __name__ == "__main__":
    unittest.main()