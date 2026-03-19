from __future__ import annotations

from pathlib import Path
import json

from typing_app.models import Passage


def load_passages() -> list[Passage]:
    data_path = Path(__file__).resolve().parent / "data" / "passages.json"
    with data_path.open("r", encoding="utf-8") as file:
        passages_data = json.load(file)

    return [
        Passage(
            id=passage["id"],
            title=passage["title"],
            text=passage["text"],
        )
        for passage in passages_data
    ]


def load_fixed_passage() -> Passage:
    return load_passages()[0]
