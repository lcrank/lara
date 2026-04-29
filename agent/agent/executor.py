"""
Command Executor - Safe command execution on laptop
Handles different command types with appropriate safety measures
"""

import logging
import subprocess
import time
import platform
import os
from typing import NamedTuple

logger = logging.getLogger(__name__)

class ExecutionResult(NamedTuple):
    success: bool
    details: str = ""
    error_message: str = ""
    execution_time_ms: float = 0.0
    response_data: dict = {}

class CommandExecutor:
    """
    Safely executes commands received from backend
    
    Supported commands:
    - open_app: Launch application
    - type_text: Type text at cursor
    - screenshot: Capture screen
    - search_web: Search on web
    - click_position: Click at coordinates
    - key_press: Press keyboard keys
    - close_app: Close application
    """
    
    def __init__(self):
        self.system_platform = platform.system()  # Windows, Darwin, Linux
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        logger.info(f"Executor initialized on {self.system_platform}")
    
    async def _get_page(self):
        """Get or create a persistent browser page using real Brave profile"""
        from playwright.async_api import async_playwright
        
        if not self.playwright:
            self.playwright = await async_playwright().start()
            
        if not self.browser or not self.page or self.page.is_closed():
            # Real Brave paths
            brave_exe = os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")
            user_data = os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data")
            
            if os.path.exists(brave_exe) and os.path.exists(user_data):
                logger.info(f"Launching persistent Brave at: {brave_exe}")
                # We use launch_persistent_context to use your real login/cookies
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=user_data,
                    executable_path=brave_exe,
                    headless=False,
                    args=["--remote-debugging-port=9222", "--no-first-run"],
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Brave/1.65.114",
                    ignore_default_args=["--enable-automation"]
                )
                self.browser = self.context.browser
                self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            else:
                logger.warning("Brave or User Data not found, falling back to default Chromium")
                self.browser = await self.playwright.chromium.launch(headless=False)
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
            
        return self.page
    
    async def execute(self, command: dict) -> ExecutionResult:
        """
        Execute a command
        
        Args:
            command: Command payload with type and parameters
        
        Returns:
            ExecutionResult with success/failure information
        """
        
        try:
            command_type = command.get("command_type")
            parameters = command.get("parameters", {})
            
            logger.info(f"Executing: {command_type}")
            
            start_time = time.time()
            
            if command_type == "open_app":
                result = self._open_app(parameters)
            
            elif command_type == "type_text":
                result = self._type_text(parameters)
            
            elif command_type == "screenshot":
                result = self._take_screenshot(parameters)
            
            elif command_type == "search_web":
                result = self._search_web(parameters)
            
            elif command_type in ("click_position", "click"):
                result = self._click_position(parameters)
            
            elif command_type == "scroll":
                result = self._scroll(parameters)
            
            elif command_type == "browser_action":
                result = await self._browser_action(parameters)
            
            elif command_type == "key_press":
                result = self._key_press(parameters)
            
            elif command_type == "close_app":
                result = self._close_app(parameters)
            
            elif command_type == "run_shell":
                result = self._run_shell(parameters)
            
            else:
                result = ExecutionResult(
                    success=False,
                    error_message=f"Unknown command: {command_type}"
                )
            
            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000  # milliseconds
            
            # Return result with timing
            return ExecutionResult(
                success=result.success,
                details=result.details,
                error_message=result.error_message,
                execution_time_ms=execution_time,
                response_data=result.response_data
            )
        
        except Exception as e:
            logger.error(f"Execution error: {str(e)}", exc_info=e)
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
    
    def _open_app(self, params: dict) -> ExecutionResult:
        """Open an application"""
        
        try:
            app_name = params.get("app", "").lower()
            
            if self.system_platform == "Windows":
                # Map app names to executables
                app_map = {
                    "notepad": "notepad.exe",
                    "calculator": "calc.exe",
                    "chrome": "chrome.exe",
                    "firefox": "firefox.exe",
                    "opera": "opera.exe",
                    "vlc": "vlc.exe",
                    "spotify": "spotify.exe",
                    "vscode": "code.exe",
                }
                
                executable = app_map.get(app_name)
                if not executable:
                    return ExecutionResult(
                        success=False,
                        error_message=f"Unknown app: {app_name}"
                    )
                
                # Launch the application
                subprocess.Popen(executable)
                
                return ExecutionResult(
                    success=True,
                    details=f"Opened {app_name}"
                )
            
            elif self.system_platform == "Darwin":  # macOS
                subprocess.run(["open", "-a", app_name], check=True)
                return ExecutionResult(
                    success=True,
                    details=f"Opened {app_name}"
                )
            
            else:  # Linux
                subprocess.Popen([app_name])
                return ExecutionResult(
                    success=True,
                    details=f"Opened {app_name}"
                )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
    
    def _type_text(self, params: dict) -> ExecutionResult:
        """Type text at current cursor position"""
        
        try:
            import pyautogui
            
            text = params.get("text", "")
            delay_ms = params.get("delay_ms", 50) / 1000.0  # Convert to seconds
            
            # Type the text with delay between characters
            for char in text:
                pyautogui.typewrite(char, interval=delay_ms)
            
            logger.info(f"Typed {len(text)} characters")
            
            return ExecutionResult(
                success=True,
                details=f"Typed {len(text)} characters"
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
    
    def _take_screenshot(self, params: dict) -> ExecutionResult:
        """Take a screenshot of the screen"""
        
        try:
            import pyautogui
            from PIL import Image
            import io
            import base64
            
            # Take screenshot
            screenshot = pyautogui.screenshot()
            
            # Convert to bytes
            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG")
            screenshot_bytes = buffer.getvalue()
            
            # Encode to base64 for transmission
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
            
            logger.info(f"Screenshot taken: {screenshot.size}")
            
            return ExecutionResult(
                success=True,
                details="Screenshot captured",
                response_data={
                    "image_base64": screenshot_b64,
                    "width": screenshot.size[0],
                    "height": screenshot.size[1]
                }
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
    
    def _search_web(self, params: dict) -> ExecutionResult:
        """Open web search in default browser"""
        
        try:
            import webbrowser
            
            query = params.get("query", "")
            engine = params.get("engine", "google").lower()
            
            # Build search URL
            if engine == "google":
                url = f"https://www.google.com/search?q={query}"
            elif engine == "duckduckgo":
                url = f"https://duckduckgo.com/?q={query}"
            else:
                url = f"https://www.google.com/search?q={query}"
            
            webbrowser.open(url)
            
            return ExecutionResult(
                success=True,
                details=f"Opened search for: {query}"
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
    
    def _scroll(self, params: dict) -> ExecutionResult:
        """Scroll the screen up or down"""
        try:
            import pyautogui
            amount = params.get("amount", -300)
            pyautogui.scroll(amount)
            direction = "down" if amount < 0 else "up"
            logger.info(f"Scrolled {direction} by {abs(amount)}")
            return ExecutionResult(success=True, details=f"Scrolled {direction}")
        except Exception as e:
            return ExecutionResult(success=False, error_message=str(e))

    async def _browser_action(self, params: dict) -> ExecutionResult:
        """Execute DOM-based browser automation using persistent Brave/Chromium"""
        try:
            action = params.get("action", "play_youtube")
            query = params.get("query", "")
            
            page = await self._get_page()
            
            if action == "play_youtube":
                url = f"https://www.youtube.com/results?search_query={query}"
                logger.info(f"Navigating to: {url}")
                await page.goto(url)
                
                # Wait for results to load
                await page.wait_for_selector("#video-title", timeout=10000)
                
                # Click the first one
                logger.info("Clicking first video title...")
                await page.click("#video-title", force=True)
                
                # Bring to front
                await page.bring_to_front()
                
                details = f"Started playing YouTube video for: {query}"
            else:
                details = "Browser action completed"
            
            return ExecutionResult(success=True, details=details)
                
        except Exception as e:
            logger.error(f"Browser action error: {str(e)}")
            return ExecutionResult(success=False, error_message=str(e))

    def _click_position(self, params: dict) -> ExecutionResult:
        """Click mouse at specific coordinates"""
        
        try:
            import pyautogui
            
            x = params.get("x", 0)
            y = params.get("y", 0)
            
            # Click at position
            pyautogui.click(x, y)
            
            logger.info(f"Clicked at ({x}, {y})")
            
            return ExecutionResult(
                success=True,
                details=f"Clicked at ({x}, {y})"
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
    
    def _key_press(self, params: dict) -> ExecutionResult:
        """Press keyboard keys including media keys via PowerShell"""
        try:
            keys = params.get("keys", [])
            if not keys:
                return ExecutionResult(success=False, error_message="No keys specified")

            # Media / special keys handled via PowerShell SendKeys or wscript
            media_key_map = {
                "volumeup":    "(New-Object -com WScript.Shell).SendKeys([char]175)",
                "volumedown":  "(New-Object -com WScript.Shell).SendKeys([char]174)",
                "volumemute":  "(New-Object -com WScript.Shell).SendKeys([char]173)",
                "playpause":   "(New-Object -com WScript.Shell).SendKeys([char]179)",
                "nexttrack":   "(New-Object -com WScript.Shell).SendKeys([char]176)",
                "prevtrack":   "(New-Object -com WScript.Shell).SendKeys([char]177)",
            }

            if len(keys) == 1 and keys[0].lower() in media_key_map:
                key = keys[0].lower()
                ps_cmd = media_key_map[key]
                subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
                logger.info(f"Media key pressed: {key}")
                return ExecutionResult(success=True, details=f"Pressed: {key}")

            # Regular keys via pyautogui
            import pyautogui
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)

            logger.info(f"Pressed keys: {'+'.join(keys)}")
            return ExecutionResult(success=True, details=f"Pressed: {'+'.join(keys)}")

        except Exception as e:
            return ExecutionResult(success=False, error_message=str(e))
    
    def _close_app(self, params: dict) -> ExecutionResult:
        """Close an application"""
        
        try:
            app_name = params.get("app", "").lower()
            
            if self.system_platform == "Windows":
                # Use taskkill to close the application
                process_name = app_name
                if not process_name.endswith(".exe"):
                    process_name += ".exe"
                
                subprocess.run(
                    ["taskkill", "/IM", process_name, "/F"],
                    capture_output=True
                )
                
                return ExecutionResult(
                    success=True,
                    details=f"Closed {app_name}"
                )
            
            else:
                # macOS/Linux
                subprocess.run(["pkill", "-f", app_name])
                
                return ExecutionResult(
                    success=True,
                    details=f"Closed {app_name}"
                )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
            
    def _run_shell(self, params: dict) -> ExecutionResult:
        """Execute a raw shell command"""
        try:
            command_str = params.get("command", "")
            logger.info(f"Running shell command: {command_str}")
            
            result = subprocess.run(
                ["powershell", "-Command", command_str], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if not output:
                    output = "Command executed successfully (no output)"
                return ExecutionResult(success=True, details=output[:500])
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return ExecutionResult(success=False, error_message=f"Shell error: {error[:500]}")
                
        except Exception as e:
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
