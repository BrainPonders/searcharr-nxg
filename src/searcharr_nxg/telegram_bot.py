"""Telegram bot runtime for Searcharr-nxg."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Sequence, Tuple

from searcharr_nxg.domain.decision_model import Action
from searcharr_nxg.integrations.radarr import RadarrOption
from searcharr_nxg.integrations.tmdb import TmdbMovieCandidate
from searcharr_nxg.render import (
    action_label,
    render_candidate_browser_message,
    render_exclusion_override_message,
    render_movie_action_result_message,
    render_movie_inspection_message,
    render_profile_selection_message,
)
from searcharr_nxg.runtime import SearcharrRuntime
from searcharr_nxg.services.movie_actions import resolve_quality_profile_choices
from searcharr_nxg.services.movie_inspection import MovieInspectionReport

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import CallbackContext


_CALLBACK_BROWSE = "browse"
_CALLBACK_SELECT = "select"
_CALLBACK_ACTION = "act"
_CALLBACK_PROFILE = "profile"
_CALLBACK_CONTINUE = "continue"
_CALLBACK_CANCEL = "cancel"


def _browse_callback(direction: int) -> str:
    return f"{_CALLBACK_BROWSE}:{direction}"


def _select_callback() -> str:
    return _CALLBACK_SELECT


def _action_callback(tmdb_id: int, action: Action) -> str:
    return f"{_CALLBACK_ACTION}:{tmdb_id}:{action.value}"


def _profile_callback(tmdb_id: int, action: Action, profile_id: int) -> str:
    return f"{_CALLBACK_PROFILE}:{tmdb_id}:{action.value}:{profile_id}"


def _cancel_callback(scope: str) -> str:
    return f"{_CALLBACK_CANCEL}:{scope}"


def _continue_callback(tmdb_id: int, action: Action) -> str:
    return f"{_CALLBACK_CONTINUE}:{tmdb_id}:{action.value}"


def _parse_callback(data: str) -> Tuple[str, List[str]]:
    parts = data.split(":")
    return parts[0], parts[1:]


def _browser_state_key(chat_id: int) -> str:
    return f"movie_browser:{chat_id}"


def _tmdb_movie_url(tmdb_id: int) -> str:
    return f"https://www.themoviedb.org/movie/{tmdb_id}"


def browser_button_rows(candidate: TmdbMovieCandidate) -> List[List[dict]]:
    """Build browser controls for a single TMDB candidate."""

    return [
        [
            {"text": "<", "callback_data": _browse_callback(-1)},
            {"text": "TMDB", "url": _tmdb_movie_url(candidate.tmdb_id)},
            {"text": ">", "callback_data": _browse_callback(1)},
        ],
        [
            {"text": "Select", "callback_data": _select_callback()},
            {"text": "Cancel", "callback_data": _cancel_callback("search")},
        ],
    ]


def action_button_rows(report: MovieInspectionReport) -> List[List[dict]]:
    """Build button labels and callback payloads for allowed actions."""

    buttons = [
        {"text": action_label(action), "callback_data": _action_callback(report.candidate.tmdb_id, action)}
        for action in report.actions
    ]
    rows = [buttons[index:index + 2] for index in range(0, len(buttons), 2)]
    rows.append([{"text": "Cancel", "callback_data": _cancel_callback("action")}])
    return rows


def exclusion_button_rows(tmdb_id: int, action: Action) -> List[List[dict]]:
    """Build manual override controls for excluded titles."""

    return [
        [{"text": f"{action_label(action)} Anyway", "callback_data": _continue_callback(tmdb_id, action)}],
        [{"text": "Cancel", "callback_data": _cancel_callback("action")}],
    ]


def profile_button_rows(
    tmdb_id: int,
    action: Action,
    options: Sequence[RadarrOption],
) -> List[List[dict]]:
    """Build profile-selection controls for add/change-profile actions."""

    rows = [
        [{"text": option.name, "callback_data": _profile_callback(tmdb_id, action, option.id)}]
        for option in options
    ]
    rows.append([{"text": "Cancel", "callback_data": _cancel_callback("action")}])
    return rows


def _build_inline_keyboard(rows: Sequence[Sequence[dict]]):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard_rows = []
    for row in rows:
        buttons = []
        for item in row:
            if "url" in item:
                buttons.append(InlineKeyboardButton(item["text"], url=item["url"]))
            else:
                buttons.append(InlineKeyboardButton(item["text"], callback_data=item["callback_data"]))
        keyboard_rows.append(buttons)
    return InlineKeyboardMarkup(keyboard_rows)


def build_browser_keyboard(candidate: TmdbMovieCandidate):
    """Build the inline keyboard for browsing TMDB candidates."""

    return _build_inline_keyboard(browser_button_rows(candidate))


def build_action_keyboard(report: MovieInspectionReport):
    """Build the inline keyboard for allowed actions."""

    return _build_inline_keyboard(action_button_rows(report))


def build_profile_keyboard(tmdb_id: int, action: Action, options: Sequence[RadarrOption]):
    """Build the inline keyboard for profile selection."""

    return _build_inline_keyboard(profile_button_rows(tmdb_id, action, options))


def build_exclusion_keyboard(tmdb_id: int, action: Action):
    """Build the inline keyboard for excluded titles."""

    return _build_inline_keyboard(exclusion_button_rows(tmdb_id, action))


class TelegramBotService:
    """Small polling-based Telegram runtime for Searcharr-nxg."""

    def __init__(self, runtime: SearcharrRuntime, logger: logging.Logger) -> None:
        self.runtime = runtime
        self.logger = logger

    def run(self, token: str) -> None:
        """Start the Telegram polling loop."""

        from telegram.ext import CallbackQueryHandler, CommandHandler, Updater

        updater = Updater(token=token, use_context=True)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CommandHandler("start", self._handle_start))
        dispatcher.add_handler(CommandHandler("help", self._handle_help))
        dispatcher.add_handler(CommandHandler("movie", self._handle_movie))
        dispatcher.add_handler(CallbackQueryHandler(self._handle_callback))

        self.logger.info("Starting Telegram bot polling.")
        updater.start_polling()
        updater.idle()

    def _handle_start(self, update: "Update", context: "CallbackContext") -> None:
        self._reply(
            update,
            "Searcharr-nxg is online.\nUse /movie &lt;title&gt; to browse a movie, then inspect the Orion stack.",
        )

    def _handle_help(self, update: "Update", context: "CallbackContext") -> None:
        self._reply(
            update,
            "Commands:\n/movie &lt;title&gt;  Browse TMDB candidates with posters, then inspect Ryot and Radarr state.",
        )

    def _handle_movie(self, update: "Update", context: "CallbackContext") -> None:
        query = " ".join(context.args or []).strip()
        if not query:
            self._reply(update, "Usage: /movie &lt;title&gt;")
            return

        try:
            candidates = list(self.runtime.search_movie_candidates(query, limit=20))
        except RuntimeError as exc:
            self._reply(update, str(exc))
            return

        if not candidates:
            self._reply(update, f'No TMDB candidates found for "{query}".')
            return

        self._close_previous_browser_state(context, update.effective_chat.id if update.effective_chat else 0)
        browser_state = {
            "query": query,
            "index": 0,
            "candidates": candidates,
            "message_id": None,
        }
        self._set_browser_state(context, update.effective_chat.id if update.effective_chat else 0, browser_state)
        self._send_candidate_card(update, browser_state)

    def _handle_callback(self, update: "Update", context: "CallbackContext") -> None:
        query = update.callback_query
        if query is None or query.data is None:
            return

        query.answer()
        kind, args = _parse_callback(query.data)
        try:
            if kind == _CALLBACK_BROWSE:
                self._handle_browse_callback(query, context, int(args[0]))
                return
            if kind == _CALLBACK_SELECT:
                self._handle_select_callback(query, context)
                return
            if kind == _CALLBACK_ACTION:
                self._handle_action_callback(query, Action(args[1]), int(args[0]))
                return
            if kind == _CALLBACK_PROFILE:
                self._handle_profile_callback(query, Action(args[1]), int(args[0]), args[2])
                return
            if kind == _CALLBACK_CONTINUE:
                self._handle_continue_callback(query, Action(args[1]), int(args[0]))
                return
            if kind == _CALLBACK_CANCEL:
                self._handle_cancel_callback(query, args[0] if args else "request")
                return
        except (RuntimeError, ValueError) as exc:
            self.logger.warning("Telegram callback failed: %s", exc)
            self._edit_message(query, f"Request failed: {exc}")
            return

        self._edit_message(query, "Unsupported callback payload.")

    def _handle_browse_callback(self, query, context: "CallbackContext", direction: int) -> None:
        browser_state = self._require_browser_state(context, query)
        candidates = browser_state["candidates"]
        browser_state["index"] = (browser_state["index"] + direction) % len(candidates)
        self._set_browser_state(context, query.message.chat_id, browser_state)
        self._render_candidate_card(query, browser_state)

    def _handle_select_callback(self, query, context: "CallbackContext") -> None:
        browser_state = self._require_browser_state(context, query)
        candidate = browser_state["candidates"][browser_state["index"]]
        report = self.runtime.inspect_tmdb_movie(candidate.tmdb_id)
        self._edit_message(
            query,
            render_movie_inspection_message(report),
            reply_markup=build_action_keyboard(report),
        )

    def _handle_action_callback(self, query, action: Action, tmdb_id: int) -> None:
        report = self.runtime.inspect_tmdb_movie(tmdb_id)
        if action in (Action.ADD_MOVIE, Action.ADD_AND_SEARCH) and report.radarr.is_excluded:
            self._edit_message(
                query,
                render_exclusion_override_message(report, action),
                reply_markup=build_exclusion_keyboard(tmdb_id, action),
            )
            return
        if self._needs_quality_profile_selection(action):
            options = self._quality_profile_options()
            if len(options) > 1:
                self._edit_message(
                    query,
                    render_profile_selection_message(report, action),
                    reply_markup=build_profile_keyboard(tmdb_id, action, options),
                )
                return

        preview = self.runtime.perform_movie_action(
            tmdb_id=tmdb_id,
            action=action,
            execute=True,
        )
        refreshed = self.runtime.inspect_tmdb_movie(tmdb_id)
        self._edit_message(
            query,
            f"{render_movie_action_result_message(preview)}\n\n{render_movie_inspection_message(refreshed)}",
            reply_markup=build_action_keyboard(refreshed),
        )

    def _handle_continue_callback(self, query, action: Action, tmdb_id: int) -> None:
        report = self.runtime.inspect_tmdb_movie(tmdb_id)
        if self._needs_quality_profile_selection(action):
            options = self._quality_profile_options()
            if len(options) > 1:
                self._edit_message(
                    query,
                    render_profile_selection_message(report, action),
                    reply_markup=build_profile_keyboard(tmdb_id, action, options),
                )
                return

        preview = self.runtime.perform_movie_action(
            tmdb_id=tmdb_id,
            action=action,
            execute=True,
        )
        refreshed = self.runtime.inspect_tmdb_movie(tmdb_id)
        self._edit_message(
            query,
            f"{render_movie_action_result_message(preview)}\n\n{render_movie_inspection_message(refreshed)}",
            reply_markup=build_action_keyboard(refreshed),
        )

    def _handle_profile_callback(
        self,
        query,
        action: Action,
        tmdb_id: int,
        profile_id: str,
    ) -> None:
        preview = self.runtime.perform_movie_action(
            tmdb_id=tmdb_id,
            action=action,
            execute=True,
            quality_profile=profile_id,
        )
        refreshed = self.runtime.inspect_tmdb_movie(tmdb_id)
        self._edit_message(
            query,
            f"{render_movie_action_result_message(preview)}\n\n{render_movie_inspection_message(refreshed)}",
            reply_markup=build_action_keyboard(refreshed),
        )

    def _handle_cancel_callback(self, query, scope: str) -> None:
        if scope == "search":
            self._edit_message(query, "Search cancelled.")
            return
        self._edit_message(query, "Action cancelled.")

    def _quality_profile_options(self) -> List[RadarrOption]:
        if self.runtime.radarr_client is None:
            raise RuntimeError("Radarr must be enabled to select quality profiles.")
        return resolve_quality_profile_choices(
            radarr_client=self.runtime.radarr_client,
            settings_module=self.runtime.settings_module,
        )

    @staticmethod
    def _needs_quality_profile_selection(action: Action) -> bool:
        return action in (Action.ADD_MOVIE, Action.ADD_AND_SEARCH, Action.CHANGE_PROFILE)

    def _send_candidate_card(self, update: "Update", browser_state: Dict) -> None:
        candidate = browser_state["candidates"][browser_state["index"]]
        position = browser_state["index"] + 1
        total = len(browser_state["candidates"])
        caption = render_candidate_browser_message(candidate, position, total)
        keyboard = build_browser_keyboard(candidate)
        if update.effective_message is None:
            return
        if candidate.poster_url:
            sent = update.effective_message.reply_photo(
                photo=candidate.poster_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            browser_state["message_id"] = sent.message_id
            return
        sent = update.effective_message.reply_text(caption, parse_mode="HTML", reply_markup=keyboard)
        browser_state["message_id"] = sent.message_id

    def _render_candidate_card(self, query, browser_state: Dict) -> None:
        from telegram import InputMediaPhoto

        candidate = browser_state["candidates"][browser_state["index"]]
        position = browser_state["index"] + 1
        total = len(browser_state["candidates"])
        caption = render_candidate_browser_message(candidate, position, total)
        keyboard = build_browser_keyboard(candidate)
        message = query.message
        if message is None:
            return

        if candidate.poster_url and getattr(message, "photo", None):
            query.edit_message_media(
                media=InputMediaPhoto(media=candidate.poster_url, caption=caption, parse_mode="HTML"),
                reply_markup=keyboard,
            )
            browser_state["message_id"] = message.message_id
            return
        if candidate.poster_url:
            message.delete()
            sent = message.chat.send_photo(
                photo=candidate.poster_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            browser_state["message_id"] = sent.message_id
            return
        if getattr(message, "photo", None):
            message.delete()
            sent = message.chat.send_message(text=caption, parse_mode="HTML", reply_markup=keyboard)
            browser_state["message_id"] = sent.message_id
            return
        query.edit_message_text(text=caption, parse_mode="HTML", reply_markup=keyboard)
        browser_state["message_id"] = message.message_id

    def _require_browser_state(self, context: "CallbackContext", query) -> Dict:
        if query.message is None:
            raise RuntimeError("No Telegram message context was found.")
        state = self._get_browser_state(context, query.message.chat_id)
        if state is None:
            raise RuntimeError("The movie browser expired. Start again with /movie <title>.")
        if state.get("message_id") != query.message.message_id:
            raise RuntimeError("This movie browser expired. Start again with /movie <title>.")
        return state

    @staticmethod
    def _get_browser_state(context: "CallbackContext", chat_id: int) -> Dict | None:
        return context.user_data.get(_browser_state_key(chat_id))

    @staticmethod
    def _set_browser_state(context: "CallbackContext", chat_id: int, state: Dict) -> None:
        context.user_data[_browser_state_key(chat_id)] = state

    def _close_previous_browser_state(self, context: "CallbackContext", chat_id: int) -> None:
        state = self._get_browser_state(context, chat_id)
        if state is None or state.get("message_id") is None:
            return
        try:
            context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=state["message_id"],
                caption="Search cancelled by a new query.",
                parse_mode="HTML",
                reply_markup=None,
            )
        except Exception:
            try:
                context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=state["message_id"],
                    text="Search cancelled by a new query.",
                    parse_mode="HTML",
                    reply_markup=None,
                )
            except Exception:
                pass
        context.user_data.pop(_browser_state_key(chat_id), None)

    @staticmethod
    def _reply(update: "Update", text: str, reply_markup=None) -> None:
        if update.effective_message is None:
            return
        update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)

    @staticmethod
    def _edit_message(query, text: str, reply_markup=None) -> None:
        message = query.message
        if message is not None and getattr(message, "photo", None):
            query.edit_message_caption(caption=text, parse_mode="HTML", reply_markup=reply_markup)
            return
        query.edit_message_text(text=text, parse_mode="HTML", reply_markup=reply_markup)


def run_telegram_bot(runtime: SearcharrRuntime, logger: logging.Logger) -> None:
    """Run the configured Telegram bot runtime."""

    token = getattr(runtime.settings_module, "tgram_token", "")
    if not token:
        raise RuntimeError("tgram_token is required to start the Telegram bot.")
    TelegramBotService(runtime, logger).run(token)
