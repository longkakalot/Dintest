"""Streamlit regression for observed submission/history behavior only."""
from __future__ import annotations
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

class AppFlowBaselineTests(unittest.TestCase):
    def test_trial_submission_records_history_and_advances_snr(self):
        entrypoint = Path(__file__).resolve().parents[1] / "app" / "app.py"
        app = AppTest.from_file(entrypoint, default_timeout=20).run()
        app.session_state["page"] = 9
        app.session_state["trial1_started"] = True
        app.session_state["current_digits"] = ["1", "2", "3"]
        app.session_state["trial_audio_path"] = None
        app.run()
        for digit in ["1", "2", "3"]:
            next(button for button in app.button if button.label == digit).click().run()
        next(button for button in app.button if button.label == "Kế tiếp").click().run()
        self.assertEqual(app.session_state["trial_index"], 2)
        self.assertEqual(app.session_state["snr_history"], [0])
        self.assertEqual(app.session_state["current_snr"], -2)
        self.assertEqual(app.session_state["results"], [{"trial": 1, "target": "123", "answer": "123", "correct_count": 3, "passed": True, "snr": 0}])
        audio_path = app.session_state["trial_audio_path"]
        if audio_path and Path(audio_path).exists():
            Path(audio_path).unlink()



