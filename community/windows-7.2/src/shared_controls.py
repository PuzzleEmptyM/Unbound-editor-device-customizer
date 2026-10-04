"""Momentary common controls; app templates and saved actions stay untouched."""
import copy,time,html
from PyQt6.QtCore import Qt,QTimer
from PyQt6.QtWidgets import QWidget,QVBoxLayout,QLabel,QCheckBox,QComboBox,QPushButton
import app,config as cfg
import speed_editor_context as context
import speed_editor_context_runtime as runtime
import speed_editor_expanded_overlay as overlay
import speed_editor_desktop_input as inputs
import speed_editor_usability as ux
import speed_editor_precision_input as precision
import speed_editor_uniform_controls as uniform

LAYER='shared-controls'
MODIFIER='LIVE_OWR'
MOUSE={'SLIP_SRC':'hold_x','SLIP_DEST':'hold_y','TRANS_DUR':'hold_left','CUT':'click','DIS':'right_click','SMTH_CUT':'double_click'}
HOTKEYS={'CAM1':('複製','ctrl+c'),'CAM2':('貼上','ctrl+v'),'CAM3':('剪下','ctrl+x'),
 'CAM4':('復原','ctrl+z'),'CAM5':('重做','ctrl+y'),'CAM6':('全選','ctrl+a'),
 'CAM7':('尋找','ctrl+f'),'CAM8':('儲存','ctrl+s'),'CAM9':('切換視窗','alt+tab'),
 'IN':('網頁上一頁','alt+left'),'OUT':('網頁下一頁','alt+right'),
 'TRIM_IN':('上一個分頁','ctrl+shift+tab'),'TRIM_OUT':('下一個分頁','ctrl+tab'),
 'SOURCE':('新增分頁','ctrl+t'),'TIMELINE':('重開分頁','ctrl+shift+t'),
 'FULL_VIEW':('關閉分頁','ctrl+w'),'STOP_PLAY':('確認選取','enter'),
 'SYNC_BIN':('取消／返回','esc'),'VIDEO_ONLY':('重新整理','ctrl+r')}
NAMES={'hold_x':'滑鼠左右','hold_y':'滑鼠上下','hold_left':'按住拖曳選取',
 'click':'滑鼠左鍵','right_click':'滑鼠右鍵','double_click':'滑鼠雙擊'}

def settings(config):
    value=context.preferences(config).get('shared_controls',{})
    return {'enabled':True,'modifier':MODIFIER,**(value if isinstance(value,dict) else {})}

def layer(config):
    if LAYER in config.get('layers',{}):return config['layers'][LAYER]
    buttons={key:{'action':'mouse_control','kind':kind} for key,kind in MOUSE.items()}
    buttons.update({key:{'action':'hotkey','keys':keys} for key,(name,keys) in HOTKEYS.items()})
    buttons.update({key:{'action':'context_dial','mode':mode} for key,mode in [('JOG','scroll'),('SHTL','pointer_x'),('SCRL','pointer_y')]})
    labels={key:{'name':NAMES[kind],'action':copy.deepcopy(buttons[key])} for key,kind in MOUSE.items()}
    labels.update({key:{'name':name,'action':copy.deepcopy(buttons[key])} for key,(name,keys) in HOTKEYS.items()})
    labels.update({key:{'name':name,'action':copy.deepcopy(buttons[key])} for key,name in [('JOG','旋鈕：頁面捲動'),('SHTL','旋鈕：滑鼠左右'),('SCRL','旋鈕：滑鼠上下')]})
    return {'name':'固定通用操作','buttons':buttons,'application_catalog':{'labels':labels},'context_dial':{'enabled':True,'pointer_step':12,'scroll_step':35,'interval_ms':120}}

def active(owner):return bool(owner._context.bridge and getattr(owner._context.bridge,'shared_active',False))

