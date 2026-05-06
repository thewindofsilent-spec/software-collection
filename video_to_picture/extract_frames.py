#!/usr/bin/env python3
"""AVI Video to Pictures - Command Line Tool

Usage:
    python extract_frames.py <video_file> [output_dir] [options]

Options:
    --interval FRAMES   Extract every N frames (default: 30)
    --start FRAME       Start from frame N (default: 0)
    --end FRAME         End at frame N (0 = end of video)
    --format FORMAT    Image format: png, jpg, bmp (default: png)

Examples:
    python extract_frames.py video.avi
    python extract_frames.py video.avi ./output --interval 10
    python extract_frames.py video.avi ./frames --start 100 --end 500
"""

import os
import sys
import argparse
import cv2


def extract_frames(video_path, output_dir=".", interval=30, start=0, end=0, img_format="png"):
    """Extract frames from video at specified interval."""
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return False

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video: {video_path}")
        return False

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"Video: {video_path}")
    print(f"Total frames: {total_frames}")
    print(f"FPS: {fps:.2f}")
    print(f"Output: {output_dir}")
    print(f"Interval: every {interval} frames")
    print(f"Range: {start} to {end if end > 0 else 'end'}")

    cap.set(cv2.CAP_PROP_POS_FRAMES, start)

    frame_count = 0
    saved_count = 0
    current_pos = start

    ext = f".{img_format.lower()}"
    if img_format.lower() == "jpg":
        ext = ".jpg"

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if end > 0 and current_pos > end:
            break

        if current_pos % interval == 0:
            filename = f"frame_{current_pos:06d}{ext}"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)
            saved_count += 1
            print(f"  Saved: {filename}")

        frame_count += 1
        current_pos += 1

    cap.release()

    print(f"\nExtraction complete!")
    print(f"Saved {saved_count} frames")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from video files as images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("output", nargs="?", default=".", help="Output directory (default: current directory)")
    parser.add_argument("--interval", type=int, default=30, help="Extract every N frames (default: 30)")
    parser.add_argument("--start", type=int, default=0, help="Start from frame N (default: 0)")
    parser.add_argument("--end", type=int, default=0, help="End at frame N (0 = end of video)")
    parser.add_argument("--format", choices=["png", "jpg", "bmp"], default="png",
                       help="Image format (default: png)")

    args = parser.parse_args()

    extract_frames(
        args.video,
        args.output,
        args.interval,
        args.start,
        args.end,
        args.format
    )


if __name__ == "__main__":
    main()