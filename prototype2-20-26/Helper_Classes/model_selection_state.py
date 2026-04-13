"""Process-wide singleton that remembers the last model the user picked.

Any window that shows a NavBar reads this on startup so the dropdown
always restores the previous selection without needing to pass the path
through every window constructor.
"""


class ModelSelectionState:
    def __init__(self):
        self._path: str = ""

    def get(self) -> str:
        return self._path

    def set(self, path: str) -> None:
        self._path = path


instance = ModelSelectionState()


def get_model_selection_state() -> ModelSelectionState:
    return instance
