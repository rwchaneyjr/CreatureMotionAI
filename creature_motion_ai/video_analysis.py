"""Conservative OpenCV silhouette backend for normalized motion landmarks."""
import cv2


def analyze_video(video_path, start=0, end=None, threshold=18):
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    end = total if end is None else min(end, total)
    capture.set(cv2.CAP_PROP_POS_FRAMES, start)
    previous = None
    frames = []
    for index in range(start, end):
        ok, image = capture.read()
        if not ok:
            break
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if previous is None:
            motion = gray * 0
        else:
            motion = cv2.absdiff(gray, previous)
        previous = gray
        _, mask = cv2.threshold(motion, threshold, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, None)
        points = cv2.findNonZero(mask)
        if points is None:
            frames.append({"frame": index, "landmarks": {}, "confidence": 0.0})
            continue
        x, y, w, h = cv2.boundingRect(points)
        def norm(px, py):
            return [px / max(width, 1), py / max(height, 1), 0.0]
        frames.append({
            "frame": index,
            "landmarks": {
                "motion_center": norm(x + w / 2, y + h / 2),
                "motion_top": norm(x + w / 2, y),
                "motion_bottom": norm(x + w / 2, y + h),
                "motion_left": norm(x, y + h / 2),
                "motion_right": norm(x + w, y + h / 2),
            },
            "confidence": min(1.0, (w * h) / max(width * height * 0.1, 1)),
        })
    capture.release()
    return {"format": "creature_motion_ai.motion.v1", "width": width, "height": height, "frames": frames}
