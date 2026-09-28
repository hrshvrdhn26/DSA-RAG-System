import json
from pathlib import Path


INPUT_FILE = Path("../data/all_transcripts_clean.json")
OUTPUT_FILE = Path("../data/transcript_chunks.json")

TARGET_CHUNK_SIZE = 600
OVERLAP_SIZE = 100


def load_transcript(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def create_chunks(data):
    chunks = []

    for video_data in data:

        segments = video_data["segments"]

        current_segments = []
        current_length = 0
        chunk_number = 1

        for segment in segments:

            text = segment["text"].strip()

            if not text:
                continue

            current_segments.append(segment)
            current_length += len(text)

            if current_length >= TARGET_CHUNK_SIZE:

                chunk = build_chunk(
                    current_segments,
                    video_data,
                    chunk_number
                )

                chunks.append(chunk)

                chunk_number += 1

                overlap_segments = []
                overlap_length = 0

                for previous_segment in reversed(current_segments):

                    previous_text = previous_segment["text"].strip()

                    if overlap_length + len(previous_text) > OVERLAP_SIZE:
                        break

                    overlap_segments.insert(0, previous_segment)
                    overlap_length += len(previous_text)

                current_segments = overlap_segments
                current_length = overlap_length

        # Add remaining segments as final chunk
        if current_segments:

            chunk = build_chunk(
                current_segments,
                video_data,
                chunk_number
            )

            chunks.append(chunk)

    return chunks


def build_chunk(segments, video_data, chunk_number):

    chunk_text = " ".join(
        segment["text"].strip()
        for segment in segments
    )

    start_time = segments[0]["start"]
    end_time = segments[-1]["end"]

    return {
        "chunk_id": f"{video_data['video_id']}_{chunk_number:03d}",
        "text": chunk_text,
        "start": start_time,
        "end": end_time,
        "video_id": video_data["video_id"],
        "video_title": video_data["title"],
        "youtube_url": video_data["youtube_url"]
    }


def save_chunks(chunks, output_file):

    with open(output_file, "w", encoding="utf-8") as file:

        json.dump(
            chunks,
            file,
            ensure_ascii=False,
            indent=2
        )


def main():

    print("Loading cleaned transcripts...")

    data = load_transcript(INPUT_FILE)

    print(f"Total cleaned videos: {len(data)}")

    # --------------------------------------------------
    # Load previously created chunks
    # --------------------------------------------------

    if OUTPUT_FILE.exists():

        existing_chunks = load_transcript(OUTPUT_FILE)

    else:

        existing_chunks = []

    # --------------------------------------------------
    # Find videos that already have chunks
    # --------------------------------------------------

    existing_video_ids = {
        chunk["video_id"]
        for chunk in existing_chunks
        if "video_id" in chunk
    }

    print(f"Videos already chunked: {len(existing_video_ids)}")

    # --------------------------------------------------
    # Only process newly cleaned videos
    # --------------------------------------------------

    videos_to_chunk = [
        video
        for video in data
        if video.get("video_id") not in existing_video_ids
    ]

    print(f"New videos to chunk: {len(videos_to_chunk)}")

    if not videos_to_chunk:

        print("Nothing new to chunk.")

        print(f"Total existing chunks: {len(existing_chunks)}")

        return

    # --------------------------------------------------
    # Create chunks only for new videos
    # --------------------------------------------------

    new_chunks = create_chunks(videos_to_chunk)

    print(f"New chunks created: {len(new_chunks)}")

    # --------------------------------------------------
    # Append new chunks to existing chunks
    # --------------------------------------------------

    all_chunks = existing_chunks + new_chunks

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    save_chunks(all_chunks, OUTPUT_FILE)

    print("\nChunking completed.")

    print(f"Previously existing chunks: {len(existing_chunks)}")
    print(f"New chunks: {len(new_chunks)}")
    print(f"Total chunks: {len(all_chunks)}")

    print(f"\nChunks saved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()