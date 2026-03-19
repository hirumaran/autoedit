"""
One-time model pre-download script.
Run once before first use:  python -m backend.setup_models
"""
import sys
from pathlib import Path

# Allow running as: python -m backend.setup_models
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.utils.model_downloader import (
    fix_macos_ssl,
    download_florence_model,
    find_local_model,
    APP_CACHE_DIR,
)


def main() -> None:
    fix_macos_ssl()

    existing = find_local_model()
    if existing:
        print(f"✅ Florence-2 already cached at:\n   {existing}\n   Nothing to download.")
        return

    try:
        path = download_florence_model(APP_CACHE_DIR)
        print(f"\n🎉 Model ready at: {path}")
        print("   You can now run the app offline with: npm run dev")
    except Exception as exc:
        print(f"\n❌ Failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
