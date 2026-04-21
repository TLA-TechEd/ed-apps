import threading

try:
    import requests
    import ui
except ImportError as exc:
    raise SystemExit(
        "This app is designed to run in Pythonista on iOS (requires ui and requests modules)."
    ) from exc


APP_TITLE = "AI Choose Now (Pythonista)"
DEFAULT_HOST = "192.168.1.100"
DEFAULT_PORT = "11434"
DEFAULT_MODEL = "llama3.1:8b"
TIMEOUT_SECONDS = 120
MAX_TURNS = 14


class AdventureState:
    def __init__(self):
        self.scenario = ""
        self.turns = []  # [{"action": str, "story": str, "choices": [str, str, str]}]

    def reset(self, scenario_text):
        self.scenario = scenario_text.strip()
        self.turns = []

    def add_turn(self, action, story, choices):
        self.turns.append({"action": action, "story": story, "choices": choices})
        if len(self.turns) > MAX_TURNS:
            self.turns = self.turns[-MAX_TURNS:]

    def build_context(self):
        chunks = [f"Scenario Essentials:\n{self.scenario}"]
        for idx, turn in enumerate(self.turns, 1):
            chunks.append(f"Turn {idx} - Player action: {turn['action']}")
            chunks.append(f"Turn {idx} - Story result: {turn['story']}")
        return "\n\n".join(chunks)


