"""Edit overflow actions locally without persisting a virtual configuration layer."""
import copy
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QSplitter, QMessageBox
import app, config as cfg
import speed_editor_desktop_ui as desktop
import speed_editor_usability as ux
from speed_editor_expanded_obs import OPERATIONS


def action_value(panel):
    """Read every currently supported ActionPanel type without invoking its saver."""
    index = panel._current_flat_idx()
    if index == 0:
        return {'action': cfg.ACTION_NONE}
    text = {1: ('hotkey', 'keys', 'hotkey_input'), 2: ('hold_key', 'keys', 'hold_input'),
            3: ('toggle_hold', 'keys', 'toggle_hold_input'), 4: ('app_switch', 'app', 'app_input'),
            5: ('app_launch', 'path', 'launch_input')}
    if index in text:
        action, field, widget = text[index]
        return {'action': action, field: getattr(panel, widget).text().strip()}
    if index == 6:
        return {'action': cfg.ACTION_OBS_SCENE, 'scene': panel.obs_scene.currentText()}
    if index in (7, 8, 9):
        return {'action': cfg.ACTION_OBS_TOGGLE, 'toggle': {7: 'stream', 8: 'record', 9: 'mute_mic'}[index]}
    if index == 10:
        return {'action': cfg.ACTION_LAYER_PUSH, 'layer': panel.layer_push_combo.currentData() or ''}
    if index == 11:
        return {'action': cfg.ACTION_LAYER_POP}
    if index in (12, 13, 14):
        mode, prefix = {12: ('sys_vol', 'sys_vol'), 13: ('app_vol', 'app_vol'), 14: ('brightness', 'brightness')}[index]
        value = {'action': cfg.ACTION_DIAL_MODE, 'mode': mode,
                 'hw_mode': getattr(panel, prefix + '_hw_mode').currentText(),
                 'sensitivity': getattr(panel, prefix + '_sensitivity').value()}
        if index == 13:
            value['app'] = panel.dial_app_input.text().strip()
        return value
    if index == 15:
        return {'action': cfg.ACTION_DIAL_MODE, 'mode': 'normal'}
    if index == 16:
        return {'action': 'context_dial', 'mode': panel._context_mode.currentData()}
    if index == 17:
        return {'action': 'mouse_control', 'kind': panel._desktop_mouse.currentData()}
    if index == 18:
        operation = panel._obs_op.currentData()
        if operation not in OPERATIONS:
            raise ValueError('請選擇 OBS 動作。')
        value = {'action': 'obs_control', 'operation': operation}
        for field in OPERATIONS[operation][1]:
            widget = panel._obs_fields[field]
            if field == 'value':
                value[field] = widget.value()
            else:
                data = widget.currentData()
                value[field] = data if data is not None and widget.currentText() == widget.itemText(widget.currentIndex()) else widget.currentText().strip()
        return value
    raise ValueError('這個動作類型尚未提供其他功能編輯器。')


def records(config, layer_id):
    layer = config.get('layers', {}).get(layer_id, {})
    settings = layer.get('uniform_controls', {})
    values = settings.get('extras', []) if isinstance(settings, dict) else []
    return values if isinstance(values, list) else []


def editable(record):
    return isinstance(record, dict) and isinstance(record.get('action'), dict)


