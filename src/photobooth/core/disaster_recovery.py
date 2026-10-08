import os
import re


def natural_sort_key(name: str):
    """
    Helper function to sort alphanumeric strings naturally.
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', name)]


def has_pending_session(current_path: str) -> bool:
    """
    Method which verifies if the last session left some photos in the current folder.
    :param current_path: the path of the current folder
    :return: True if some photos are left, False otherwise
    """

    return len(os.listdir(current_path)) != 0


def pending_photos(current_path: str) -> list:
    """
    Method which returns the photos left in the current folder from the last session,
    sorted with a natural order.
    :param current_path: the path of the current folder
    :return: list of photo paths
    """

    photos = os.listdir(current_path)
    photos.sort(key=natural_sort_key)
    return [os.path.join(current_path, photo) for photo in photos]