"""
Florence-2 model manager.

Priority order:
  1. FLORENCE_LOCAL_PATH env var (manual placement)
  2. Local HF cache (local_files_only=True) — works 100% offline
  3. hf-mirror.com
  4. huggingface.co
  5. Print exact manual download instructions and raise
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

MODEL_ID = os.environ.get("FLORENCE_MODEL_ID", "microsoft/Florence-2-base")
_MIRRORS = [
    os.environ.get("HF_ENDPOINT", "https://hf-mirror.com"),
    "https://huggingface.co",
]


# ── Public API ────────────────────────────────────────────────────────────────

def ensure_florence_model() -> Tuple[object, object]:
    """
    Return (processor, model) for Florence-2. Tries every source in order.
    Raises RuntimeError with manual download instructions if all fail.
    """
    from rich.console import Console
    console = Console()

    console.print(f"\n[bold cyan]🔍 Looking for Florence-2 model:[/bold cyan] {MODEL_ID}")

    # 1 ── Manual local path
    local_path = _local_path()
    if local_path:
        console.print(f"[green]📂 FLORENCE_LOCAL_PATH set → {local_path}[/green]")
        return _load_from_path(str(local_path))

    # 2 ── Already in HF cache (offline-safe)
    result = _try_local_cache(console)
    if result:
        return result

    # 3 ── Network download (mirrors in order)
    if os.environ.get("HF_HUB_OFFLINE", "0") == "1":
        console.print("[yellow]⚠️  HF_HUB_OFFLINE=1 — skipping network attempts.[/yellow]")
    else:
        result = _try_network_download(console)
        if result:
            return result

    # 4 ── All failed → instructions
    _print_manual_instructions(console)
    raise RuntimeError(
        "Florence-2 model unavailable. Follow the manual download instructions above."
    )


def load_florence_model(device: str = "cpu") -> Tuple[object, object]:
    """
    High-level loader called by video_analyzer.py.
    Returns (processor, model) with model moved to `device`.
    """
    processor, model = ensure_florence_model()
    try:
        model = model.to(device)
        logger.info(f"✅ Florence-2 loaded on {device}")
    except Exception as exc:
        logger.warning(f"Could not move model to {device}: {exc} — staying on CPU")
    return processor, model


# ── Private helpers ───────────────────────────────────────────────────────────

def _local_path() -> Optional[Path]:
    raw = os.environ.get("FLORENCE_LOCAL_PATH", "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser().resolve()
    if p.is_dir():
        return p
    logger.error(f"FLORENCE_LOCAL_PATH set but directory not found: {p}")
    return None


def _hf_cache_dir() -> Path:
    """Default HF hub cache directory."""
    base = os.environ.get("HF_HOME", os.environ.get("HUGGINGFACE_HUB_CACHE", ""))
    if base:
        return Path(base).expanduser()
    return Path.home() / ".cache" / "huggingface" / "hub"


def _try_local_cache(console) -> Optional[Tuple]:
    """Attempt to load from local HF cache without network."""
    try:
        from huggingface_hub import snapshot_download
        console.print("[dim]  Checking local HF cache (no network)…[/dim]")
        path = snapshot_download(
            MODEL_ID,
            local_files_only=True,
            ignore_patterns=["*.msgpack", "flax_model*"],
        )
        console.print(f"[green]✅ Found in local cache → {path}[/green]")
        return _load_from_path(path)
    except Exception as exc:
        console.print(f"[dim]  Not in local cache ({_short(exc)})[/dim]")
        return None


def _try_network_download(console) -> Optional[Tuple]:
    """Try each mirror in order."""
    from huggingface_hub import snapshot_download

    for mirror in _MIRRORS:
        console.print(f"[cyan]  🌐 Trying mirror: {mirror}[/cyan]")
        try:
            os.environ["HF_ENDPOINT"] = mirror
            path = snapshot_download(
                MODEL_ID,
                local_files_only=False,
                ignore_patterns=["*.msgpack", "flax_model*"],
            )
            console.print(f"[green]✅ Downloaded from {mirror} → {path}[/green]")
            return _load_from_path(path)
        except Exception as exc:
            console.print(f"[yellow]  ✗ {mirror} failed: {_short(exc)}[/yellow]")

    return None


def _load_from_path(model_path: str) -> Tuple:
    """Load processor + model from a local directory path."""
    from transformers import AutoProcessor, AutoModelForCausalLM

    logger.info(f"Loading Florence-2 from: {model_path}")
    processor = AutoProcessor.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
    )
    return processor, model


def _short(exc: Exception) -> str:
    """Short one-line exception summary."""
    return str(exc).split("\n")[0][:120]


def _print_manual_instructions(console) -> None:
    cache_dir = _hf_cache_dir()
    # HF hub stores models as models--org--name/snapshots/<sha>/
    org, name = MODEL_ID.split("/")
    target = cache_dir / f"models--{org}--{name}"

    console.print("\n" + "=" * 70)
    console.print("[bold red]❌ Florence-2 could not be downloaded automatically.[/bold red]")
    console.print("[bold yellow]📋 MANUAL DOWNLOAD INSTRUCTIONS[/bold yellow]\n")
    console.print("Option A — Download via browser on a machine WITH internet:")
    console.print(f"  1. Open: [link]https://huggingface.co/{MODEL_ID}/tree/main[/link]")
    console.print("  2. Download ALL files (config.json, model files, tokenizer, etc.)")
    console.print(f"  3. Place them in a folder, e.g. ~/Downloads/{name}/")
    console.print("  4. Set the env var before starting:")
    console.print(f"     [bold]export FLORENCE_LOCAL_PATH=~/Downloads/{name}[/bold]")
    console.print("     [bold]./run.sh start[/bold]\n")
    console.print("Option B — Use huggingface-cli on a machine WITH internet:")
    console.print(f"  [bold]huggingface-cli download {MODEL_ID} --local-dir ~/Downloads/{name}[/bold]")
    console.print("  Then copy the folder to this machine and set FLORENCE_LOCAL_PATH.\n")
    console.print("Option C — Git LFS (requires git-lfs installed):")
    console.print(f"  [bold]git clone https://huggingface.co/{MODEL_ID} ~/Downloads/{name}[/bold]\n")
    console.print(f"Expected cache location if you use Option B on this machine:")
    console.print(f"  [bold]{target}[/bold]")
    console.print("=" * 70 + "\n")
    console.print(
        "[dim]💡 Tip: The app works fine WITHOUT Florence-2 — "
        "video analysis features will be disabled until the model is available.[/dim]"
    )
