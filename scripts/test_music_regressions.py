"""Regression tests for dropped intro transients and skipped grid beats."""
import unittest
from compose_show import Composer
from fseq_writer import FseqWriter


class OnsetRegression(unittest.TestCase):
    def fixture(self):
        c=Composer.__new__(Composer)
        c.n=200
        c.channels=48
        c.w=FseqWriter(48,200)
        c.beats=[40]
        c.onset_frames=[40]
        c.onset_strength=[.95]
        c.music_start=0
        c.music_end=200
        c.intro_end=100
        c.build_end=140
        c.climax_end=180
        c.pan_bass=[0.]*200
        return c

    def test_intro_strong_transient_emits_light(self):
        c=self.fixture()
        c.rendered_beats=set()
        c._onset_layer()
        self.assertTrue(any(c.w.frames[40*48:42*48]))

    def test_skipped_grid_beat_does_not_suppress_onset(self):
        c=self.fixture()
        c.intro_end=0
        c.rendered_beats=set()
        c._onset_layer()
        self.assertTrue(any(c.w.frames[40*48:43*48]))

    def test_rendered_beat_suppresses_duplicate(self):
        c=self.fixture()
        c.rendered_beats={40}
        c._onset_layer()
        self.assertFalse(any(c.w.frames))


if __name__=='__main__':
    unittest.main()
