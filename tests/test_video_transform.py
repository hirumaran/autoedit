from unittest.mock import patch

from backend.video_processor import VideoProcessor


def _mock_probe_result():
    return {
        "format": {"duration": "10.0"},
        "streams": [{"codec_type": "video", "width": 1920, "height": 1080}],
    }


@patch("backend.video_processor.ffmpeg.probe", return_value=_mock_probe_result())
@patch("backend.video_processor.subprocess.run")
def test_transform_video_defaults_to_fit_preserving_full_frame(mock_run, _mock_probe):
    processor = VideoProcessor("/tmp/input.mp4")

    processor.transform_video(
        "/tmp/output.mp4",
        aspect_ratio="9:16",
        resolution="1080x1920",
    )

    cmd = mock_run.call_args[0][0]
    vf = cmd[cmd.index("-vf") + 1]

    assert "force_original_aspect_ratio=decrease" in vf
    assert "pad=1080:1920:(ow-iw)/2:(oh-ih)/2" in vf
    assert "crop=if(gt(iw/ih" not in vf


@patch("backend.video_processor.ffmpeg.probe", return_value=_mock_probe_result())
@patch("backend.video_processor.subprocess.run")
def test_transform_video_crop_mode_keeps_center_crop_available(mock_run, _mock_probe):
    processor = VideoProcessor("/tmp/input.mp4")

    processor.transform_video(
        "/tmp/output.mp4",
        aspect_ratio="9:16",
        resolution="1080x1920",
        resize_mode="crop",
    )

    cmd = mock_run.call_args[0][0]
    vf = cmd[cmd.index("-vf") + 1]

    assert "crop=if(gt(iw/ih" in vf
    assert "scale=1080:1920" in vf