def extra_records(bridge,origin=None):
    config=bridge.controller.window._config
    origin=origin if origin is not None else getattr(bridge,'shared_origin','')
    result=copy.deepcopy(uniform.extras(config['layers'].get(origin,{})))
    if origin!=LAYER:result+=copy.deepcopy(uniform.extras(layer(config)))
    modifier=settings(config)['modifier'];mod_action=layer(config).get('buttons',{}).get(modifier,{})
    if mod_action.get('action','none')!='none':result.append({'from_key':modifier,'action':copy.deepcopy(mod_action),'label':'通用鍵原功能'})
    action=layer(config).get('buttons',{}).get('ESC',{})
    if result and action.get('action','none')!='none':
        result.append({'from_key':'ESC','action':copy.deepcopy(action),'label':'共用 ESC 原功能'})
    return result

def runtime_layer(bridge):
    data=copy.deepcopy(layer(bridge.controller.window._config));records=extra_records(bridge)
    page=getattr(bridge,'shared_extra',0)
    if records:
        if page:
            buttons={key:{'action':'mouse_control','kind':kind} for key,kind in MOUSE.items()}
            labels={key:{'name':NAMES[kind],'action':copy.deepcopy(buttons[key])} for key,kind in MOUSE.items()}
            slots=[k for k in bridge.controller.window.se_widget._btn_widgets if k not in MOUSE and k not in ('ESC',settings(bridge.controller.window._config)['modifier'])]
            # Keep OBS media controls in the adjacent top-left six-key block.
            preferred=['SMART_INSRT','APPND','RIPL_OWR','CLOSE_UP','PLACE_ON_TOP','SRC_OWR']
            slots=[k for k in preferred if k in slots]+[k for k in slots if k not in preferred]
            order={'media_previous':0,'media_pause_toggle':1,'media_next':2,'media_restart':3,'media_stop':4,'filter_toggle':5}
            records.sort(key=lambda r:order.get(r['action'].get('operation'),99))
            for key,record in zip(slots,records[(page-1)*len(slots):page*len(slots)]):
                buttons[key]=record['action'];labels[key]={'name':record.get('label') or record['from_key'].replace('_',' ')+' 原功能','action':copy.deepcopy(record['action'])}
            data={'name':'程式其他功能','buttons':buttons,'application_catalog':{'labels':labels}}
        data.setdefault('buttons',{})['ESC']={'action':'shared_page'}
        data.setdefault('application_catalog',{}).setdefault('labels',{})['ESC']={'name':'切換其他功能' if page else '程式其他功能','action':{'action':'shared_page'}}
    return data

def effective_mode(bridge):
    data=runtime_layer(bridge)
    held=getattr(bridge,'shared_held',set())-getattr(bridge,'shared_blocked',set())
    kinds=[data.get('buttons',{}).get(k,{}).get('kind') for k in held]
    if 'hold_y' in kinds:return 'pointer_y'
    if 'hold_x' in kinds:return 'pointer_x'
    return getattr(bridge,'shared_mode','pointer_x')

def rows(owner):
    bridge=owner._context.bridge
    data=runtime_layer(bridge) if bridge and getattr(bridge,'shared_active',False) else layer(owner._config)
    result=[];modifier=settings(owner._config)['modifier']
    for key in owner.se_widget._btn_widgets:
        action=data.get('buttons',{}).get(key,{'action':'none'})
        label='放開回到程式' if key==modifier else NAMES.get(action.get('kind'),'')
        if not label and action.get('action')=='hotkey':
            label=HOTKEYS[key][0] if key in HOTKEYS and action.get('keys')==HOTKEYS[key][1] else action.get('keys','快捷鍵')
        if action.get('action')=='context_dial':label={'scroll':'旋鈕：頁面捲動','pointer_x':'旋鈕：滑鼠左右','pointer_y':'旋鈕：滑鼠上下'}.get(action.get('mode'),'旋鈕')
        if not label:label=app._get_btn_display_label(key,key,{'layers':{LAYER:data}},LAYER).replace('\n',' ') if action.get('action')!='none' else '未指定'
        result.append((key,label,action))
    return result

