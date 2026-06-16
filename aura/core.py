"""Core download logic for Aura Frame Downloader."""

import json
import logging
import os
import shutil
import time
from typing import Callable, Dict, List, Optional, Tuple

import requests

from .exceptions import (
    DownloadCancelledError,
    DownloadError,
    LoginError,
    NoAssetsError,
)

LOGGER = logging.getLogger(__name__)

# API URLs
LOGIN_URL = "https://api.pushd.com/v5/login.json"
FRAME_URL_TEMPLATE = "https://api.pushd.com/v5/frames/{frame_id}/assets.json?side_load_users=false"
IMAGE_URL_TEMPLATE = "https://imgproxy.pushd.com/{user_id}/{file_name}"

# Live Photos are saved as their still image; the motion clip goes in this
# subdirectory of the download folder.
LIVE_PHOTO_VIDEO_DIRNAME = "live_photo_videos"


def create_session(email: str, password: str) -> requests.Session:
    """
    Create an authenticated session with the Aura API.

    Args:
        email: User's email address
        password: User's password

    Returns:
        Authenticated requests.Session object

    Raises:
        LoginError: If authentication fails
    """
    login_payload = {
        "identifier_for_vendor": "does-not-matter",
        "client_device_id": "does-not-matter",
        "app_identifier": "com.pushd.Framelord",
        "locale": "en",
        "user": {
            "email": email,
            "password": password
        }
    }

    session = requests.Session()
    response = session.post(LOGIN_URL, json=login_payload)

    if response.status_code != 200:
        raise LoginError("Login failed: Check your credentials")

    json_data = response.json()
    session.headers.update({
        'X-User-Id': json_data['result']['current_user']['id'],
        'X-Token-Auth': json_data['result']['current_user']['auth_token']
    })

    LOGGER.info("Login successful")
    return session


def get_frame_assets(session: requests.Session, frame_id: str) -> List[Dict]:
    """
    Fetch assets from a frame.

    Args:
        session: Authenticated requests.Session
        frame_id: ID of the frame to fetch assets from

    Returns:
        List of asset dictionaries

    Raises:
        NoAssetsError: If no assets are found or API returns error
    """
    frame_url = FRAME_URL_TEMPLATE.format(frame_id=frame_id)
    response = session.get(frame_url)
    json_data = json.loads(response.text)

    if "assets" not in json_data:
        LOGGER.error("No images returned from this Aura Frame. API responded with:")
        LOGGER.error(json_data)
        raise NoAssetsError("No images found in this Aura Frame")

    return json_data["assets"]


def download_photos_from_aura(
    email: str,
    password: str,
    frame_id: str,
    file_path: str,
    organize_by_year: bool = False,
    count_only: bool = False,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Tuple[int, int, int]:
    """
    Download photos from an Aura frame.

    Args:
        email: User's email address
        password: User's password
        frame_id: ID of the frame to download from
        file_path: Directory to save photos to
        organize_by_year: If True, organize photos into year subdirectories
        count_only: If True, return count without downloading
        progress_callback: Optional callback(current, total, filename) for progress updates
        cancel_check: Optional callback() that returns True if download should be cancelled

    Returns:
        Tuple of (downloaded_count, skipped_count, total_count)

    Raises:
        LoginError: If authentication fails
        NoAssetsError: If no assets are found
        DownloadCancelledError: If download is cancelled via cancel_check
        DownloadError: If a critical download error occurs
    """
    # Create authenticated session
    session = create_session(email, password)

    # Get frame assets
    assets = get_frame_assets(session, frame_id)
    total_count = len(assets)
    LOGGER.info("Found %s photos", total_count)

    if count_only:
        return (0, 0, total_count)

    # Ensure output directory exists
    if not os.path.isdir(file_path):
        LOGGER.info("Creating new images directory: %s", file_path)
        os.makedirs(file_path)

    LOGGER.info("Starting download process")

    downloaded_count = 0
    skipped_count = 0
    current = 0

    for item in assets:
        current += 1

        # Check for cancellation
        if cancel_check and cancel_check():
            LOGGER.info("Download cancelled by user")
            raise DownloadCancelledError("Download cancelled by user")

        try:
            # Make a unique filename base using timestamp + id.
            # Clean the timestamp to be Windows-friendly.
            clean_time = item['taken_at'].replace(':', '-')
            base_name = clean_time + "_" + item['id']

            is_live = bool(item.get('is_live'))
            video_url = item.get('video_url')

            # Where the primary file lands (optionally bucketed by year).
            if organize_by_year:
                dest_dir = os.path.join(file_path, clean_time[:4])
            else:
                dest_dir = file_path

            # Pick the primary file for this asset:
            #   - real videos: the signed MP4
            #   - live photos: the still image (the motion clip is saved separately below)
            #   - plain photos: the still image
            if video_url and not is_live:
                primary_url = video_url
                primary_name = base_name + '.mp4'
            else:
                primary_url = IMAGE_URL_TEMPLATE.format(
                    user_id=item['user_id'],
                    file_name=item['file_name']
                )
                primary_name = base_name + os.path.splitext(item['file_name'])[1]

            # (url, destination) jobs for this asset; a live photo has two.
            jobs = [(primary_url, os.path.join(dest_dir, primary_name))]
            if is_live and video_url:
                live_dir = os.path.join(file_path, LIVE_PHOTO_VIDEO_DIRNAME)
                jobs.append((video_url, os.path.join(live_dir, base_name + '.mp4')))

            # Update progress
            if progress_callback:
                progress_callback(current, total_count, primary_name)

            for url, file_to_write in jobs:
                os.makedirs(os.path.dirname(file_to_write), exist_ok=True)
                display_name = os.path.basename(file_to_write)

                # Check if file exists and skip it if so
                if os.path.isfile(file_to_write):
                    LOGGER.info("%i: Skipping %s, already downloaded", current, display_name)
                    skipped_count += 1
                    continue

                # Get the file from the url
                LOGGER.info("%i: Downloading %s", current, display_name)
                response = requests.get(url, stream=True, timeout=90)

                # Write to a file
                with open(file_to_write, 'wb') as out_file:
                    shutil.copyfileobj(response.raw, out_file)
                del response

                downloaded_count += 1

                # Wait a bit to avoid throttling
                time.sleep(2)

        except DownloadCancelledError:
            raise
        except Exception as e:
            LOGGER.error("Item %i failed to download: %s", current, str(e))
            time.sleep(10)

    return (downloaded_count, skipped_count, total_count)
