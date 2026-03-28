# tests/test_agents/test_video.py
import pytest


def test_video_asset_model_exists():
    from launchlens.models.video_asset import VideoAsset
    assert hasattr(VideoAsset, "listing_id")
    assert hasattr(VideoAsset, "video_type")
    assert hasattr(VideoAsset, "chapters")
    assert hasattr(VideoAsset, "social_cuts")
    assert hasattr(VideoAsset, "status")
