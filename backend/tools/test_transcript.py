import json
import time
from pathlib import Path

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    RequestBlocked,
    IpBlocked,
)


# ============================================================
# CONFIGURATION
# ============================================================

PLAYLIST_URL = "https://youtube.com/playlist?list=PLbJhGqY-mq47k_WLUtzVjmarUm1EuXPj2"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

OUTPUT_FILE = DATA_DIR / "all_transcripts.json"
FAILURE_FILE = DATA_DIR / "transcript_failures.json"

# Delay between successful/failed video attempts
REQUEST_DELAY = 3


# ============================================================
# CREATE DATA DIRECTORY
# ============================================================

DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD EXISTING TRANSCRIPTS
# ============================================================

def load_existing_transcripts():

    if not OUTPUT_FILE.exists():

        print("No existing transcript file found.")
        print("Starting from scratch.\n")

        return []

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(data, list):

            print("ERROR: all_transcripts.json is not a list.")
            print("Please check the file format.")

            return []

        print(
            f"Existing transcripts found: {len(data)} videos"
        )

        return data

    except json.JSONDecodeError:

        print(
            "ERROR: all_transcripts.json contains invalid JSON."
        )

        return []


# ============================================================
# LOAD FAILURE LOG
# ============================================================

def load_failures():

    if not FAILURE_FILE.exists():

        return []

    try:

        with open(
            FAILURE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):

            return data

        return []

    except json.JSONDecodeError:

        return []


# ============================================================
# SAVE TRANSCRIPTS
# ============================================================

def save_transcripts(transcripts):

    temporary_file = OUTPUT_FILE.with_suffix(".tmp")

    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            transcripts,
            file,
            ensure_ascii=False,
            indent=2
        )

    # Replace the old file only after the new JSON
    # has been completely written.
    temporary_file.replace(OUTPUT_FILE)


# ============================================================
# SAVE FAILURE LOG
# ============================================================

def save_failures(failures):

    with open(
        FAILURE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            failures,
            file,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# GET PLAYLIST VIDEOS
# ============================================================

def get_playlist_videos():

    print("\nReading playlist...")

    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            PLAYLIST_URL,
            download=False
        )

    videos = []

    for entry in info.get("entries", []):

        if not entry:
            continue

        video_id = entry.get("id")

        title = entry.get(
            "title",
            "Unknown Title"
        )

        if not video_id:
            continue

        videos.append(
            {
                "video_id": video_id,
                "title": title,
                "youtube_url": f"https://youtu.be/{video_id}",
            }
        )

    return videos


# ============================================================
# GET TRANSCRIPT
# ============================================================

def get_transcript(video_id):

    api = YouTubeTranscriptApi()

    transcript_list = api.list(video_id)


    # --------------------------------------------------------
    # Prefer Hindi
    # --------------------------------------------------------

    try:

        transcript = transcript_list.find_transcript(
            ["hi"]
        )

        fetched = transcript.fetch()

        return (
            fetched,
            transcript.language,
            transcript.language_code,
            transcript.is_generated
        )

    except NoTranscriptFound:
        pass


    # --------------------------------------------------------
    # Fallback to English
    # --------------------------------------------------------

    try:

        transcript = transcript_list.find_transcript(
            ["en"]
        )

        fetched = transcript.fetch()

        return (
            fetched,
            transcript.language,
            transcript.language_code,
            transcript.is_generated
        )

    except NoTranscriptFound:

        pass


    # --------------------------------------------------------
    # Try any available transcript
    # --------------------------------------------------------

    try:

        transcript = next(iter(transcript_list))

        fetched = transcript.fetch()

        return (
            fetched,
            transcript.language,
            transcript.language_code,
            transcript.is_generated
        )

    except StopIteration:

        raise NoTranscriptFound(
            "No transcript available."
        )


# ============================================================
# CONVERT SEGMENTS
# ============================================================

def convert_segments(fetched_transcript):

    segments = []

    for segment in fetched_transcript:

        # youtube-transcript-api versions can expose
        # segment data slightly differently.

        try:

            start = segment.start
            duration = segment.duration
            text = segment.text

        except AttributeError:

            start = segment["start"]
            duration = segment["duration"]
            text = segment["text"]

        end = start + duration

        segments.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "text": text.strip(),
            }
        )

    return segments


# ============================================================
# TRANSCRIBE ONE VIDEO
# ============================================================

