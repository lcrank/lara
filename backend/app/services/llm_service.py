"""
LLM Service - Command Parsing using Groq (Free & Ultra-fast)
Supports both text commands and Visual AI (screenshot → click)
"""

import logging
import json
from groq import AsyncGroq

logger = logging.getLogger(__name__)

# Keywords that require looking at the screen first
VISUAL_KEYWORDS = [
    "first video", "second video", "third video", "1st video", "2nd video", "3rd video",
    "play the", "click on", "click the", "open the first", "open the second",
    "scroll down", "scroll up", "scroll", "swipe down", "swipe up",
    "tap on", "press on", "select the", "choose the",
    "what's on screen", "what is on screen", "read the screen",
    "the button", "the link", "search bar", "click search",
    "play a song", "play the video", "play song", "play music",
]

class CommandPayload:
    def __init__(self, command_type="run_shell", parameters=None, confidence=1.0,
                 requires_confirmation=False, natural_language=""):
        self.command_type = command_type
        self.parameters = parameters or {}
        self.confidence = confidence
        self.requires_confirmation = requires_confirmation
        self.natural_language = natural_language

class LLMService:
    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.client = AsyncGroq(api_key=api_key)
        self.model = model
        self.vision_model = "llama-3.2-11b-vision-preview"

    def is_visual_command(self, text: str) -> bool:
        """Check if the command needs to look at the screen"""
        text_lower = text.lower()
        return any(kw in text_lower for kw in VISUAL_KEYWORDS)

    async def parse_visual_command(self, user_input: str, screenshot_base64: str) -> CommandPayload:
        """Use Groq Vision to analyze screen and determine what to click/scroll"""

        # ── Smart fallbacks for simple scroll commands (no vision needed) ──
        text_lower = user_input.lower()
        if any(x in text_lower for x in ["scroll down", "swipe down"]):
            amount = -1000 if "lot" in text_lower or "more" in text_lower else -500
            return CommandPayload(command_type="scroll", parameters={"amount": amount}, natural_language=user_input)
        if any(x in text_lower for x in ["scroll up", "swipe up"]):
            amount = 1000 if "lot" in text_lower or "more" in text_lower else 500
            return CommandPayload(command_type="scroll", parameters={"amount": amount}, natural_language=user_input)

        try:
            logger.info(f"Analyzing screen for visual command: '{user_input}'")

            prompt = f"""You are a precise laptop screen automation agent.

User wants to: "{user_input}"

Look at this screenshot VERY carefully and find the EXACT element to interact with.

CRITICAL RULES:
1. Return ONLY a JSON object. No explanation text.
2. For "play first video" / "play the first video" / "open first video": find the FIRST video thumbnail visible and return its CENTER x,y coordinates as a CLICK command. Do NOT search for anything.
3. For "play second video" / "second video": find the SECOND video thumbnail and click its center.
4. Clicking a YouTube video thumbnail = click the thumbnail image itself (the big picture), not the title text.
5. The y coordinate of the first YouTube result thumbnail is typically between 100-300 pixels from top.
6. NEVER return a run_shell command with a YouTube search URL for these visual commands.

JSON format to return:
{{
  "command_type": "click",
  "parameters": {{"x": <pixel_x>, "y": <pixel_y>, "button": "left"}},
  "confidence": 0.9,
  "description": "clicking on [what you see]"
}}

For scrolling only:
{{
  "command_type": "scroll",
  "parameters": {{"amount": -500}},
  "confidence": 0.9,
  "description": "scrolling down"
}}"""

            response = await self.client.chat.completions.create(
                model=self.vision_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{screenshot_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }],
                temperature=0.0,
                max_tokens=200,
            )

            raw = response.choices[0].message.content.strip()
            logger.info(f"Vision AI raw response: {raw[:300]}")

            start = raw.find("{")
            end = raw.rfind("}") + 1
            parsed = json.loads(raw[start:end])

            # Safety guard: if Vision AI returned a run_shell (search), override it
            if parsed.get("command_type") == "run_shell" and "play" in user_input.lower():
                logger.warning("Vision AI returned run_shell for a 'play' command — overriding with click at estimated position")
                # Estimate: first YouTube result thumbnail is roughly at (385, 215) for 1920x1080
                return CommandPayload(
                    command_type="click",
                    parameters={"x": 385, "y": 215, "button": "left"},
                    confidence=0.7,
                    natural_language=user_input
                )

            cmd = CommandPayload(
                command_type=parsed.get("command_type", "click"),
                parameters=parsed.get("parameters", {}),
                confidence=parsed.get("confidence", 0.9),
                natural_language=user_input
            )
            desc = parsed.get("description", "")
            logger.info(f"Vision AI → [{cmd.command_type}]: {desc} | params: {cmd.parameters}")
            return cmd

        except Exception as e:
            logger.error(f"Vision command error: {str(e)}", exc_info=e)
            if "play" in user_input.lower() and ("first" in user_input.lower() or "1" in user_input.lower()):
                return CommandPayload(command_type="click", parameters={"x": 385, "y": 215, "button": "left"}, natural_language=user_input)
            if "second" in user_input.lower() or "2nd" in user_input.lower():
                return CommandPayload(command_type="click", parameters={"x": 385, "y": 490, "button": "left"}, natural_language=user_input)
            return CommandPayload(command_type="scroll", parameters={"amount": -500}, natural_language=user_input)

    async def parse_command(self, user_input: str) -> CommandPayload:
        """Parse natural language into a laptop command"""
        try:
            logger.debug(f"Parsing command: '{user_input}'")

            prompt = f"""You are an advanced Windows 11 laptop automation agent. Convert the user's natural language command into an action.

User command: "{user_input}"

IMPORTANT RULES:
1. Respond ONLY with a valid JSON object, nothing else.
2. Choose command_type based on the action needed.

COMMAND TYPES:

A) command_type: "browser_action"
   - For YouTube: Use this for "play [song]" or "watch [video]". It is much more accurate than shell scripts.
   - Parameters: {{"action": "play_youtube", "query": "SONG_NAME"}}

B) command_type: "run_shell"
   - For opening apps, files, folders, system settings
   - Parameters: {{"command": "POWERSHELL_SCRIPT"}}
   - Use Start-Process for GUI apps (non-blocking)
   - For web searches (other than YouTube): Start-Process "brave" -ArgumentList "https://www.google.com/search?q=QUERY"
   - For folders: Start-Process "explorer" -ArgumentList "C:\\Users\\$env:USERNAME\\Downloads"

B) command_type: "key_press"
   - For keyboard shortcuts and special key presses
   - Parameters: {{"keys": ["key1", "key2"]}} for combos, or {{"keys": ["key"]}} for single keys
   - "volume up" → {{"keys": ["volumeup"]}}
   - "volume down" → {{"keys": ["volumedown"]}}
   - "mute" → {{"keys": ["volumemute"]}}
   - "play" or "pause" → {{"keys": ["playpause"]}}
   - "next song" → {{"keys": ["nexttrack"]}}
   - "previous song" → {{"keys": ["prevtrack"]}}
   - "screenshot" / "snip" → {{"keys": ["win", "shift", "s"]}}
   - "minimize all" / "show desktop" → {{"keys": ["win", "d"]}}
   - "task manager" → {{"keys": ["ctrl", "shift", "esc"]}}
   - "lock screen" → {{"keys": ["win", "l"]}}
   - "fullscreen" → {{"keys": ["f11"]}}
   - "close window" → {{"keys": ["alt", "f4"]}}
   - "copy" → {{"keys": ["ctrl", "c"]}}
   - "paste" → {{"keys": ["ctrl", "v"]}}

C) command_type: "screenshot"
   - When user says "take a screenshot", "capture screen"
   - Parameters: {{}}

D) command_type: "type_text"
   - When user wants to type something at cursor
   - Parameters: {{"text": "the text to type"}}

E) command_type: "scroll"
   - Scroll the screen
   - Parameters: {{"amount": -500}} for down, {{"amount": 500}} for up

Respond with this exact JSON format:
{{
  "command_type": "CHOSEN_TYPE",
  "parameters": {{}},
  "confidence": 0.95,
  "requires_confirmation": false
}}"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
            )

            raw = response.choices[0].message.content.strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            parsed = json.loads(raw[start:end])

            cmd = CommandPayload(
                command_type=parsed.get("command_type", "run_shell"),
                parameters=parsed.get("parameters", {"command": user_input}),
                confidence=parsed.get("confidence", 0.95),
                requires_confirmation=parsed.get("requires_confirmation", False),
                natural_language=user_input
            )
            logger.info(f"Groq → [{cmd.command_type}]: {str(cmd.parameters)[:100]}")
            return cmd

        except Exception as e:
            logger.error(f"Error parsing command: {str(e)}", exc_info=e)
            return CommandPayload(
                command_type="run_shell",
                parameters={"command": user_input},
                confidence=0.5,
                natural_language=user_input
            )
