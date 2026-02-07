"""Terminal UI utilities for research30 skill."""

import sys
import time
import threading
import random
from typing import Optional

IS_TTY = sys.stderr.isatty()


class Colors:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


MINI_BANNER = f"""{Colors.PURPLE}{Colors.BOLD}/research30{Colors.RESET} {Colors.DIM}· searching scientific literature...{Colors.RESET}"""

BIORXIV_MESSAGES = [
    "Scanning bioRxiv preprints...",
    "Reading biology preprints...",
    "Checking bioRxiv for recent submissions...",
]

MEDRXIV_MESSAGES = [
    "Scanning medRxiv preprints...",
    "Reading medical preprints...",
    "Checking medRxiv for clinical studies...",
]

ARXIV_MESSAGES = [
    "Querying arXiv for papers...",
    "Searching arXiv submissions...",
    "Finding arXiv preprints...",
]

PUBMED_MESSAGES = [
    "Searching PubMed database...",
    "Querying NCBI for publications...",
    "Finding peer-reviewed articles...",
]

HF_MESSAGES = [
    "Checking HuggingFace Hub...",
    "Searching models and datasets...",
    "Finding ML implementations...",
]

PROCESSING_MESSAGES = [
    "Analyzing results...",
    "Scoring and ranking papers...",
    "Removing duplicates...",
    "Organizing findings...",
]

SPINNER_FRAMES = ['\u28cb', '\u28d9', '\u28f9', '\u28f8', '\u28fc', '\u28f4', '\u28e6', '\u28e7', '\u28c7', '\u28cf']


class Spinner:
    """Animated spinner for long-running operations."""

    def __init__(self, message: str = "Working", color: str = Colors.CYAN):
        self.message = message
        self.color = color
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.frame_idx = 0
        self.shown_static = False

    def _spin(self):
        while self.running:
            frame = SPINNER_FRAMES[self.frame_idx % len(SPINNER_FRAMES)]
            sys.stderr.write(f"\r{self.color}{frame}{Colors.RESET} {self.message}  ")
            sys.stderr.flush()
            self.frame_idx += 1
            time.sleep(0.08)

    def start(self):
        self.running = True
        if IS_TTY:
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()
        else:
            if not self.shown_static:
                sys.stderr.write(f"  {self.message}\n")
                sys.stderr.flush()
                self.shown_static = True

    def update(self, message: str):
        self.message = message
        if not IS_TTY:
            sys.stderr.write(f"  {message}\n")
            sys.stderr.flush()

    def stop(self, final_message: str = ""):
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.2)
        if IS_TTY:
            sys.stderr.write("\r" + " " * 80 + "\r")
        if final_message:
            sys.stderr.write(f"  {final_message}\n")
        sys.stderr.flush()


class ProgressDisplay:
    """Progress display for research phases."""

    def __init__(self, topic: str, show_banner: bool = True):
        self.topic = topic
        self.spinner: Optional[Spinner] = None
        self.start_time = time.time()

        if show_banner:
            self._show_banner()

    def _show_banner(self):
        if IS_TTY:
            sys.stderr.write(MINI_BANNER + "\n")
            sys.stderr.write(f"{Colors.DIM}Topic: {Colors.RESET}{Colors.BOLD}{self.topic}{Colors.RESET}\n\n")
        else:
            sys.stderr.write(f"/research30 - searching: {self.topic}\n")
        sys.stderr.flush()

    def start_source(self, source: str):
        messages = {
            'biorxiv': BIORXIV_MESSAGES,
            'medrxiv': MEDRXIV_MESSAGES,
            'arxiv': ARXIV_MESSAGES,
            'pubmed': PUBMED_MESSAGES,
            'huggingface': HF_MESSAGES,
        }
        colors = {
            'biorxiv': Colors.GREEN,
            'medrxiv': Colors.BLUE,
            'arxiv': Colors.CYAN,
            'pubmed': Colors.YELLOW,
            'huggingface': Colors.PURPLE,
        }
        msg = random.choice(messages.get(source, PROCESSING_MESSAGES))
        color = colors.get(source, Colors.CYAN)
        self.spinner = Spinner(f"{color}{source}{Colors.RESET} {msg}", color)
        self.spinner.start()

    def end_source(self, source: str, count: int):
        if self.spinner:
            self.spinner.stop(f"{source}: {count} results")

    def start_processing(self):
        msg = random.choice(PROCESSING_MESSAGES)
        self.spinner = Spinner(f"{Colors.PURPLE}Processing{Colors.RESET} {msg}", Colors.PURPLE)
        self.spinner.start()

    def end_processing(self):
        if self.spinner:
            self.spinner.stop()

    def show_complete(self, counts: dict):
        elapsed = time.time() - self.start_time
        parts = [f"{src}: {n}" for src, n in counts.items() if n > 0]
        summary = " | ".join(parts)

        if IS_TTY:
            sys.stderr.write(f"\n{Colors.GREEN}{Colors.BOLD}Research complete{Colors.RESET} ")
            sys.stderr.write(f"{Colors.DIM}({elapsed:.1f}s){Colors.RESET}\n")
            if summary:
                sys.stderr.write(f"  {summary}\n")
            sys.stderr.write("\n")
        else:
            sys.stderr.write(f"Research complete ({elapsed:.1f}s) - {summary}\n")
        sys.stderr.flush()

    def show_cached(self, age_hours: Optional[float] = None):
        age_str = f" ({age_hours:.1f}h old)" if age_hours is not None else ""
        sys.stderr.write(f"  Using cached results{age_str}\n\n")
        sys.stderr.flush()

    def show_error(self, message: str):
        sys.stderr.write(f"  Error: {message}\n")
        sys.stderr.flush()