def process_video(video):

    video_id = video["video_id"]

    print("\n----------------------------------------")
    print(f"Video ID : {video_id}")
    print(f"Title    : {video['title']}")
    print("----------------------------------------")

    try:

        (
            transcript,
            language,
            language_code,
            is_generated
        ) = get_transcript(video_id)

        segments = convert_segments(transcript)

        if not segments:

            raise ValueError(
                "Transcript was found but contains no segments."
            )

        result = {
            "video_id": video_id,
            "title": video["title"],
            "youtube_url": video["youtube_url"],
            "language": language,
            "language_code": language_code,
            "is_generated": is_generated,
            "segments": segments,
        }

        return result

    except (
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    ) as e:

        print(f"Transcript unavailable: {e}")

        return None, str(e)

    except (
        RequestBlocked,
        IpBlocked,
    ) as e:

        print("\nYouTube request blocking detected.")
        print(str(e))

        return "BLOCKED", str(e)

    except Exception as e:

        print(f"Error: {e}")

        return None, str(e)


# ============================================================
# MAIN
# ============================================================

def main():

    print("========================================")
    print("RESUME-SAFE PLAYLIST TRANSCRIBER")
    print("========================================")


    # --------------------------------------------------------
    # Load existing data
    # --------------------------------------------------------

    transcripts = load_existing_transcripts()

    failures = load_failures()


    # --------------------------------------------------------
    # Existing video IDs
    # --------------------------------------------------------

    completed_ids = {
        item["video_id"]
        for item in transcripts
        if "video_id" in item
    }


    print(
        f"Completed videos already saved: "
        f"{len(completed_ids)}"
    )


    # --------------------------------------------------------
    # Get playlist
    # --------------------------------------------------------

    try:

        videos = get_playlist_videos()

    except Exception as e:

        print("\nCould not read playlist.")
        print(f"Error: {e}")

        return


    print(
        f"Total videos in playlist: {len(videos)}"
    )


    # --------------------------------------------------------
    # Determine remaining videos
    # --------------------------------------------------------

    remaining_videos = [
        video
        for video in videos
        if video["video_id"] not in completed_ids
    ]


    print(
        f"Remaining videos: "
        f"{len(remaining_videos)}"
    )


    if not remaining_videos:

        print("\nAll playlist videos are already saved.")

        return


    # --------------------------------------------------------
    # Process remaining videos
    # --------------------------------------------------------

    for index, video in enumerate(
        remaining_videos,
        start=1
    ):

        print(
            f"\nProgress: "
            f"{index}/{len(remaining_videos)}"
        )

        result = process_video(video)


        # ----------------------------------------------------
        # YouTube blocked us
        # ----------------------------------------------------

        if isinstance(result, tuple) and result[0] == "BLOCKED":

            error_message = result[1]

            print("\n========================================")
            print("YOUTUBE REQUEST BLOCKED")
            print("========================================")

            print(
                "Stopping now so we do not keep "
                "sending requests."
            )

            print(
                f"Already saved videos: "
                f"{len(transcripts)}"
            )

            print(
                "Run this script again later."
            )

            # Save current state before stopping.
            save_transcripts(transcripts)

            return


        # ----------------------------------------------------
        # Successful transcript
        # ----------------------------------------------------

        if isinstance(result, dict):

            transcripts.append(result)

            # SAVE IMMEDIATELY
            save_transcripts(transcripts)

            print(
                f"SUCCESS: "
                f"{len(result['segments'])} segments saved."
            )

            print(
                f"Total videos saved: "
                f"{len(transcripts)}"
            )

        else:

            error_message = (
                result[1]
                if isinstance(result, tuple)
                else "Unknown error"
            )

            failures.append(
                {
                    "video_id": video["video_id"],
                    "title": video["title"],
                    "youtube_url": video["youtube_url"],
                    "error": error_message,
                }
            )

            save_failures(failures)

            print("FAILED.")
            print(
                f"Failure saved to: {FAILURE_FILE}"
            )


        # ----------------------------------------------------
        # Delay before next request
        # ----------------------------------------------------

        if index < len(remaining_videos):

            print(
                f"Waiting {REQUEST_DELAY} seconds..."
            )

            time.sleep(REQUEST_DELAY)


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    total_segments = sum(
        len(video.get("segments", []))
        for video in transcripts
    )


    print("\n========================================")
    print("TRANSCRIPTION COMPLETE")
    print("========================================")

    print(
        f"Total videos saved : {len(transcripts)}"
    )

    print(
        f"Total segments     : {total_segments}"
    )

    print(
        f"Failures           : {len(failures)}"
    )

    print(
        f"\nTranscript file:"
        f"\n{OUTPUT_FILE}"
    )

    print(
        f"\nFailure file:"
        f"\n{FAILURE_FILE}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()