class SharedPage(QWidget):
    def __init__(self,owner):
        super().__init__();self.owner=owner;layout=QVBoxLayout(self)
        title=QLabel('固定通用操作');title.setStyleSheet('font-size:23px;font-weight:600');layout.addWidget(title)
        self.enabled=QCheckBox('按住通用鍵時使用共用配置');self.enabled.setChecked(settings(owner._config)['enabled']);layout.addWidget(self.enabled)
        layout.addWidget(QLabel('通用鍵（原來的單按功能會在放開時執行）：'))
        self.modifier=QComboBox()
        for key in owner.se_widget._btn_widgets:
            if key not in MOUSE and key!='ESC':self.modifier.addItem(key.replace('_',' '),key)
        self.modifier.setCurrentIndex(max(0,self.modifier.findData(settings(owner._config)['modifier'])));layout.addWidget(self.modifier)
        self.hint=QLabel();self.hint.setWordWrap(True);layout.addWidget(self.hint)
        layout.addWidget(QLabel('共用配置適用所有程式；網頁功能使用瀏覽器標準快捷鍵。\n關閉共用配置時，有其他功能的程式仍可按住通用鍵進入附加頁。'))
        edit=QPushButton('編輯並儲存共用按鍵…');edit.clicked.connect(self.edit);layout.addWidget(edit)
        self.feedback=QLabel();self.feedback.setWordWrap(True);layout.addWidget(self.feedback);layout.addStretch()
        self.enabled.toggled.connect(self.save);self.modifier.currentIndexChanged.connect(self.save);owner._context.changed.connect(self.update_hint);self.update_hint()
    def update_hint(self):
        key=settings(self.owner._config)['modifier'].replace('_',' ')
        self.hint.setText('每個程式都相同：SLIP SRC＋旋鈕左右；SLIP DEST＋旋鈕上下\nCUT 左鍵 · DIS 右鍵 · SMTH CUT 雙擊；TRANS DUR＋方向鍵＋旋鈕拖曳\n按住 '+key+'：CAM 1～3 複製／貼上／剪下，4～6 復原／重做／全選，7～9 尋找／儲存／切換視窗\nJOG 捲動 · SHTL 左右 · SCRL 上下；放開通用鍵回到程式\n若程式有其他功能：按住通用鍵，再按 ESC 切換功能頁。')
        if LAYER in self.owner._config['layers']:
            lines=[]
            for code,label,action in rows(self.owner):
                if action.get('action','none')!='none' and code!=settings(self.owner._config)['modifier']:lines.append(code.replace('_',' ')+'：'+label)
            table=''.join('<tr>'+''.join('<td style="padding:3px 14px 3px 0">'+html.escape(value)+'</td>' for value in lines[i:i+3])+'</tr>' for i in range(0,len(lines),3))
            self.hint.setText('<p>按住 '+html.escape(key)+' 進入共用配置；預設旋鈕移動左右。</p><table width="100%">'+table+'</table>')
    def save(self,*args):
        if active(self.owner):self.feedback.setText('請先放開硬體通用鍵，再變更設定。');return
        candidate=copy.deepcopy(self.owner._config)
        candidate['layers']['default'].setdefault('context_switching',{})['shared_controls']={'enabled':self.enabled.isChecked(),'modifier':self.modifier.currentData()}
        try:cfg.save(candidate)
        except (OSError,ValueError,TypeError) as error:self.feedback.setText('尚未儲存：'+str(error));return
        self.owner._config['layers']=candidate['layers'];self.update_hint();self.feedback.setText('已儲存通用鍵設定。');self.owner._context.changed.emit()
    def edit(self):
        if not ux._allow_leave(self.owner.action_panel):return
        from speed_editor_desktop_ui import TemplateEditor
        if LAYER not in self.owner._config['layers']:
            candidate=copy.deepcopy(self.owner._config);candidate['layers'][LAYER]=copy.deepcopy(layer(candidate))
            try:cfg.save(candidate)
            except (OSError,ValueError,TypeError) as error:self.feedback.setText('尚未儲存：'+str(error));return
            self.owner._config['layers']=candidate['layers']
        manager=QWidget(self);manager.window=self.owner;manager.binding=QComboBox(manager);manager.binding.addItem('固定通用操作',LAYER)
        dialog=TemplateEditor(manager)
        # The original editor can store every existing action; three dial rows
        # remain labelled clearly even though they are new shared-only actions.
        dialog.setWindowTitle('編輯固定通用操作（所有程式共用）')
        for i in range(dialog.keys.count()):
            if dialog.keys.item(i).data(Qt.ItemDataRole.UserRole)=='CAM1':dialog.keys.setCurrentRow(i);break
        floating=self.owner._expanded_overlay;visible=floating.isVisible();floating.hide()
        try:dialog.exec()
        finally:
            if visible and not floating.closing:floating.show()
            manager.deleteLater()
        self.owner._context.changed.emit()

