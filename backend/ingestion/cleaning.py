import json
import re
import unicodedata
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "all_transcripts.json"
OUTPUT_FILE = DATA_DIR / "all_transcripts_clean.json"


def clean_text(text):
    """
    Clean transcript text without changing its meaning.
    """

    if not text:
        return ""

    # Unicode normalization
    text = unicodedata.normalize("NFC", text)

    # Remove zero-width and invisible characters
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)

    # Normalize newlines and tabs
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = text.replace("\t", " ")

    # Normalize multiple spaces
    text = re.sub(r"\s+", " ", text)

    # Remove spaces before punctuation
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)

    # Final strip
    text = text.strip()

    return text


def load_json(file_path):
    if not file_path.exists():
        return []

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def clean_video(video):
    """
    Clean one video transcript.
    """

    cleaned_segments = []

    for segment in video.get("segments", []):

        cleaned_text = clean_text(segment.get("text", ""))

        if not cleaned_text:
            continue

        cleaned_segments.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": cleaned_text
        })

    return {
        "video_id": video["video_id"],
        "title": video["title"],
        "youtube_url": video["youtube_url"],
        "segments": cleaned_segments
    }


def main():

    print("Loading transcripts...")

    raw_transcripts = load_json(INPUT_FILE)

    if not raw_transcripts:
        print("No transcripts found.")
        return

    existing_cleaned = load_json(OUTPUT_FILE)

    # Video IDs that are already cleaned
    cleaned_video_ids = {
        video["video_id"]
        for video in existing_cleaned
        if "video_id" in video
    }

    print(f"Total raw videos: {len(raw_transcripts)}")
    print(f"Already cleaned videos: {len(cleaned_video_ids)}")

    # Only process videos that are not already cleaned
    videos_to_clean = [
        video
        for video in raw_transcripts
        if video.get("video_id") not in cleaned_video_ids
    ]

    print(f"New videos to clean: {len(videos_to_clean)}")

    if not videos_to_clean:
        print("Nothing new to clean.")
        return

    new_cleaned_videos = []

    for index, video in enumerate(videos_to_clean, start=1):

        video_id = video.get("video_id")
        title = video.get("title", "Unknown Title")

        print(
            f"\nCleaning {index}/{len(videos_to_clean)}: "
            f"{title} [{video_id}]"
        )

        cleaned_video = clean_video(video)

        new_cleaned_videos.append(cleaned_video)

        print(
            f"Segments: "
            f"{len(video.get('segments', []))} -> "
            f"{len(cleaned_video['segments'])}"
        )

    # Append newly cleaned videos to existing cleaned data
    existing_cleaned.extend(new_cleaned_videos)

    # Save safely
    temp_file = OUTPUT_FILE.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(
            existing_cleaned,
            file,
            ensure_ascii=False,
            indent=2
        )

    temp_file.replace(OUTPUT_FILE)

    print("\nCleaning completed.")

    print(f"Previously cleaned: {len(cleaned_video_ids)}")
    print(f"Newly cleaned: {len(new_cleaned_videos)}")
    print(f"Total cleaned videos: {len(existing_cleaned)}")

    print(f"\nSaved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()