class AdventureView(ui.View):
    def __init__(self):
        super().__init__(name=APP_TITLE, bg_color="#111111")
        self.state = AdventureState()
        self._build_ui()

    def _build_ui(self):
        pad = 8

        self.server_field = ui.TextField(
            frame=(pad, 8, 150, 32),
            placeholder="Ollama host",
            text=DEFAULT_HOST,
            text_color="white",
            bg_color="#222",
            border_style="rounded_rect",
            clear_button_mode="while_editing",
        )
        self.add_subview(self.server_field)

        self.port_field = ui.TextField(
            frame=(166, 8, 80, 32),
            placeholder="Port",
            text=DEFAULT_PORT,
            text_color="white",
            bg_color="#222",
            border_style="rounded_rect",
        )
        self.add_subview(self.port_field)

        self.model_field = ui.TextField(
            frame=(252, 8, 220, 32),
            placeholder="Model",
            text=DEFAULT_MODEL,
            text_color="white",
            bg_color="#222",
            border_style="rounded_rect",
            clear_button_mode="while_editing",
        )
        self.add_subview(self.model_field)

        self.new_button = ui.Button(frame=(478, 8, 90, 32), title="New Game")
        self.new_button.background_color = "#6a4b16"
        self.new_button.tint_color = "white"
        self.new_button.corner_radius = 6
        self.new_button.action = self.start_new_game
        self.add_subview(self.new_button)

        self.status_label = ui.Label(frame=(pad, 44, 560, 22), text_color="#cccccc", font=("<system>", 12))
        self.status_label.text = "Set host/model, enter a scenario, then tap New Game."
        self.add_subview(self.status_label)

        self.scenario_view = ui.TextView(frame=(pad, 70, 560, 90), bg_color="#1c1c1c", text_color="white")
        self.scenario_view.font = ("Menlo", 13)
        self.scenario_view.text = "A drifting sky-city powered by ancient weather engines."
        self.add_subview(self.scenario_view)

        self.story_view = ui.TextView(frame=(pad, 168, 560, 460), bg_color="#171717", text_color="#f4e8c1")
        self.story_view.font = ("Georgia", 16)
        self.story_view.editable = False
        self.add_subview(self.story_view)

        self.choice_buttons = []
        for i in range(3):
            btn = ui.Button(frame=(pad, 636 + i * 42, 560, 36), title=f"Choice {i+1}")
            btn.background_color = "#2b2b2b"
            btn.tint_color = "white"
            btn.corner_radius = 7
            btn.action = self.pick_choice
            btn.enabled = False
            self.choice_buttons.append(btn)
            self.add_subview(btn)

        self.custom_action = ui.TextField(
            frame=(pad, 768, 430, 36),
            placeholder="Or type your own action...",
            text_color="white",
            bg_color="#222",
            border_style="rounded_rect",
            clear_button_mode="while_editing",
        )
        self.add_subview(self.custom_action)

        self.send_button = ui.Button(frame=(446, 768, 122, 36), title="Send Action")
        self.send_button.background_color = "#255f29"
        self.send_button.tint_color = "white"
        self.send_button.corner_radius = 7
        self.send_button.action = self.send_custom_action
        self.send_button.enabled = False
        self.add_subview(self.send_button)

    @property
    def ollama_url(self):
        host = self.server_field.text.strip() or DEFAULT_HOST
        port = self.port_field.text.strip() or DEFAULT_PORT
        return f"http://{host}:{port}"

    def set_busy(self, busy):
        self.new_button.enabled = not busy
        self.send_button.enabled = not busy and bool(self.state.turns)
        for b in self.choice_buttons:
            b.enabled = (not busy) and bool(self.state.turns)

    def start_new_game(self, sender):
        scenario = self.scenario_view.text.strip()
        if not scenario:
            self.set_status("Please add scenario essentials before starting.")
            return

        self.state.reset(scenario)
        self.story_view.text = ""
        self.custom_action.text = ""
        self.set_status("Creating opening scene...")
        self._request_turn("Begin the adventure with an exciting opening scene.")

    def send_custom_action(self, sender):
        action = self.custom_action.text.strip()
        if not action:
            self.set_status("Type an action first.")
            return
        self.custom_action.text = ""
        self._request_turn(action)

    def pick_choice(self, sender):
        action = sender.title
        self._request_turn(action)

    def _request_turn(self, action):
        self.set_busy(True)
        self.set_status("Thinking...")

        def worker():
            try:
                story, choices = generate_next_turn(
                    ollama_url=self.ollama_url,
                    model=self.model_field.text.strip() or DEFAULT_MODEL,
                    context=self.state.build_context(),
                    action=action,
                )
                self.state.add_turn(action, story, choices)
                ui.delay(lambda: self._update_ui_after_turn(story, choices), 0)
            except Exception as exc:  # noqa: BLE001
                ui.delay(lambda: self._handle_error(exc), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _update_ui_after_turn(self, story, choices):
        block = f"\n\n▶ {self.state.turns[-1]['action']}\n\n{story.strip()}\n"
        self.story_view.text += block
        self.story_view.content_offset = (0, max(0, self.story_view.content_size[1] - self.story_view.height))

        for idx, btn in enumerate(self.choice_buttons):
            btn.title = choices[idx]
            btn.enabled = True
        self.send_button.enabled = True
        self.new_button.enabled = True
        self.set_status("Choose an option or type a custom action.")

    def _handle_error(self, exc):
        self.new_button.enabled = True
        for b in self.choice_buttons:
            b.enabled = bool(self.state.turns)
        self.send_button.enabled = bool(self.state.turns)
        self.set_status(f"Error: {exc}")

    def set_status(self, message):
        self.status_label.text = message


PROMPT_TEMPLATE = """
You are the narrator for a cinematic choose-your-own-adventure.
Write exactly two short paragraphs that continue the story based on the player's action.
Then provide exactly three distinct choices.

Return in this exact format:
STORY:
<paragraph 1>

<paragraph 2>

CHOICES:
1. <choice one>
2. <choice two>
3. <choice three>

Constraints:
- Keep tone consistent with the scenario.
- Choices must be actionable and different.
- Never include extra sections.

Scenario and context:
{context}

Player action:
{action}
""".strip()


def generate_next_turn(ollama_url, model, context, action):
    payload = {
        "model": model,
        "prompt": PROMPT_TEMPLATE.format(context=context, action=action),
        "stream": False,
        "options": {"temperature": 0.8},
    }

    resp = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=TIMEOUT_SECONDS)
    if resp.status_code != 200:
        raise RuntimeError(f"Ollama error {resp.status_code}: {resp.text[:200]}")

    body = resp.json()
    raw = body.get("response", "").strip()
    story, choices = parse_story_and_choices(raw)
    return story, choices


def parse_story_and_choices(text):
    upper = text.upper()
    story_marker = upper.find("STORY:")
    choices_marker = upper.find("CHOICES:")

    if story_marker >= 0 and choices_marker > story_marker:
        story = text[story_marker + len("STORY:"):choices_marker].strip()
        tail = text[choices_marker + len("CHOICES:"):].strip()
    else:
        parts = text.split("\n")
        story = "\n".join(parts[:2]).strip() or text.strip()
        tail = text

    choices = []
    for line in tail.splitlines():
        line = line.strip().lstrip("-*")
        if not line:
            continue
        if line[:2] in {"1.", "2.", "3.", "1)", "2)", "3)"}:
            line = line[2:].strip()
        if line and len(choices) < 3:
            choices.append(line)

    while len(choices) < 3:
        choices.append(f"Do something unexpected ({len(choices)+1})")

    return story, choices[:3]


def main():
    view = AdventureView()
    view.present(style="sheet", orientations=["portrait"], hide_title_bar=False)


if __name__ == "__main__":
    main()
