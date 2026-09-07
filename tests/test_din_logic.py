"""Baseline tests only: passing them does not establish clinical correctness."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import core

class FakeStreamlit:
    def __init__(self):
        self.session_state = {}

class DinLogicBaselineTests(unittest.TestCase):
    """Freeze observed implementation behavior, not DIN protocol validity."""
    def test_digit_scoring_requires_three_ordered_matches(self):
        self.assertEqual(core.check_2_of_3(["1", "2", "3"], ["1", "2", "3"]), (True, 3))
        self.assertEqual(core.check_2_of_3(["1", "2", "3"], ["1", "3", "2"]), (False, 1))
        self.assertEqual(core.check_2_of_3(["1", "2", "3"], ["1", "2"]), (False, 0))
    def test_adaptive_snr_step_and_bounds(self):
        self.assertEqual(core.update_snr(0, True), -2)
        self.assertEqual(core.update_snr(0, False), 2)
        self.assertEqual(core.update_snr(core.MIN_SNR, True), core.MIN_SNR)
        self.assertEqual(core.update_snr(core.MAX_SNR, False), core.MAX_SNR)
    def test_reversal_is_a_strict_local_extremum_from_trial_four(self):
        self.assertEqual(core.get_reversal_points([0, -2, -4, -6, -4, -2]), [{"trial": 4, "snr": -6}])
    def test_plateau_is_not_a_reversal(self):
        self.assertEqual(core.get_reversal_points([0, -2, -4, -6, -6, -4]), [])
    def test_reversal_endpoints_are_not_counted(self):
        self.assertEqual(core.get_reversal_points([4, 0, 0, 0]), [])
        self.assertEqual(core.get_reversal_points([0] * 22 + [4]), [])
    def test_final_srt_is_mean_of_observed_reversals(self):
        history = [0, -2, -4, -6, -4, -6, -8]
        self.assertEqual(core.get_reversal_points(history), [{"trial": 4, "snr": -6}, {"trial": 5, "snr": -4}])
        self.assertEqual(core.calculate_final_snr(history), -5.0)
        self.assertIsNone(core.calculate_final_snr([0, -2, -4, -6]))
    def test_session_initialization_preserves_existing_values(self):
        streamlit = FakeStreamlit()
        streamlit.session_state["voice"] = "Giọng Miền Nam"
        core.init_session_state(streamlit)
        self.assertEqual(streamlit.session_state["voice"], "Giọng Miền Nam")
        self.assertEqual(streamlit.session_state["page"], 1)
        self.assertEqual(streamlit.session_state["trial_index"], 1)
        self.assertEqual(streamlit.session_state["current_snr"], core.START_SNR)
        self.assertEqual(streamlit.session_state["results"], [])
    def test_reset_only_resets_test_state(self):
        streamlit = FakeStreamlit()
        core.init_session_state(streamlit)
        streamlit.session_state.update(gender="Nam", health_conditions=["Không có bệnh lý kèm theo"], headphone_confirmed=True, trial_index=10, current_snr=-8, snr_history=[0, -2], current_digits=["1", "2", "3"], typed_digits="123", results=[{"trial": 1}], final_snr=-2, trial_audio_path="temporary.wav", trial1_started=True, used_digit_files=["one.wav"])
        core.reset_test_state(streamlit)
        self.assertEqual(streamlit.session_state["trial_index"], 1)
        self.assertEqual(streamlit.session_state["current_snr"], core.START_SNR)
        self.assertEqual(streamlit.session_state["snr_history"], [])
        self.assertEqual(streamlit.session_state["current_digits"], [])
        self.assertEqual(streamlit.session_state["results"], [])
        self.assertIsNone(streamlit.session_state["final_snr"])
        self.assertEqual(streamlit.session_state["gender"], "Nam")
        self.assertEqual(streamlit.session_state["health_conditions"], ["Không có bệnh lý kèm theo"])
        self.assertTrue(streamlit.session_state["headphone_confirmed"])
