"""
core/vision.py — Screen awareness module.
Takes screenshots and sends them to a local vision model (moondream via Ollama)
for understanding what's on screen.
"""

import os
import base64
import tempfile
from datetime import datetime
from config import VISION_ENABLED, VISION_MODEL
from logger import setup_logging

logger = setup_logging()

# ── Availability Checks ─────────────────────────────────────
VISION_AVAILABLE = False

try:
    from PIL import ImageGrab
    VISION_AVAILABLE = True
except ImportError:
    logger.warning("PIL not available — vision/screenshot features disabled")


def is_available():
    """Check if vision features are available."""
    return VISION_ENABLED and VISION_AVAILABLE


def take_screenshot(save_path=None):
    """
    Capture the screen and return the file path.

    Args:
        save_path: Optional path to save the screenshot. If None,
                   saves to ~/Pictures/Screenshots/.

    Returns:
        File path to the saved screenshot, or None on failure.
    """
    if not VISION_AVAILABLE:
        logger.warning("Screenshot unavailable: PIL not installed")
        return None

    try:
        if not save_path:
            screenshots_dir = os.path.join(
                os.path.expanduser("~"), "Pictures", "Screenshots"
            )
            os.makedirs(screenshots_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(screenshots_dir, f"maya_{timestamp}.png")

        screenshot = ImageGrab.grab()
        screenshot.save(save_path)
        logger.info(f"Screenshot saved: {save_path}")
        return save_path

    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return None


def describe_screen(prompt=None):
    """
    Take a screenshot and ask the vision model to describe it.

    Args:
        prompt: Optional custom prompt. Defaults to general description.

    Returns:
        String description of what's on screen, or error message.
    """
    if not is_available():
        return "Screen awareness isn't available right now."

    # Take screenshot
    screenshot_path = take_screenshot()
    if not screenshot_path:
        return "I couldn't capture the screen."

    # Default prompt
    if not prompt:
        prompt = (
            "Describe what you see on this computer screen. "
            "Be concise and focus on the main content visible."
        )

    try:
        return _query_vision_model(screenshot_path, prompt)
    finally:
        # Clean up temporary screenshot
        try:
            if screenshot_path and "maya_" in screenshot_path:
                os.unlink(screenshot_path)
        except OSError:
            pass


def analyze_screen(question):
    """
    Answer a specific question about what's on screen.

    Args:
        question: The user's question about the screen content.

    Returns:
        Answer string from the vision model.
    """
    if not is_available():
        return "Screen awareness isn't available right now."

    screenshot_path = take_screenshot()
    if not screenshot_path:
        return "I couldn't capture the screen."

    prompt = (
        f"Look at this screenshot of a computer screen and answer this question: {question}\n"
        "Be concise and direct in your answer."
    )

    try:
        return _query_vision_model(screenshot_path, prompt)
    finally:
        try:
            if screenshot_path and "maya_" in screenshot_path:
                os.unlink(screenshot_path)
        except OSError:
            pass


def _query_vision_model(image_path, prompt):
    """
    Send an image to the Ollama vision model and get a response.

    Uses the Ollama API directly (not OpenAI-compatible) since
    vision requires the ollama-native format with base64 images.
    """
    try:
        import requests

        # Read and encode image
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        # Ollama native API for vision
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": VISION_MODEL,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
            },
            timeout=60,
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "I couldn't understand what's on screen.")
        else:
            logger.error(f"Vision API error: {response.status_code} — {response.text}")
            return "The vision model didn't respond properly."

    except requests.exceptions.ConnectionError:
        return "Ollama isn't running. Start it with 'ollama serve' to enable screen awareness."
    except Exception as e:
        logger.error(f"Vision query failed: {e}")
        return f"Screen analysis failed: {e}"
