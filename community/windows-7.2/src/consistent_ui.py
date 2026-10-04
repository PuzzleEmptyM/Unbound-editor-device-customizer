"""Persist fixed controls and expose one fine-motion setting for every app."""
import copy
from PyQt6.QtWidgets import QGroupBox,QFormLayout,QSpinBox,QCheckBox,QLabel,QMessageBox
import app,config as cfg
import speed_editor_usability as ux
import speed_editor_uniform_controls as uniform
import speed_editor_precision_input as precision
import speed_editor_shared_controls as shared

def normalize(config):
    changed=uniform.normalize(config)
    prefs=config.get('layers',{}).get('default',{}).get('context_switching',{})
    common=prefs.get('shared_controls',{})
    if common.get('modifier') in (*uniform.MOUSE,'ESC'):
        common['modifier']='LIVE_OWR';changed=True
    return changed

def install():
    # A dialog parented to an editor embedded in QGraphicsProxyWidget can be
    # embedded itself: on Windows the resulting modal stays blank. Keep the
    # original questions and actions, but parent them to the real window.
    for name in ('question','warning','information','critical'):
        original_message=getattr(QMessageBox,name)
        def message(parent,*args,_original=original_message,**kwargs):
            if parent is not None:
                proxy=parent.graphicsProxyWidget()
                if proxy and proxy.scene() and proxy.scene().views():parent=proxy.scene().views()[0].window()
            return _original(parent,*args,**kwargs)
        setattr(QMessageBox,name,staticmethod(message))
    previous_load=cfg.load;previous_save=cfg.save
    def save(config):
        backup=copy.deepcopy(config)
        try:
            normalize(config)
            return previous_save(config)
        except Exception:
            config.clear();config.update(backup);raise
    def load(*args,**kwargs):
        config=previous_load(*args,**kwargs)
        if normalize(config):save(config)
        return config
    cfg.load=load;cfg.save=save
    precision.install(lambda:getattr(getattr(app,'_active_context_controller',None),'window',None)._config if getattr(getattr(app,'_active_context_controller',None),'window',None) is not None else {})
    previous_init=app.MainWindow.__init__
    def init(window,*args,**kwargs):
        previous_init(window,*args,**kwargs)
        if normalize(window._config):cfg.save(window._config)
        window.refresh_button_colors()
    app.MainWindow.__init__=init
    import speed_editor_catalog as catalog
    original_create=catalog.create_layer
    def create_layer(window,*args,**kwargs):
        result=original_create(window,*args,**kwargs)
        if result and normalize(window._config):cfg.save(window._config);window.refresh_button_colors()
        return result
    catalog.create_layer=create_layer
    original_refresh=ux._refresh
    def fixed(panel):
        return getattr(panel,'_button_name',None) in uniform.MOUSE and panel._mode_stack.currentIndex()==0
    def refresh(panel,*args):
        original_refresh(panel,*args)
        locked=fixed(panel)
        for control in (panel.category_combo,panel.action_combo,panel.stack):control.setEnabled(not locked)
        if locked:
            panel.save_btn.setEnabled(False)
            panel._ux_notice.setText('此鍵是所有程式共用的固定滑鼠操作。速度請到「通用操作」調整。')
            owner=getattr(panel,'_ux_owner',None)
            if owner:owner._ux_save_button.setEnabled(False)
    ux._refresh=refresh
    original_load=app.ActionPanel.load_button;original_dial=app.ActionPanel.load_dial;original_save=app.ActionPanel._save
    def load_button(panel,*args,**kwargs):
        result=original_load(panel,*args,**kwargs);refresh(panel);return result
    def load_dial(panel,*args,**kwargs):
        for control in (panel.category_combo,panel.action_combo,panel.stack):control.setEnabled(True)
        return original_dial(panel,*args,**kwargs)
    def save_button(panel):
        if fixed(panel):refresh(panel);return False
        if panel._mode_stack.currentIndex()==0 and panel._current_flat_idx()==17:
            panel._ux_notice.setText('滑鼠固定使用 SLIP SRC、SLIP DEST、TRANS DUR、CUT、DIS、SMTH CUT；請選擇其他功能。');return False
        return original_save(panel)
    app.ActionPanel.load_button=load_button;app.ActionPanel.load_dial=load_dial;app.ActionPanel._save=save_button
    original_page=shared.SharedPage.__init__
    def page(widget,owner):
        original_page(widget,owner)
        group=QGroupBox('所有程式共用的滑鼠速度');form=QFormLayout(group);prefs=precision.settings(owner._config)
        widget.pointer_step=QSpinBox();widget.pointer_step.setRange(1,12);widget.pointer_step.setValue(prefs['pointer_step']);widget.pointer_step.setSuffix(' 像素')
        widget.scroll_step=QSpinBox();widget.scroll_step.setRange(1,40);widget.scroll_step.setValue(prefs['scroll_step'])
        widget.acceleration=QCheckBox('快速旋轉時溫和加速');widget.acceleration.setChecked(prefs['acceleration'])
        form.addRow('滑鼠每步距離',widget.pointer_step);form.addRow('頁面捲動量',widget.scroll_step);form.addRow(widget.acceleration)
        note=QLabel('數值越小越精細。設定立即儲存，切換程式後速度保持一致。');note.setWordWrap(True);form.addRow(note)
        widget.layout().insertWidget(widget.layout().count()-2,group)
        def persist(*args):
            candidate=copy.deepcopy(owner._config)
            candidate['layers']['default'].setdefault('context_switching',{})['precision_input']={'pointer_step':widget.pointer_step.value(),'scroll_step':widget.scroll_step.value(),'acceleration':widget.acceleration.isChecked()}
            try:cfg.save(candidate)
            except (OSError,ValueError,TypeError) as error:widget.feedback.setText('尚未儲存：'+str(error));return
            owner._config['layers']=candidate['layers'];precision.reset();widget.feedback.setText('已儲存；所有程式立即共用此速度。');owner._context.changed.emit()
        widget.pointer_step.valueChanged.connect(persist);widget.scroll_step.valueChanged.connect(persist);widget.acceleration.toggled.connect(persist)
    shared.SharedPage.__init__=page
    # Retain old dial settings on disk while presenting the actual global values.
    from speed_editor_context import ProfileManager
    old_dial=ProfileManager.load_dial
    def dial(manager,*args,**kwargs):
        result=old_dial(manager,*args,**kwargs);prefs=precision.settings(manager.window._config)
        for name,key in [('_desktop_pointer_step','pointer_step'),('_desktop_scroll_step','scroll_step')]:
            control=getattr(manager,name,None)
            if control:
                control.blockSignals(True);control.setMinimum(1);control.setValue(prefs[key]);control.setEnabled(False);control.setToolTip('所有程式共用；請到「通用操作」調整。');control.blockSignals(False)
        return result
    ProfileManager.load_dial=dial
