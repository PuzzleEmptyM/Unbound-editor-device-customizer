"""Configurable glass surfaces. Native Acrylic is optional; no global OS settings."""
import copy,ctypes,os,re,sys
from PyQt6.QtCore import Qt,QObject,QEvent,QTimer,QRectF
from PyQt6.QtGui import QColor,QPainter,QLinearGradient,QRadialGradient,QPalette
from PyQt6.QtWidgets import QApplication,QWidget,QComboBox
import app,config as cfg
import speed_editor_context as context

DEFAULTS={'accent':'#8b9dff','light':False,'frost':78,'native_blur':True}
PRESETS=[('霧藍','#8b9dff'),('薄荷','#54cfb8'),('薰衣草','#b098f0'),('玫瑰','#ee9abc'),('琥珀','#e4b86b'),('冰川','#68c8e9')]

def preferences(config):
    saved=context.preferences(config).get('appearance',{})
    result={**DEFAULTS,**(saved if isinstance(saved,dict) else {})}
    if not isinstance(result['accent'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',result['accent']):result['accent']=DEFAULTS['accent']
    try:result['frost']=max(45,min(96,int(result['frost'])))
    except (TypeError,ValueError):result['frost']=78
    result['light']=bool(result['light']);result['native_blur']=bool(result['native_blur'])
    return result

def mix(a,b,ratio):
    a,b=QColor(a),QColor(b)
    return QColor(*(round(x+(y-x)*ratio) for x,y in zip(a.getRgb()[:3],b.getRgb()[:3]))).name()

def colors(config):
    s=preferences(config);a=s['accent'];light=s['light']
    return {'accent':a,'base':mix('#edf1f7' if light else '#0b1220',a,.12),
            'surface':mix('#f8faff' if light else '#172333',a,.12),
            'raised':mix('#ffffff' if light else '#263449',a,.15),
            'line':mix('#afb9ca' if light else '#455269',a,.23),
            'text':'#18253b' if light else '#eef3ff','muted':'#526077' if light else '#b1bed5',
            'selected':mix('#d2daf2' if light else '#293450',a,.35),'disabled':'#7b889c',
            'solid':mix(a,'#162137',.50 if light else .34),'frost':s['frost'],'light':light}

def rgba(color,alpha):
    c=QColor(color);return f'rgba({c.red()},{c.green()},{c.blue()},{int(alpha)})'

def remap(style,c):
    backgrounds={'#080d18','#0a1020','#0b1322','#0e1729','#0f172a','#10172a','#111827','#111c31','#141c30','#142039','#162137','#172238','#1e293b','#1e2d50','#23334e','#1a2540','#243260','#0f1525','#162040','#131c33'}
    lines={'#2b3b58','#2d3f6e','#2d4062','#334155','#3a4d6b','#3d5080','#405779','#455879','#4b617f','#516685'}
    muted={'#64748b','#63738b','#7f95b6','#94a3b8','#94aaca','#95a9c6','#9eb0cc','#a9c2e5','#acc0df'}
    accents={'#4338ca','#4f46e5','#5248bf','#5b21b6','#6366f1','#6558ef','#818cf8','#2b4080','#4c1d95','#3730a3'}
    bright={'#c7d2fe','#cbdaf0','#dce7fa','#e2e8f0','#e5edff','#ecf2ff','#eef3ff','#f2f6fd','#ffffff','#cbd5e1','#e0e7ff'}
    def replace(m):
        value=m.group().lower()
        if value in backgrounds:return rgba(c['surface'],220)
        if value in lines:return c['line']
        if value in muted:return c['muted']
        if value in accents:return c['solid']
        if value in bright:return c['text']
        return value
    return re.sub(r'#[0-9a-fA-F]{6}\b',replace,style)

def stylesheet(c):
    surface=rgba(c['surface'],218);raised=rgba(c['raised'],235)
    return f'''
      QWidget {{color:{c['text']};font-family:"Microsoft JhengHei UI","Segoe UI";font-size:13px;}}
      QTabWidget > QWidget {{background:transparent;}}
      QMainWindow#glassMain,QWidget#floatingGuide {{background:transparent;}}
      QDialog,QMenu {{background:{c['base']};}}
      QLabel {{background:transparent;}}
      QTabWidget::pane {{background:{rgba(c['base'],175)};border:1px solid {c['line']};border-radius:13px;}}
      QTabBar::tab {{background:{surface};border:1px solid {c['line']};border-radius:9px;padding:9px 20px;margin:4px 3px;color:{c['muted']};}}
      QTabBar::tab:selected {{background:{c['selected']};color:{c['text']};border-color:{c['accent']};}}
      QFrame#contextHeader,QFrame#contextCard,QGroupBox,QFrame#glassCard {{background:{surface};border:1px solid {c['line']};border-radius:14px;}}
      QGroupBox {{margin-top:14px;padding:15px;}} QGroupBox::title {{subcontrol-origin:margin;left:18px;padding:0 6px;color:{c['muted']};}}
      QPushButton {{background:{raised};border:1px solid {c['line']};border-radius:8px;padding:7px 12px;}}
      QPushButton:hover {{background:{c['selected']};border-color:{c['accent']};}}
      QPushButton:pressed,QPushButton:checked {{background:{c['selected']};border-color:{c['accent']};}}
      QPushButton:disabled {{color:{c['disabled']};background:{surface};}}
      QPushButton#contextPrimary,QPushButton#glassPrimary {{background:{c['solid']};color:#ffffff;border-color:{c['accent']};}}
      QPushButton#contextAuto:checked {{background:{c['selected']};border-color:{c['accent']};}}
      QLineEdit,QSpinBox,QComboBox {{background:{raised};border:1px solid {c['line']};border-radius:7px;padding:7px;color:{c['text']};selection-background-color:{c['solid']};selection-color:white;}}
      QComboBox::drop-down {{width:24px;border:0;}}
      QComboBox QAbstractItemView {{background:{c['surface']};color:{c['text']};selection-background-color:{c['selected']};selection-color:{c['text']};}}
      QListWidget,QTextBrowser {{background:{surface};border:1px solid {c['line']};border-radius:12px;padding:5px;}}
      QListWidget::item {{padding:9px 10px;margin:2px;border-radius:7px;}}
      QListWidget::item:selected {{background:{c['selected']};color:{c['text']};}}
      QScrollArea,QGraphicsView {{background:transparent;border:0;}}
      QCheckBox {{background:transparent;spacing:8px;}}
      QCheckBox::indicator {{width:15px;height:15px;border:1px solid {c['line']};border-radius:4px;background:{c['surface']};}}
      QCheckBox::indicator:checked {{background:{c['solid']};border:2px solid {c['accent']};}}
      QSlider::groove:horizontal {{height:5px;background:{c['line']};border-radius:2px;}}
      QSlider::sub-page:horizontal {{background:{c['accent']};border-radius:2px;}}
      QSlider::handle:horizontal {{width:15px;margin:-6px 0;border-radius:7px;background:{c['accent']};border:1px solid {c['line']};}}
      QScrollBar:vertical {{width:10px;background:transparent;margin:0;}}
      QScrollBar:horizontal {{height:10px;background:transparent;margin:0;}}
      QScrollBar::handle {{background:{c['line']};border-radius:5px;min-height:24px;min-width:24px;}}
      QScrollBar::add-line,QScrollBar::sub-line {{width:0;height:0;}}
      QScrollBar::add-page,QScrollBar::sub-page {{background:transparent;}}
      QSplitter::handle {{background:{c['line']};width:5px;}}
      QStatusBar {{background:{rgba(c['base'],235)};color:{c['muted']};}}
      QToolTip {{background:{c['surface']};color:{c['text']};border:1px solid {c['accent']};padding:6px;}}
    '''

def paint_surface(widget,config,rounded=False):
    c=colors(config);p=QPainter(widget);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect=QRectF(widget.rect()).adjusted(.5,.5,-.5,-.5)
    gradient=QLinearGradient(rect.topLeft(),rect.bottomRight())
    alpha=round(c['frost']*2.55)
    # An opaque base is retained when the compositor cannot supply real blur.
    native=getattr(widget,'_glass_native',False)
    top,bottom=QColor(c['raised']),QColor(c['base'])
    top.setAlpha(alpha if native else 255);bottom.setAlpha(min(255,alpha+26) if native else 255)
    gradient.setColorAt(0,top);gradient.setColorAt(1,bottom)
    p.setPen(QColor(c['line']) if rounded else Qt.PenStyle.NoPen);p.setBrush(gradient)
    p.drawRoundedRect(rect,16 if rounded else 0,16 if rounded else 0)
    glow=QRadialGradient(rect.width()*.16,0,max(200,rect.width()*.65));tint=QColor(c['accent']);tint.setAlpha(30)
    glow.setColorAt(0,tint);tint.setAlpha(0);glow.setColorAt(1,tint);p.setBrush(glow);p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(rect,16 if rounded else 0,16 if rounded else 0);p.end()

def native_backdrop(widget,config):
    widget._glass_native=False
    if os.name!='nt' or QApplication.platformName()!='windows':return False
    try:
        if sys.getwindowsversion().build<22621:return False
        dwm=ctypes.WinDLL('dwmapi');handle=ctypes.c_void_p(int(widget.winId()))
        fn=dwm.DwmSetWindowAttribute;fn.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint];fn.restype=ctypes.c_long
        s=preferences(config)
        for attr,value in ((20,0 if s['light'] else 1),(33,2),(38,3 if s['native_blur'] else 1)):
            v=ctypes.c_int(value);result=fn(handle,attr,ctypes.byref(v),ctypes.sizeof(v))
        class Margins(ctypes.Structure):_fields_=[(n,ctypes.c_int) for n in ('left','right','top','bottom')]
        margins=Margins(-1,-1,-1,-1);extend=dwm.DwmExtendFrameIntoClientArea
        extend.argtypes=[ctypes.c_void_p,ctypes.POINTER(Margins)];extend.restype=ctypes.c_long
        extended=extend(handle,ctypes.byref(margins))
        widget._glass_native=result==0 and extended==0 and s['native_blur']
    except (OSError,AttributeError,ValueError):pass
    return widget._glass_native

class Theme(QObject):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.applying=False;self.closed=False
        self.original_app_style=QApplication.instance().styleSheet()
        self.original_owner_style=owner.styleSheet()
        self.last='';self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.check_config)
        self.apply();self.timer.start();QApplication.instance().installEventFilter(self)
        QApplication.instance().aboutToQuit.connect(self.close)
    def close(self):
        self.closed=True;self.timer.stop();QApplication.instance().removeEventFilter(self)
    def style_tree(self,root,c):
        widgets=[root]+root.findChildren(QWidget)
        for view in root.findChildren(QWidget):
            editor=getattr(view,'editor',None)
            if isinstance(editor,QWidget):widgets.extend([editor]+editor.findChildren(QWidget))
        seen=set()
        for widget in widgets:
            if id(widget) in seen or widget is self.owner or widget is self.owner._expanded_overlay:continue
            seen.add(id(widget))
            if widget.property('glassHardware'):continue
            original=getattr(widget,'_glass_original_style',None)
            if original is None:original=widget.styleSheet();widget._glass_original_style=original
            if original:widget.setStyleSheet(remap(original,c))
    def eventFilter(self,widget,event):
        if self.closed:return False
        if event.type()==QEvent.Type.Show and isinstance(widget,QWidget) and widget.isWindow() and not self.applying:
            self.style_tree(widget,colors(self.owner._config))
        return False
    def check_config(self):
        if not self.closed and repr(preferences(self.owner._config))!=self.last:self.apply()
    def save(self,**changes):
        candidate=copy.deepcopy(self.owner._config);s=preferences(candidate);s.update(changes)
        candidate['layers']['default'].setdefault('context_switching',{})['appearance']=s
        try:cfg.save(candidate)
        except (OSError,ValueError,TypeError) as error:
            self.owner.statusBar().showMessage('外觀尚未儲存：'+str(error),6000);return False
        self.owner._config['layers']['default']['context_switching']['appearance']=s
        self.apply();return True
    def apply(self):
        if self.applying:return
        self.applying=True
        try:
            owner=self.owner;c=colors(owner._config);self.last=repr(preferences(owner._config))
            # Keep v6 spacing, fonts, card outlines and combo arrows intact.
            QApplication.instance().setStyleSheet(remap(self.original_app_style,c))
            owner.setStyleSheet(remap(self.original_owner_style,c)+'QMainWindow#glassMain{background:transparent;}')
            panel=owner._expanded_overlay;panel.setStyleSheet(stylesheet(c))
            palette=QPalette(QApplication.palette())
            for role,color in ((QPalette.ColorRole.Window,c['base']),(QPalette.ColorRole.Base,c['surface']),
                (QPalette.ColorRole.Text,c['text']),(QPalette.ColorRole.WindowText,c['text']),
                (QPalette.ColorRole.Button,c['raised']),(QPalette.ColorRole.ButtonText,c['text']),
                (QPalette.ColorRole.Highlight,c['selected']),(QPalette.ColorRole.HighlightedText,c['text'])):palette.setColor(role,QColor(color))
            QApplication.instance().setPalette(palette);owner.setPalette(palette);panel.setPalette(palette)
            for root in (owner,panel):
                self.style_tree(root,c)
                for widget in root.findChildren(QComboBox):widget.view().setPalette(palette)
                root.update()
            for view in (owner._ux_grid_scroll,owner._ux_panel_scroll):view.setBackgroundBrush(QColor(c['surface']))
            owner.refresh_button_colors();panel.board.update()
            native_backdrop(owner,owner._config);native_backdrop(panel,owner._config)
            if hasattr(owner,'_glass_appearance'):owner._glass_appearance.sync()
            if hasattr(owner,'_glass_help'):owner._glass_help.render()
        finally:self.applying=False
