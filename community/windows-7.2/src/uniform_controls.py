"""Keep one physical mouse block in every layer without losing other actions.

This module has no Qt, disk, or runtime dependencies.  Call normalize before
persisting a candidate configuration; the caller owns atomic saving and UI
refresh.  Non-mouse overflow remains executable through the caller's extra
function bank, rather than being discarded or silently replacing another key.
"""
import copy

MOUSE = {
    'SLIP_SRC': 'hold_x',
    'SLIP_DEST': 'hold_y',
    'TRANS_DUR': 'hold_left',
    'CUT': 'click',
    'DIS': 'right_click',
    'SMTH_CUT': 'double_click',
}
NAMES = {
    'hold_x': '滑鼠左右', 'hold_y': '滑鼠上下',
    'hold_left': '按住拖曳選取', 'click': '滑鼠左鍵',
    'right_click': '滑鼠右鍵', 'double_click': '滑鼠雙擊',
}
SLOTS = (
    'SMART_INSRT APPND RIPL_OWR CLOSE_UP PLACE_ON_TOP SRC_OWR '
    'TRANS SPLIT SNAP RIPL_DEL IN OUT TRIM_IN TRIM_OUT ROLL '
    'SLIP_SRC SLIP_DEST TRANS_DUR CUT DIS SMTH_CUT '
    'CAM1 CAM2 CAM3 CAM4 CAM5 CAM6 CAM7 CAM8 CAM9 '
    'SYNC_BIN AUDIO_LEVEL FULL_VIEW LIVE_OWR VIDEO_ONLY AUDIO_ONLY '
    'SOURCE TIMELINE SHTL JOG SCRL STOP_PLAY ESC'
).split()


def _mouse(action):
    return (isinstance(action, dict)
            and action.get('action') == 'mouse_control'
            and action.get('kind') in NAMES)


def _empty(action):
    return (action is None or isinstance(action, dict)
            and action.get('action', 'none') in ('none', None))


def extras(layer):
    """Return usable saved overflow records without modifying the layer."""
    settings = layer.get('uniform_controls', {})
    values = settings.get('extras', []) if isinstance(settings, dict) else []
    if not isinstance(values, list):
        return []
    return [entry for entry in values if isinstance(entry, dict)
            and isinstance(entry.get('action'), dict)
            and not _empty(entry['action'])]


def _valid_label(labels, key, action):
    value = labels.get(key)
    return copy.deepcopy(value) if (isinstance(value, dict)
                                    and value.get('action') == action) else None


def _normalize_layer(layer):
    buttons = layer.get('buttons')
    if buttons is None:
        buttons = layer['buttons'] = {}
    if not isinstance(buttons, dict):
        return
    metadata = layer.get('application_catalog')
    if not isinstance(metadata, dict):
        metadata = layer['application_catalog'] = {}
    labels = metadata.get('labels')
    if not isinstance(labels, dict):
        labels = metadata['labels'] = {}
    settings = layer.get('uniform_controls')
    if not isinstance(settings, dict):
        settings = layer['uniform_controls'] = {}
    saved_extras = settings.get('extras')
    if not isinstance(saved_extras, list):
        saved_extras = settings['extras'] = []
    settings['version'] = 1

    # Read every source before changing any key, including cycles where a
    # former mouse key is itself inside the new canonical block.
    displaced = []
    for key in MOUSE:
        action = buttons.get(key)
        if not _empty(action) and not _mouse(action):
            displaced.append((key, copy.deepcopy(action),
                              _valid_label(labels, key, action)))
    former = {kind: [] for kind in NAMES}
    for key in SLOTS:
        action = buttons.get(key)
        if key not in MOUSE and _mouse(action):
            former[action['kind']].append(key)
    former_keys = {key for values in former.values() for key in values}

    for key, action in list(buttons.items()):
        if _mouse(action):
            del buttons[key]
            labels.pop(key, None)

    # Prefer a displaced function's matching old mouse position, followed by
    # other former mouse positions, then genuinely unused physical keys.
    free = [key for key in SLOTS if key not in MOUSE and _empty(buttons.get(key))]
    for source, action, label in displaced:
        preferred = [key for key in former[MOUSE[source]] if key in free]
        preferred += [key for key in free if key in former_keys and key not in preferred]
        target = (preferred or free or [None])[0]
        if target is None:
            record = {'from_key': source, 'action': action,
                      'label': str(label.get('name', '')) if label else ''}
            if label is not None:
                record['label_metadata'] = label
            saved_extras.append(record)
        else:
            free.remove(target)
            buttons[target] = action
            if label is not None:
                labels[target] = label
            else:
                labels.pop(target, None)

    for key, kind in MOUSE.items():
        action = {'action': 'mouse_control', 'kind': kind}
        buttons[key] = action
        labels[key] = {'name': NAMES[kind], 'action': copy.deepcopy(action)}


def normalize(config):
    """Normalize all valid layers in place; return whether anything changed.

    Every assigned non-mouse action remains assigned exactly once, or becomes
    one durable extras record when the physical layer has no available slot.
    Existing extras and unrelated configuration fields are retained.
    """
    layers = config.get('layers', {})
    if not isinstance(layers, dict):
        return False
    changed = False
    for layer in layers.values():
        if not isinstance(layer, dict):
            continue
        before = copy.deepcopy(layer)
        _normalize_layer(layer)
        changed = changed or layer != before
    return changed
