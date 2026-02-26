import requests

def test_process():
    res = requests.post('http://localhost:8000/api/process', json={
        "video_id": "testvideo123",
        "user_prompt": "test",
        "platform": "tiktok",
        "format": "short",
        "aspect_ratio": "9:16",
        "resolution": "1080x1920"
    })
    print("Process Status:", res.status_code)
    print("Process Body:", res.text)

def test_render():
    res = requests.post('http://localhost:8000/api/render', json={
        "video_id": "testvideo123",
        "platform": "tiktok",
        "format": "short",
        "aspect_ratio": "9:16",
        "resolution": "1080x1920",
        "rotation": 90,
        "flip_horizontal": True
    })
    print("Render Status:", res.status_code)
    print("Render Body:", res.text)

if __name__ == "__main__":
    test_process()
    test_render()
