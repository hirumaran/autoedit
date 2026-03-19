from pathlib import Path

a = Analysis(
    ['backend/main.py'],
    # ...existing code...
    datas=[
        # Pre-download model first:
        #   huggingface-cli download microsoft/Florence-2-base \
        #     --local-dir ~/.cache/ai_video_editor/florence2
        # Then include it:
        (str(Path.home() / '.cache/ai_video_editor/florence2'), 'models/florence2'),
    ],
    # ...existing code...
)