def install():
    old_key=runtime.RuntimeBridge.on_key;old_jog=runtime.RuntimeBridge.on_jog;old_commit=runtime.RuntimeBridge.commit;old_release=runtime.RuntimeBridge.release_mouse
    def release(bridge):
        precision.reset()
        if getattr(bridge,'shared_drag',False):inputs.left_button(False);bridge.shared_drag=False
        old_release(bridge)
    def commit(bridge):
        if not getattr(bridge,'shared_active',False):return old_commit(bridge)
    def dispatch(bridge,key,released=False):
        pressed=getattr(bridge,'shared_actions',{})
        if released:
            action=pressed.pop(key,None)
            if action is None:return
        else:
            action=copy.deepcopy(runtime_layer(bridge).get('buttons',{}).get(key,{}));pressed[key]=action;bridge.shared_actions=pressed
        if action.get('action')=='shared_page':
            if not released and not (getattr(bridge,'shared_held',set())-{key,settings(bridge.controller.window._config)['modifier']}):
                count=len([k for k in bridge.controller.window.se_widget._btn_widgets if k not in MOUSE and k not in ('ESC',settings(bridge.controller.window._config)['modifier'])])
                pages=(len(extra_records(bridge))+count-1)//count
                bridge.shared_extra=(getattr(bridge,'shared_extra',0)+1)%(pages+1)
                if not settings(bridge.controller.window._config)['enabled'] and not bridge.shared_extra:bridge.shared_extra=1
                precision.reset()
            return
        kind=action.get('kind')
        if action.get('action')=='mouse_control':
            if kind=='hold_left':
                if not released and not getattr(bridge,'shared_drag',False):inputs.left_button(True);bridge.shared_drag=True
                elif released and getattr(bridge,'shared_drag',False):inputs.left_button(False);bridge.shared_drag=False
            elif kind not in ('hold_x','hold_y') and not released:inputs.click(kind)
        elif action.get('action')=='context_dial' and not released:bridge.shared_mode=action.get('mode','pointer_x');precision.reset()
        elif action.get('action')=='toggle_hold':
            if not released:
                toggles=bridge.cells['_toggle_holds'].cell_contents;token='shared:'+key
                if token in toggles:app.hotkey_action.release_keys(toggles.pop(token))
                else:app.hotkey_action.press_keys(action.get('keys',''));toggles[token]=action.get('keys','')
        elif action.get('action')=='dial_mode':
            if not released:
                mode=action.get('mode','normal');current=bridge.cells['_dial_override'].cell_contents
                if mode!='normal' and current and current.get('mode')==mode:
                    bridge.cells['_set_dial_override'].cell_contents('normal');bridge.cells['signals'].cell_contents.dial_mode_changed.emit('','')
                else:
                    bridge.cells['_set_dial_override'].cell_contents(mode,action.get('app',''),action.get('sensitivity',100));bridge.cells['signals'].cell_contents.dial_mode_changed.emit(mode,key)
        else:
            temporary=copy.copy(bridge.controller.window._config);temporary['layers']={**temporary['layers'],LAYER:{'buttons':{key:action}}}
            callbacks={name:bridge.cells[cell].cell_contents for name,cell in [('on_push','_push_layer'),('on_pop','_pop_layer')] if cell in bridge.cells}
            app.dispatch(key,temporary,LAYER,is_release=released,**callbacks)
    def key(bridge,keys):
        with bridge.lock:
            owner=bridge.controller.window;s=settings(owner._config);names={k.name for k in keys};modifier=s['modifier']
            before=getattr(bridge,'shared_held',set());was=getattr(bridge,'shared_active',False)
            has_extra=bool(extra_records(bridge,bridge.stack[-1]))
            wants=bool((s['enabled'] or has_extra) and modifier in names)
            if wants and not was:
                old_commit(bridge);bridge.key_callback([]);release(bridge)
                bridge.shared_active=True;bridge.shared_used=False;bridge.shared_mode='pointer_x';bridge.shared_last=0
                bridge.shared_origin=bridge.stack[-1];bridge.shared_extra=0 if s['enabled'] else 1;bridge.shared_actions={}
                bridge.shared_blocked=set(before)-{modifier};before=set()
            if wants:
                bridge.shared_held=names
                bridge.shared_blocked=getattr(bridge,'shared_blocked',set())&names
                for k in before-names-{modifier}:dispatch(bridge,k,True)
                for k in names-before-{modifier}-bridge.shared_blocked:dispatch(bridge,k);bridge.shared_used=True
                bridge.controller.changed.emit();return
            if was:
                for k in before-{modifier}:dispatch(bridge,k,True)
                release(bridge);bridge.shared_active=False;bridge.shared_held=set()
                if not bridge.shared_used:
                    from hid_layer import Key
                    bridge.key_callback([Key[modifier]]);bridge.key_callback([])
                bridge.shared_blocked=names;old_commit(bridge);bridge.controller.changed.emit();return
            blocked=getattr(bridge,'shared_blocked',set())&names;bridge.shared_blocked=blocked;bridge.shared_held=names
            if (before^names)&set(MOUSE):precision.reset()
            return old_key(bridge,[k for k in keys if k.name not in blocked])
    def jog(bridge,callback,mode,value):
        if not getattr(bridge,'shared_active',False):
            with bridge.lock:
                bridge.commit()
                data=bridge.controller.window._config['layers'].get(bridge.stack[-1],{});dial=data.get('context_dial',{})
                selected=bridge.modes.get(bridge.stack[-1],dial.get('mode','default'))
                axis=list(bridge.pointer_holds.values())[-1] if bridge.pointer_holds else (selected[-1] if selected in ('pointer_x','pointer_y') and dial.get('enabled',False) and not bridge.cells['_dial_override'].cell_contents else None)
                if axis:
                    inputs.move(axis,value);return
            return old_jog(bridge,callback,mode,value)
        with bridge.lock:
            if not value:return
            bridge.shared_used=True;data=runtime_layer(bridge);settings_=data.get('context_dial',{})
            selected=effective_mode(bridge)
            now=time.monotonic();interval=0 if selected.startswith('pointer_') else .12
            if now-getattr(bridge,'shared_last',0)<interval:return
            bridge.shared_last=now
            if selected.startswith('pointer_'):inputs.move(selected[-1],value,settings_.get('pointer_step',12))
            else:inputs.scroll(value,settings_.get('scroll_step',35))
    runtime.RuntimeBridge.on_key=key;runtime.RuntimeBridge.on_jog=jog;runtime.RuntimeBridge.commit=commit;runtime.RuntimeBridge.release_mouse=release
    original_rows=overlay.rows;original_caption=overlay.dial_caption;original_refresh=overlay.Overlay.refresh
    overlay.rows=lambda owner:rows(owner) if active(owner) else original_rows(owner)
    overlay.dial_caption=lambda owner:({'scroll':'頁面捲動','pointer_x':'滑鼠左右','pointer_y':'滑鼠上下'}.get(effective_mode(owner._context.bridge),'滑鼠左右') if active(owner) else original_caption(owner))
    def refresh(panel):
        original_refresh(panel)
        if active(panel.owner):
            panel.title.setText('程式其他功能' if getattr(panel.owner._context.bridge,'shared_extra',0) else '固定通用操作');panel.detail.setText('按住 '+settings(panel.owner._config)['modifier'].replace('_',' ')+' · 放開回到 '+panel.owner._config['layers'].get(overlay.active_layer(panel.owner),{}).get('name','目前程式'));panel.board.update()
        else:
            # Force app title restoration even if no app or layer changed.
            if panel.title.text() in ('固定通用操作','程式其他功能'):panel.last_signature=None;original_refresh(panel)
    overlay.Overlay.refresh=refresh

