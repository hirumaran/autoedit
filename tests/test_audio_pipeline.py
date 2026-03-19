import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from backend.services.music_agent import MusicAgent, MusicTrack
from backend.services.viral_editor import ViralEditor

@pytest.fixture
def mock_music_agent():
    agent = MagicMock(spec=MusicAgent)
    agent.download_track.return_value = Path("/tmp/mock_audio.mp3")
    return agent

@pytest.fixture
def viral_editor(mock_music_agent):
    return ViralEditor(mock_music_agent, Path("/tmp/output"))

def test_apply_viral_edit_success(viral_editor, mock_music_agent):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        
        result = viral_editor.apply_viral_edit(
            video_path="/tmp/video.mp4",
            audio_track_id="123",
            transcript_segments=[{"start": 10, "end": 20}],
            volume_level=0.5
        )
        
        assert result["success"] is True
        assert "output_path" in result
        
        # Verify FFmpeg call
        args = mock_run.call_args[0][0]
        # Check volume filter logic — format: if(between(...), duck_vol, bg_vol)
        assert "volume='if(between(t,10,20), 0.15, 0.5)':eval=frame" in args[args.index("-filter_complex") + 1]

def test_apply_viral_edit_preview(viral_editor):
    with patch("subprocess.run") as mock_run:
        result = viral_editor.apply_viral_edit(
            video_path="/tmp/video.mp4",
            audio_track_id="123",
            is_preview=True
        )
        
        args = mock_run.call_args[0][0]
        assert "-t" in args
        assert "15" in args # Preview duration
        assert result["is_preview"] is True

