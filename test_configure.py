import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('configure', Path(__file__).with_name('configure-dsp.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class DescriptorTests(unittest.TestCase):
    def test_alternate_interfaces_and_different_channel_counts(self):
        text = '''Playback:
  Interface 1
    Altset 1
    Format: S24_3LE
    Channels: 34
    Rates: 44100, 48000
    Altset 2
    Format: S24_3LE
    Channels: 18
    Rates: 88200, 96000
Capture:
  Interface 2
    Altset 1
    Format: S32_LE
    Channels: 16
    Rates: 88200, 96000
'''
        parsed = m.candidates(text)
        self.assertEqual([x['channels'] for x in parsed['Playback']], [34, 18])
        self.assertEqual(parsed['Capture'][0]['channels'], 16)
        self.assertEqual(parsed['Capture'][0]['rates'], '88200, 96000')

    def test_padded_and_packed_24bit_map_to_correct_camilla_names(self):
        for alsa, expected in [('S24_LE', 'S24_4_LE'), ('S24_3LE', 'S24_3_LE')]:
            selected = {'channels': 16, 'format': alsa, 'rates': '96000'}
            with patch.object(m, 'choose', return_value=selected), patch('builtins.input', return_value='yes'):
                self.assertEqual(m.pcm_settings('Capture', [selected]), (16, expected))


if __name__ == '__main__':
    unittest.main()
