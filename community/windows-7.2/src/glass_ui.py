"""Add appearance and guide tabs while retaining all v6 editor/runtime hooks."""
from PyQt6.QtCore import Qt,QTimer
from PyQt6.QtGui import QColor,QPainter,QPen,QFont
from PyQt6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QCheckBox,QSlider,QColorDialog,QFrame
import app
import speed_editor_usability as ux
import speed_editor_desktop_ui as desktop
from speed_editor_glass_theme import Theme,preferences,colors,PRESETS,paint_surface,remap,native_backdrop
from speed_editor_glass_help import Guide

class Appearance(QWidget):
    def __init__(self,owner):
        super().__init__();self.owner=owner;layout=QVBoxLayout(self);layout.setContentsMargins(28,24,28,24);layout.setSpacing(16)
        title=QLabel('屬於你的工作檯');title.setStyleSheet('font-size:27px;font-weight:600;');layout.addWidget(title)
        intro=QLabel('配色與霧面質感同步套用至主視窗和浮動面板。每次調整都會儲存。');intro.setWordWrap(True);layout.addWidget(intro)
        card=QFrame();card.setObjectName('glassCard');card_layout=QVBoxLayout(card);card_layout.setContentsMargins(22,22,22,22);card_layout.setSpacing(18)
        row=QHBoxLayout();row.addWidget(QLabel('主題色'));self.presets=QComboBox()
        for label,color in PRESETS:self.presets.addItem(label,color)
        self.presets.addItem('自訂',None);row.addWidget(self.presets,1);self.custom=QPushButton('自訂顏色…');row.addWidget(self.custom);card_layout.addLayout(row)
        self.light=QCheckBox('亮色介面');card_layout.addWidget(self.light)
        self.blur=QCheckBox('使用 Windows 毛玻璃背景');card_layout.addWidget(self.blur)
        row=QHBoxLayout();row.addWidget(QLabel('霧面濃度'));self.frost=QSlider(Qt.Orientation.Horizontal);self.frost.setRange(45,96);row.addWidget(self.frost,1);self.amount=QLabel();self.amount.setMinimumWidth(48);row.addWidget(self.amount);card_layout.addLayout(row)
        self.sample=QLabel('Aa 　目前功能清楚可見\n外觀不會改變原本的按鍵與配置');self.sample.setWordWrap(True);self.sample.setMinimumHeight(110);card_layout.addWidget(self.sample)
        self.state=QLabel();self.state.setWordWrap(True);card_layout.addWidget(self.state);layout.addWidget(card)
        buttons=QHBoxLayout();reset=QPushButton('恢復預設外觀');reset.clicked.connect(lambda:owner._glass_theme.save(accent='#8b9dff',light=False,frost=78,native_blur=True));buttons.addWidget(reset)
        preview=QPushButton('顯示浮動面板');preview.clicked.connect(lambda:owner._expanded_overlay.set_enabled(True));buttons.addWidget(preview);buttons.addStretch();layout.addLayout(buttons);layout.addStretch()
        self.presets.currentIndexChanged.connect(self.preset);self.custom.clicked.connect(self.pick)
        self.light.toggled.connect(lambda value:owner._glass_theme.save(light=value));self.blur.toggled.connect(lambda value:owner._glass_theme.save(native_blur=value))
        self.frost.valueChanged.connect(lambda v:self.amount.setText(str(v)+'%'));self.frost.sliderReleased.connect(lambda:owner._glass_theme.save(frost=self.frost.value()))
    def preset(self,index):
        value=self.presets.itemData(index)
        if value:self.owner._glass_theme.save(accent=value)
    def pick(self):
        value=QColorDialog.getColor(QColor(preferences(self.owner._config)['accent']),self,'選擇主題顏色')
        if value.isValid():self.owner._glass_theme.save(accent=value.name())
    def sync(self):
        s=preferences(self.owner._config);c=colors(self.owner._config)
        for widget in (self.presets,self.light,self.blur,self.frost):widget.blockSignals(True)
        index=self.presets.findData(s['accent']);self.presets.setCurrentIndex(index if index>=0 else self.presets.count()-1)
        self.light.setChecked(s['light']);self.blur.setChecked(s['native_blur']);self.frost.setValue(s['frost']);self.amount.setText(str(s['frost'])+'%')
        for widget in (self.presets,self.light,self.blur,self.frost):widget.blockSignals(False)
        self.sample.setStyleSheet(f'background:{c["selected"]};color:{c["text"]};border:1px solid {c["accent"]};border-radius:12px;padding:16px;font-size:17px;')
        self.state.setText('Windows 毛玻璃已啟用。系統可能依透明效果設定調整呈現。' if getattr(self.owner,'_glass_native',False) else '目前使用相容霧面漸層。Windows 11 22H2 以上可使用系統毛玻璃。')

