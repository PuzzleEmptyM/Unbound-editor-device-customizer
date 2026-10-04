"""Pure migration checks; optional installed-config audit prints counts only."""
import collections
import copy
import json
import pathlib
import sys

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'src'))
import uniform_controls as uniform

CHECKS = []


def check(name, result):
    CHECKS.append({'name': name, 'pass': bool(result)})
    assert result, name


def hotkey(value):
    return {'action': 'hotkey', 'keys': value}


def mouse(kind):
    return {'action': 'mouse_control', 'kind': kind}


def fingerprint(action):
    return json.dumps(action, sort_keys=True, ensure_ascii=False)


def nonmouse(layer):
    actions = list(layer.get('buttons', {}).values())
    actions += [entry['action'] for entry in uniform.extras(layer)]
    return collections.Counter(fingerprint(action) for action in actions
                               if not uniform._empty(action) and not uniform._mouse(action))


def verify(name, config):
    before = copy.deepcopy(config)
    counts = {key: nonmouse(layer) for key, layer in config['layers'].items()}
    uniform.normalize(config)
    check(name + ': all non-mouse action multiplicities preserved',
          all(nonmouse(layer) == counts[key] for key, layer in config['layers'].items()))
    check(name + ': canonical six on every layer',
          all(all(layer['buttons'].get(key) == mouse(kind) for key, kind in uniform.MOUSE.items())
              for layer in config['layers'].values()))
    check(name + ': no legacy mouse position remains',
          all(not uniform._mouse(action) or key in uniform.MOUSE
              for layer in config['layers'].values() for key, action in layer['buttons'].items()))
    check(name + ': unrelated root fields preserved',
          {k: v for k, v in before.items() if k != 'layers'} ==
          {k: v for k, v in config.items() if k != 'layers'})
    normalized = copy.deepcopy(config)
    check(name + ': second pass reports no changes', not uniform.normalize(config))
    check(name + ': second pass byte-equivalent data', config == normalized)


config = {'layers': {'default': {'name': 'Empty', 'buttons': {}}}, 'unrelated': {'keep': [1, 2]}}
verify('empty profile', config)

buttons = {key: hotkey('key-' + str(i)) for i, key in enumerate(uniform.SLOTS)}
old_mouse = ['CAM1', 'CAM2', 'CAM3', 'CAM4', 'CAM5', 'CAM6']
for destination, kind in zip(old_mouse, uniform.MOUSE.values()):
    buttons[destination] = mouse(kind)
labels = {key: {'name': 'Function ' + key, 'action': copy.deepcopy(action), 'custom': [1, 2]}
          for key, action in buttons.items()}
config = {'layers': {'custom': {'buttons': buttons, 'application_catalog': {'labels': labels},
                              'custom_metadata': {'keep': True}}}}
source = copy.deepcopy(config)
verify('fully occupied profile with former mouse slots', config)
check('matching former mouse positions receive corresponding displaced functions',
      all(config['layers']['custom']['buttons'][target] == source['layers']['custom']['buttons'][key]
          for key, target in zip(uniform.MOUSE, old_mouse)))
check('valid custom label dictionaries follow relocated actions',
      all(config['layers']['custom']['application_catalog']['labels'][target] ==
          source['layers']['custom']['application_catalog']['labels'][key]
          for key, target in zip(uniform.MOUSE, old_mouse)))
check('layer custom metadata retained', config['layers']['custom']['custom_metadata'] == {'keep': True})

buttons = {key: hotkey('full-' + str(i)) for i, key in enumerate(uniform.SLOTS)}
# Equal actions on different physical keys must not be deduplicated.
buttons['CUT'] = buttons['DIS'] = hotkey('duplicate')
config = {'layers': {'full': {'buttons': buttons, 'application_catalog': {'labels': {
    'CUT': {'name': 'Custom duplicate label', 'action': hotkey('duplicate'), 'custom': 7},
    'DIS': {'name': 'Stale label', 'action': hotkey('stale')},
}}}}}
verify('full custom profile without mouse slots', config)
records = uniform.extras(config['layers']['full'])
check('six full-profile functions retained as durable extras', len(records) == 6)
check('duplicate extra actions retained twice', sum(r['action'] == hotkey('duplicate') for r in records) == 2)
check('valid overflow label fully preserved', next(r for r in records if r['from_key'] == 'CUT')['label_metadata']['custom'] == 7)
check('stale overflow label rejected', next(r for r in records if r['from_key'] == 'DIS')['label'] == '')
saved_records = copy.deepcopy(records)
config['layers']['full']['buttons']['SLIP_SRC'] = {'action': 'layer_push', 'layer': 'custom-layer'}
verify('canonical key reedited after first migration', config)
check('old extras retained in stable order after later edit', uniform.extras(config['layers']['full'])[:6] == saved_records)
check('new displaced layer action remains available', uniform.extras(config['layers']['full'])[-1]['action'] == {'action': 'layer_push', 'layer': 'custom-layer'})

config = {'layers': {'mixed': {'buttons': {
    'SLIP_SRC': mouse('hold_y'), 'SLIP_DEST': hotkey('ctrl+s'),
    'CAM1': mouse('hold_x'), 'CAM2': mouse('hold_x'),
    'CAM3': mouse('unsupported-future-mouse-action'),
    'NONSTANDARD_BUTTON': hotkey('ctrl+alt+x'),
}}}}
verify('duplicate, swapped and unknown custom action types', config)
check('unknown custom mouse action preserved', config['layers']['mixed']['buttons']['CAM3'] == mouse('unsupported-future-mouse-action'))
check('nonstandard non-mouse physical key retained', config['layers']['mixed']['buttons']['NONSTANDARD_BUTTON'] == hotkey('ctrl+alt+x'))


print(json.dumps({"passed":True,"checks":len(CHECKS),"personal_config_read":False}))
