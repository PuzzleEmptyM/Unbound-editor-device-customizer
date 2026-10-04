"""Exercise precision motion using a stub emitter; never send native input."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
import types

WORK = pathlib.Path(__file__).resolve().parent
SOURCE = WORK.parent / 'src' / 'precision_input.py'
spec = importlib.util.spec_from_file_location('precision_input_test', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

output = []


def emit(flags, dx=0, dy=0, data=0):
    output.append((flags, dx, dy, data))


click = object()
left_button = object()
inputs = types.SimpleNamespace(emit=emit, move=None, scroll=None,
                              click=click, left_button=left_button)
sys.modules['speed_editor_desktop_input'] = inputs
config = {'layers': {'default': {'context_switching': {}}}}
original = copy.deepcopy(config)
clock = [10.0]
module._clock = lambda: clock[0]
module.install(lambda: config)
report = {'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'native_output': False, 'checks': []}



def write_report():
    pass


def check(name, ok):
    report['checks'].append({'name': name, 'pass': bool(ok)})
    write_report()
    assert ok, name


def turn(axis='x', direction=1, elapsed=.02, amount=40):
    clock[0] += elapsed
    inputs.move(axis, direction, amount)


check('defaults are fine pointer and slow wheel steps',
      module.settings(config) ==
      {'pointer_step': 2, 'scroll_step': 8, 'acceleration': True})
check('reading preferences does not change saved data', config == original)
turn()
check('first movement uses two pixels despite old per-layer distance',
      output[-1] == (1, 2, 0, 0))
for _ in range(4):
    turn(direction=1000000)
check('fast turn boost grows gently instead of using raw event magnitude',
      output[-1] == (1, 3, 0, 0))
for _ in range(25):
    turn()
check('default fast movement is capped at four pixels',
      output[-1] == (1, 4, 0, 0) and max(v[1] for v in output) == 4)
turn(elapsed=.1)
check('slower turning reduces acceleration', output[-1] == (1, 3, 0, 0))
turn(direction=-1)
check('reverse direction immediately resets speed', output[-1] == (1, -2, 0, 0))
turn(axis='y', direction=-1)
check('axis change immediately resets speed', output[-1] == (1, 0, -2, 0))
for _ in range(12):
    turn(axis='y', elapsed=.01)
turn(axis='y', elapsed=.2)
check('pause resets acceleration', output[-1] == (1, 0, 2, 0))
count = len(output)
for direction in (0, None, '', float('nan'), float('inf')):
    inputs.move('x', direction)
    inputs.scroll(direction)
inputs.move('z', 1)
check('zero and invalid events cause no output', len(output) == count)
inputs.scroll(1, 120)
inputs.scroll(-1, 120)
check('wheel uses small global step and preserves both directions',
      output[-2:] == [(0x800, 0, 0, -8), (0x800, 0, 0, 8)])
for _ in range(12):
    turn()
module.reset()
turn()
check('releasing a mouse mode discards its speed history',
      output[-1] == (1, 2, 0, 0))
for _ in range(12):
    turn()
inputs.scroll(1)
turn()
check('switching through wheel mode resets pointer speed',
      output[-1] == (1, 2, 0, 0))
config['layers']['default']['context_switching']['precision_input'] = {
    'pointer_step': 1, 'scroll_step': 3, 'acceleration': False}
for _ in range(20):
    turn(axis='y', elapsed=.01)
check('live global pointer preference applies without reinstalling',
      output[-1] == (1, 0, 1, 0))
check('disabled acceleration stays constant during fast turns',
      all(item == (1, 0, 1, 0) for item in output[-20:]))
inputs.scroll(1)
check('live global wheel preference applies without reinstalling',
      output[-1] == (0x800, 0, 0, -3))
check('click and drag functions are preserved',
      inputs.click is click and inputs.left_button is left_button)
for name, raw, expected in (
        ('large values', {'pointer_step': 100, 'scroll_step': 100}, (12, 40)),
        ('small values', {'pointer_step': -99, 'scroll_step': 0}, (1, 1)),
        ('invalid values', {'pointer_step': True, 'scroll_step': float('nan')}, (2, 8))):
    candidate = {'layers': {'default': {'context_switching': {'precision_input': raw}}}}
    values = module.settings(candidate)
    check('bounds and defaults handle ' + name,
          (values['pointer_step'], values['scroll_step']) == expected)
for index, bad in enumerate((None, [], {'layers': None},
        {'layers': {'default': {'context_switching': {'precision_input': []}}}})):
    check('malformed container uses defaults ' + str(index),
          module.settings(bad) == module.DEFAULTS)
config['layers']['default']['context_switching']['precision_input'] = {
    'pointer_step': 12, 'scroll_step': 40, 'acceleration': True}
for _ in range(20):
    turn(elapsed=.01)
check('pointer maximum remains bounded with acceleration enabled',
      all(item[1] <= 12 for item in output[-20:]))
inputs.scroll(1)
check('wheel maximum remains bounded', output[-1] == (0x800, 0, 0, -40))
report['passed'] = True
write_report()
print(json.dumps({'checks': len(report['checks']), 'passed': True,
                  'native_output': False}))