def install():
    if getattr(app,'_glass_installed',False):return
    app._glass_installed=True
    from speed_editor_glass_overlay import install as overlay_install
    overlay_install()
    from speed_editor_shared_controls import install as shared_install,SharedPage,settings as shared_settings
    shared_install()
    from speed_editor_consistent_ui import install as consistent_install
    from speed_editor_switch_reliability import install as switch_install
    consistent_install();switch_install()
    from speed_editor_extra_editor import install as extra_install
    extra_install()
    previous_init=app.MainWindow.__init__;previous_close=app.MainWindow.closeEvent;previous_style=app._apply_btn_style
    def style_button(button,key,label,config,*args,**kwargs):
        previous_style(button,key,label,config,*args,**kwargs);button.setProperty('glassHardware',True)
        c=colors(config);active=kwargs.get('dial_active',False);configured=config.get('layers',{}).get(args[0] if args else 'default',{}).get('buttons',{}).get(key,{}).get('action','none')!='none'
        button.setStyleSheet(remap(button.styleSheet(),c)+f'QPushButton{{background:{c["selected"] if configured or active else c["surface"]};color:{c["text"]};border:1px solid {c["line"]};padding:0;}} QPushButton:checked{{border:2px solid {c["accent"]};}} QPushButton:hover{{background:{c["raised"]};border-color:{c["accent"]};}}')
    app._apply_btn_style=style_button
    def dial_paint(widget,event):
        from PyQt6.QtWidgets import QApplication
        owner=next((w for w in QApplication.topLevelWidgets() if hasattr(w,'_glass_theme')),None)
        if owner is None:return
        c=colors(owner._config);p=QPainter(widget);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect=widget.rect().adjusted(7,7,-7,-7);p.setBrush(QColor(c['selected'] if widget._active else c['surface']))
        p.setPen(QPen(QColor(c['accent'] if widget._selected else c['line']),3 if widget._selected else 2));p.drawEllipse(rect)
        p.setBrush(Qt.BrushStyle.NoBrush);p.setPen(QPen(QColor(c['accent']),2));p.drawArc(rect.adjusted(10,10,-10,-10),35*16,105*16)
        p.setPen(QColor(c['muted']));font=QFont('Microsoft JhengHei UI');font.setPixelSize(16);p.setFont(font);p.drawText(rect,Qt.AlignmentFlag.AlignCenter,'旋鈕');p.end()
    app.DialCircle.paintEvent=dial_paint
    def init(window,*args,**kwargs):
        previous_init(window,*args,**kwargs)
        window.setWindowTitle(window.windowTitle().replace('加強版 6','加強版 7.2 · 統一滑鼠操作'))
        window.setObjectName('glassMain');window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        tabs=window.centralWidget();window._glass_help=Guide(window);window._glass_appearance=Appearance(window)
        tabs.addTab(window._glass_appearance,'外觀');tabs.addTab(window._glass_help,'使用說明')
        window._shared_page=SharedPage(window);tabs.addTab(window._shared_page,'通用操作')
        window._shared_hint=QLabel();window._shared_hint.setWordWrap(False)
        window._shared_hint.setStyleSheet('font-size:11px;')
        # Use existing status bar space, so the editor keeps its v6 proportions.
        window.statusBar().addPermanentWidget(window._shared_hint)
        window._glass_pass=QCheckBox('面板穿透');window._glass_pass.setChecked(window._expanded_overlay.locked)
        window._glass_pass.setToolTip('勾選：可點到底下的視窗。取消：可拖曳、縮放並操作浮動面板。')
        window._glass_pass.toggled.connect(window._expanded_overlay.set_locked);window.statusBar().addPermanentWidget(window._glass_pass)
        def hint():
            key=shared_settings(window._config)['modifier'].replace('_',' ')
            window._shared_hint.setText('SLIP SRC／DEST＋旋鈕：左右／上下 · '+key+'：通用')
            window._shared_hint.setToolTip(window._shared_page.hint.text())
        window._context.changed.connect(hint);hint()
        window._glass_theme=Theme(window)
        QTimer.singleShot(0,window._glass_theme.apply)
    def close(window,event):
        previous_close(window,event)
        if event.isAccepted() and hasattr(window,'_glass_theme'):window._glass_theme.close()
    def help_page(window):
        window.centralWidget().setCurrentWidget(window._glass_help);window._glass_help.search.setFocus()
    def paint(window,event):paint_surface(window,window._config)
    app.MainWindow.__init__=init;app.MainWindow.closeEvent=close;app.MainWindow.paintEvent=paint
    ux._help=help_page;desktop.show_help=help_page;app.MainWindow._ux_show_help=help_page
