import spotipy


def get_user_profile(spotify: spotipy.Spotify):
    user = spotify.current_user()

    return {
        "id": user["id"],
        "display_name": user.get("display_name"),
        "email": user.get("email"),
    }

