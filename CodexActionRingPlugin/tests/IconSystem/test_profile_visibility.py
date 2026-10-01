import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "tools/icons/check_profile_visibility.py"
SPEC = importlib.util.spec_from_file_location("profile_visibility", SCRIPT)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class ProfileVisibilityTests(unittest.TestCase):
    def test_white_default_and_override_fail_but_saved_dark_tint_passes(self):
        action = CHECK.PREFIX + "Loupedeck.CodexActionRingPlugin.Logitech.Primary.NextAttentionCommand"
        with tempfile.TemporaryDirectory() as folder:
            profile = Path(folder) / "ProfileInfo.json"
            profile.write_text(json.dumps({"layout": {"controls": [{"pressAction": action}]}}))
            self.assertEqual((1, []), CHECK.check_profile(profile))
            self.assertEqual((1, ["NextAttentionCommand"]), CHECK.check_profile(profile, CHECK.WHITE))
            icons = profile.parent / "ActionIcons"
            icons.mkdir()
            icon = icons / (action + ".ict")
            data = {"backgroundColor": 0xFFFFFFFF, "items": [{
                "itemType": "Image", "isVisible": True, "imageColor": 0xFFFFFFFF,
            }]}
            icon.write_text(json.dumps(data))
            self.assertEqual((1, ["NextAttentionCommand"]), CHECK.check_profile(profile))
            data["items"][0]["imageColor"] = 0xFF171717
            icon.write_text(json.dumps(data))
            self.assertEqual((1, []), CHECK.check_profile(profile))
            data["backgroundColor"] = 0xFF767676
            for tint in (0xFF171717, CHECK.WHITE):
                data["items"][0]["imageColor"] = tint
                icon.write_text(json.dumps(data))
                self.assertEqual((1, []), CHECK.check_profile(profile))
            data["items"][0]["isVisible"] = False
            icon.write_text(json.dumps(data))
            self.assertEqual((1, ["NextAttentionCommand"]), CHECK.check_profile(profile))
