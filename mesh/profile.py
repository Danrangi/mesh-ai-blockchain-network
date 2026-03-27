"""
mesh/profile.py

Manages the local user profile for a mesh node.

On a real device (phone/laptop), one profile exists per device.
In development on a single machine, we scope the profile to the port
so we can simulate multiple users at once.
"""

import json
import os


def get_profile_path(port: int) -> str:
    """Return a profile file path scoped to the given port."""
    base = os.path.dirname(__file__)
    return os.path.join(base, f"profile_{port}.json")


def load_profile(port: int) -> dict:
    """Load saved profile for this port."""
    path = get_profile_path(port)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


def save_profile(port: int, profile: dict):
    """Save profile for this port."""
    path = get_profile_path(port)
    with open(path, "w") as f:
        json.dump(profile, f, indent=2)


def get_or_create_username(port: int) -> str:
    """
    Load saved username for this port, or prompt the user to create one.
    
    On a real phone this will be one profile per device.
    Here we scope it per port to simulate multiple users on one machine.
    """
    profile = load_profile(port)

    if profile.get("username"):
        print(f"Welcome back, {profile['username']}")
        return profile["username"]

    print("\n--- First time setup ---")
    print("This name will identify you on the mesh network.")
    print("Other users will see this name when you send messages.\n")

    while True:
        username = input("Choose a username (3-20 characters, no spaces): ").strip()

        if len(username) < 3:
            print("Username too short. Try again.")
            continue

        if len(username) > 20:
            print("Username too long. Try again.")
            continue

        if " " in username:
            print("No spaces allowed. Try again.")
            continue

        profile["username"] = username
        save_profile(port, profile)
        print(f"\nUsername saved. Welcome to the mesh, {username}.\n")
        return username
