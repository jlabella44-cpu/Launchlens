# tests/test_agents/test_floorplan.py
import pytest


def test_dollhouse_scene_model_exists():
    from launchlens.models.dollhouse_scene import DollhouseScene
    assert hasattr(DollhouseScene, "listing_id")
    assert hasattr(DollhouseScene, "scene_json")
    assert hasattr(DollhouseScene, "room_count")
