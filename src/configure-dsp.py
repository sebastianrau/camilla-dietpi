#!/usr/bin/python3
"""Interactive ALSA selection; writes the initial RAM DSP config and hardware settings."""
import os
from pathlib import Path
import pwd
import re
import shlex
import shutil
import subprocess

import yaml


def candidates(text):
    result = {'Capture': [], 'Playback': []}
    section = None
    current = {}
    for line in text.splitlines() + ['Playback:']:
        heading = re.match(r'^(Capture|Playback):', line)
        alt = re.search(r'Altset\s+\d+', line)
        if heading or alt:
            if section and all(k in current for k in ('format', 'channels', 'rates')):
                result[section].append(current)
            current = {}
            if heading:
                section = heading.group(1)
        match = re.search(r'Format:\s*(\S+)', line)
        if match:
            current['format'] = match.group(1)
        match = re.search(r'Channels:\s*(\d+)', line)
        if match:
            current['channels'] = int(match.group(1))
        match = re.search(r'Rates:\s*(.*)', line)
        if match:
            current['rates'] = match.group(1)
    return result


def choose(label, options):
    if not options:
        raise RuntimeError(f'No {label} choices found; inspect /proc/asound/cardN/stream0')
    print(f'\n{label}:')
    for index, item in enumerate(options):
        print(f'  {index}: {item}')
    while True:
        answer = input('Choose index: ').strip()
        if answer.isdecimal() and int(answer) < len(options):
            return options[int(answer)]
        print('Enter one of the listed indices.')


def pcm_settings(label, options):
    supported = {'S16_LE': 'S16_LE', 'S24_LE': 'S24_4_LE',
                 'S24_3LE': 'S24_3_LE', 'S32_LE': 'S32_LE'}
    options = [x for x in options if x['channels'] >= 8 and x['format'] in supported]
    item = choose(label + ' alternate interface (must support 96000 Hz)', options)
    if input('Do the displayed rates include/support 96000 Hz? Type yes: ').strip() != 'yes':
        raise RuntimeError('96 kHz support has not been confirmed')
    return item['channels'], supported[item['format']]


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run as root')
    runtime = Path('/run/camilladsp')
    if (runtime / 'state.yml').exists():
        raise RuntimeError('Settings already exist. Do not overwrite a tuned configuration.')
    cards = []
    for line in Path('/proc/asound/cards').read_text().splitlines():
        match = re.match(r'\s*(\d+)\s+\[([^]]+)\]', line)
        if match:
            cards.append({'number': int(match.group(1)), 'id': match.group(2).strip(), 'label': line.strip()})
    card = choose('Select the RME Digiface USB card', cards)
    card_id = card['id']
    stream_path = Path(f"/proc/asound/card{card['number']}/stream0")
    if not stream_path.is_file():
        raise RuntimeError('Selected card has no USB streaming descriptor. Rerun and choose the Digiface index (0 on the observed M93), not HDMI.')
    stream = stream_path.read_text()
    print('\nFull USB streaming descriptor:\n' + stream)
    choices = candidates(stream)
    cin, fin = pcm_settings('Capture', choices['Capture'])
    cout, fout = pcm_settings('Playback', choices['Playback'])

    controls = subprocess.check_output(['amixer', '-c', card_id, 'controls'], text=True)
    print('\nALSA controls:\n' + controls)
    numid = input('numid of the clock-source selector: ').strip()
    if not numid.isdecimal():
        raise RuntimeError('Clock numid must be a number from the list')
    control = 'numid=' + numid
    detail = subprocess.check_output(['amixer', '-c', card_id, 'cget', control], text=True)
    print(detail)
    enum = re.findall(r"Item #(\d+) '([^']+)'", detail)
    if not enum:
        raise RuntimeError('Selected control is not an enumerated clock selector')
    index = input('Enum index for Optical Input 1 (read the list above): ').strip()
    if index not in [x[0] for x in enum]:
        raise RuntimeError('Invalid clock enum index')
    print('Selected:', dict(enum)[index])
    if input('Confirm this is Optical Input 1: type yes: ').strip() != 'yes':
        raise RuntimeError('Clock selection not confirmed')
    subprocess.run(['amixer', '-c', card_id, 'cset', control, index], check=True)

    root = runtime
    for directory in (root, root / 'configs', root / 'coeffs'):
        directory.mkdir(parents=True, exist_ok=True)
    device = f'hw:CARD={card_id},DEV=0'
    config = {
        'title': 'M93 ADAT 8ch 96k',
        'description': 'Initial pass-through; unused outputs silent',
        'devices': {
            'samplerate': 96000, 'chunksize': 512, 'silence_timeout': 0,
            'enable_rate_adjust': False, 'resampler': None,
            'capture': {'type': 'Alsa', 'channels': cin, 'device': device, 'format': fin},
            'playback': {'type': 'Alsa', 'channels': cout, 'device': device, 'format': fout},
        },
        'mixers': {'adat8': {
            'channels': {'in': cin, 'out': cout},
            'mapping': [{'dest': n, 'sources': [{'channel': n, 'gain': 0.0, 'inverted': False}]} for n in range(8)],
        }},
        'pipeline': [{'type': 'Mixer', 'name': 'adat8'}],
    }
    (root / 'configs/startup.yml').write_text(yaml.safe_dump(config, sort_keys=False))
    state = {'config_path': str(root / 'configs/startup.yml'),
             'mute': [False] * 5, 'volume': [-30.0, 0.0, 0.0, 0.0, 0.0]}
    (root / 'state.yml').write_text(yaml.safe_dump(state, sort_keys=False))
    account = pwd.getpwnam('dsp')
    for path in [root, *root.rglob('*')]:
        os.chown(path, account.pw_uid, account.pw_gid)
        path.chmod(0o750 if path.is_dir() else 0o640)
    settings = {'CARD_ID': card_id, 'CLOCK_CONTROL': control,
                'CLOCK_VALUE': index, 'STARTUP_GAIN_DB': '-30'}
    Path('/etc/default/camilladsp-hardware').write_text(
        ''.join(f'{k}={shlex.quote(v)}\n' for k, v in settings.items()))
    subprocess.run(['/opt/camilla/bin/camilladsp', '-c', str(root / 'configs/startup.yml')], check=True)
    print('\nInitial files created and schema checked. Test actual audio next; no settings have been saved to disk yet.')


if __name__ == '__main__':
    main()
