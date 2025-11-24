from src.core.state import ApplicationState, get_state

# For backward compatibility with test structure, alias the new class
AppState = ApplicationState


def sample_tracks(count=3):
    return [
        {"number": i + 1, "title": f"Track {i+1}"}
        for i in range(count)
    ]


def test_set_tracks_and_metadata_updates_titles():
    state = AppState()
    state.set_tracks(sample_tracks(2))
    state.set_metadata({
        1: {"title": "Hello", "artist": "World", "artwork": "/tmp/a.png"}
    })
    track = state.get_selected_track()
    assert track.title == "Hello"
    assert track.artist == "World"
    assert track.artwork == "/tmp/a.png"


def test_get_index_by_number():
    state = AppState(sample_tracks(3))
    assert state.get_index_by_number(2) == 1
    assert state.get_index_by_number(99) is None


def test_advance_track_wraps():
    state = AppState(sample_tracks(2))
    state.playback.selected_track_index = 1
    track = state.advance_track(1)
    assert track.number == 1