def allow_leave(editor):
    """Parent native prompts to the dialog, never its embedded graphics panel."""
    panel = editor.action_panel
    if not ux._dirty(panel):
        return True
    if getattr(panel, '_ux_prompt_open', False):
        return False
    panel._ux_prompt_open = True
    try:
        answer = QMessageBox.question(editor, '尚未儲存',
            '目前的設定尚未儲存。\n\n儲存後繼續，或捨棄這次變更？',
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        if answer == QMessageBox.StandardButton.Save:
            return panel._save() is True
        if answer == QMessageBox.StandardButton.Discard:
            ux._revert(panel)
            return True
        return False
    finally:
        panel._ux_prompt_open = False


class ExtraActionPanel(app.ActionPanel):
    def __init__(self, editor):
        self.extra_editor = editor
        super().__init__()

    def _save(self, *args):
        return self.extra_editor.save_current()


class ExtraEditor(QDialog):
    def __init__(self, owner, layer_id, parent=None):
        super().__init__(parent or owner)
        self.owner = owner; self.layer_id = layer_id; self.row = None; self.baseline = None
        self.virtual_id = '__extra_editor__'
        while self.virtual_id in owner._config.get('layers', {}):
            self.virtual_id += '_'
        self.virtual_config = copy.deepcopy(owner._config)
        self.virtual_config['layers'][self.virtual_id] = {'name': '其他功能（編輯中）', 'buttons': {}}
        self.setWindowTitle('編輯其他功能 · ' + owner._config['layers'][layer_id].get('name', layer_id))
        desktop.fit_screen(self, 960, 740)
        layout = QVBoxLayout(self)
        hint = QLabel('選擇左側功能，修改來源、濾鏡或動作後按「儲存」。這裡的設定適用目前程式的「其他功能」。')
        hint.setWordWrap(True); layout.addWidget(hint)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.items = QListWidget(); self.items.setMinimumWidth(180)
        self.items.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.items.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.action_panel = ExtraActionPanel(self)
        self.action_panel.set_layer(self.virtual_id, self.virtual_config)
        self.action_panel.refresh_layers(cfg.get_layers(owner._config))
        self.fit = desktop.FitEditor(self.action_panel, base=QSize(380, max(670, self.action_panel.sizeHint().height())))
        splitter.addWidget(self.items); splitter.addWidget(self.fit); splitter.setSizes([280, 650]); layout.addWidget(splitter, 1)
        self.feedback = QLabel('儲存只更新這筆其他功能，原本按鍵配置會保留。'); self.feedback.setWordWrap(True); layout.addWidget(self.feedback)
        self.close_button = QPushButton('完成並關閉'); self.close_button.clicked.connect(self.close); layout.addWidget(self.close_button)
        self.shortcut = QShortcut(QKeySequence('Ctrl+S'), self); self.shortcut.activated.connect(self.action_panel._save)
        self.items.currentItemChanged.connect(self.select)
        self.populate(); self.items.setCurrentRow(0)

    def populate(self):
        self.items.blockSignals(True); self.items.clear()
        for index, entry in enumerate(records(self.owner._config, self.layer_id)):
            if not editable(entry):
                continue
            action = entry['action']
            label = entry.get('label') or action.get('keys') or action.get('operation') or action.get('action', '未指定')
            if action.get('action') in ('none', None):
                label = '未指定'
            item = QListWidgetItem(str(self.items.count() + 1) + '　' + str(label))
            item.setData(Qt.ItemDataRole.UserRole, index); item.setToolTip(item.text()); self.items.addItem(item)
            if index == self.row:
                self.items.setCurrentItem(item)
        self.items.blockSignals(False)

    def select(self, item, previous):
        if item is None:
            return
        # Saving in the leave prompt rebuilds the list. Capture the logical
        # rows before prompting so no deleted QListWidgetItem is read later.
        requested_row = item.data(Qt.ItemDataRole.UserRole)
        previous_row = previous.data(Qt.ItemDataRole.UserRole) if previous is not None else self.row
        if not allow_leave(self):
            self.select_row(previous_row); return
        self.row = requested_row
        self.select_row(requested_row)
        values = records(self.owner._config, self.layer_id)
        if self.row >= len(values) or not editable(values[self.row]):
            self.feedback.setText('此功能已變更，請關閉後重新開啟。'); return
        self.baseline = copy.deepcopy(values[self.row])
        self.virtual_config['layers'][self.virtual_id]['buttons']['EXTRA'] = copy.deepcopy(self.baseline['action'])
        self.action_panel.load_button('EXTRA', self.virtual_config, self.virtual_id)
        self.action_panel.title.setText('其他功能：' + (str(self.baseline.get('label', '')) or str(self.row + 1)))
        self.fit.refit()

    def select_row(self, row):
        self.items.blockSignals(True)
        for index in range(self.items.count()):
            item = self.items.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == row:
                self.items.setCurrentItem(item); break
        self.items.blockSignals(False)

    def save_current(self):
        if self.row is None or self.action_panel._mode_stack.currentIndex() != 0:
            return False
        current = records(self.owner._config, self.layer_id)
        if self.row >= len(current) or current[self.row] != self.baseline:
            self.feedback.setText('這筆功能已由其他操作變更，請先關閉後重新開啟，避免覆蓋新設定。'); return False
        try:
            action = action_value(self.action_panel)
            candidate = copy.deepcopy(self.owner._config)
            record = candidate['layers'][self.layer_id]['uniform_controls']['extras'][self.row]
            record['action'] = copy.deepcopy(action)
            # Keep a meaningful existing name while only editing its target.
            same_kind = (action.get('action'), action.get('operation')) == (self.baseline['action'].get('action'), self.baseline['action'].get('operation'))
            if not same_kind:
                if action.get('action') == 'obs_control':
                    record['label'] = OPERATIONS[action['operation']][0]
                else:
                    display = {'layers': {'extra': {'buttons': {'EXTRA': action}}}}
                    record['label'] = app._get_btn_display_label('EXTRA', '其他功能', display, 'extra').replace('\n', ' ')
            if isinstance(record.get('label_metadata'), dict):
                record['label_metadata'].update(name=record.get('label', ''), action=copy.deepcopy(action))
            cfg.save(candidate)
        except (OSError, ValueError, TypeError) as error:
            self.feedback.setText('尚未儲存：' + str(error)); return False
        self.owner._config['layers'] = candidate['layers']
        self.baseline = copy.deepcopy(records(self.owner._config, self.layer_id)[self.row])
        self.virtual_config['layers'][self.virtual_id]['buttons']['EXTRA'] = copy.deepcopy(action)
        ux._mark_clean(self.action_panel); self.action_panel.saved.emit(); self.populate()
        self.feedback.setText('已儲存這筆其他功能。')
        self.owner.refresh_button_colors()
        self.owner._context.changed.emit()
        return True

    def closeEvent(self, event):
        if not allow_leave(self):
            event.ignore(); return
        super().closeEvent(event)

    def reject(self):
        # Escape and the title-bar close must use the same unsaved-change guard.
        if allow_leave(self):
            super().reject()


def install():
    if getattr(desktop.TemplateEditor, '_extra_editor_installed', False):
        return
    desktop.TemplateEditor._extra_editor_installed = True
    previous_init = desktop.TemplateEditor.__init__
    def init(editor, manager):
        previous_init(editor, manager)
        editor._extra_editor_button = QPushButton('編輯其他功能…')
        editor._extra_editor_button.setVisible(any(editable(value) for value in records(editor._config, editor._layer_id)))
        editor.layout().insertWidget(max(0, editor.layout().count() - 2), editor._extra_editor_button)
        def open_extra():
            if not allow_leave(editor):
                return
            dialog = ExtraEditor(editor.owner, editor._layer_id, editor)
            editor._extra_dialog = dialog
            dialog.exec()
            editor.populate()
        editor._extra_editor_button.clicked.connect(open_extra)
    desktop.TemplateEditor.__init__ = init
