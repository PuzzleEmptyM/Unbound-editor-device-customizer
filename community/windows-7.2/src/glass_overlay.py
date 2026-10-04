"""Responsive floating guide with function-first typography and no overlapping dial."""
import math
from PyQt6.QtCore import Qt,QPoint,QRectF,QRect
from PyQt6.QtGui import QColor,QFont,QFontMetrics,QPainter,QPen,QLinearGradient
from PyQt6.QtWidgets import QWidget,QSizePolicy,QPushButton
import speed_editor_expanded_overlay as base
from speed_editor_glass_theme import colors,paint_surface,native_backdrop,rgba

def text_layout(label,rect,show_code=True):
    flags=Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap
    font=QFont('Microsoft JhengHei UI');font.setWeight(QFont.Weight.DemiBold)
    # Sacrifice the original hardware legend before sacrificing function text.
    size=min(19,max(11,round(rect.height()*.24)))
    font.setPixelSize(size)
    with_code=rect.adjusted(5,19,-5,-5);whole=rect.adjusted(5,5,-5,-5)
    def fits(area,text):
        bounds=QFontMetrics(font).boundingRect(QRect(0,0,max(1,int(area.width())),2000),flags,text)
        return bounds.width()<=area.width() and bounds.height()<=area.height()
    code=bool(show_code and rect.width()>=90 and rect.height()>=66 and fits(with_code,label))
    area=with_code if code else whole
    while size>10 and not fits(area,label):size-=1;font.setPixelSize(size)
    visible=label
    while not fits(area,visible) and len(visible)>2:visible=(visible[:-2] if visible.endswith('…') else visible[:-1])+'…'
    return code,font,area,visible,flags

def geometry(board,controls):
    w,h=board.width(),board.height();gap=7
    compact=board.panel.compact.isChecked()
    if compact:
        priority=['STOP_PLAY','IN','OUT','TRIM_IN','TRIM_OUT','JOG','SHTL','SCRL','AUDIO_ONLY','FULL_VIEW','SOURCE','TIMELINE']
        lookup={row[0]:row for row in controls};controls=[lookup[k] for k in priority if k in lookup]
    # Original map at useful landscape proportions; otherwise fill a flowing grid.
    physical=not compact
    if physical:
        source=board.panel.owner.se_widget;rectangles={}
        for key,label,action in controls:
            widget=source._btn_widgets[key];p=widget.mapTo(source,QPoint());rectangles[key]=QRectF(p.x(),p.y(),widget.width(),widget.height())
        dial=source._dial_circle;p=dial.mapTo(source,QPoint());dr=QRectF(p.x(),p.y(),dial.width(),dial.height())
        bounding=QRectF(dr)
        for r in rectangles.values():bounding=bounding.united(r)
        scale=min((w-gap*2)/max(1,bounding.width()),(h-gap*2)/max(1,bounding.height()))
        dx=(w-bounding.width()*scale)/2;dy=(h-bounding.height()*scale)/2
        def mapped(r):return QRectF(dx+(r.x()-bounding.x())*scale,dy+(r.y()-bounding.y())*scale,r.width()*scale,r.height()*scale)
        return [(k,l,a,mapped(rectangles[k])) for k,l,a in controls],mapped(dr),'hardware'
    columns=max(3,min(8,round(math.sqrt(len(controls)*max(1,w)/max(1,h)*.78))))
    if compact:columns=min(6,columns)
    count=math.ceil(len(controls)/columns);cw=(w-gap*(columns+1))/columns;ch=(h-gap*(count+1))/count
    return [(k,l,a,QRectF(gap+(i%columns)*(cw+gap),gap+(i//columns)*(ch+gap),cw,ch)) for i,(k,l,a) in enumerate(controls)],None,'compact' if compact else 'flow'

class Board(QWidget):
    def __init__(self,panel):
        super().__init__(panel);self.panel=panel;self.setMinimumSize(260,210);self.setMouseTracking(True)
        self.hit=[];self.labels=[];self.layout_mode='';self.dial_rect=None
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
    def paintEvent(self,event):
        owner=self.panel.owner;c=colors(owner._config);p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.hit=[];self.labels=[];held=set();bridge=owner._context.bridge
        if bridge:held={getattr(k,'name',str(k)) for k in bridge.cells['_held'].cell_contents}
        if bridge and getattr(bridge,'shared_active',False):held=set(bridge.shared_held)
        cells,self.dial_rect,self.layout_mode=geometry(self,base.rows(owner))
        for key,label,action,r in cells:
            active=key in held;rect=r.adjusted(.5,.5,-.5,-.5)
            fill=QLinearGradient(rect.topLeft(),rect.bottomRight());fill.setColorAt(0,QColor(c['selected'] if active else c['raised']));fill.setColorAt(1,QColor(c['surface']))
            p.setPen(QPen(QColor(c['accent'] if active else c['line']),1.5 if active else .8));p.setBrush(fill);p.drawRoundedRect(rect,9,9)
            code,font,area,text,flags=text_layout(label,r)
            if code:
                legend=QFont('Segoe UI');legend.setPixelSize(9);p.setFont(legend);p.setPen(QColor(c['muted']))
                p.drawText(r.adjusted(4,3,-4,-r.height()+17),Qt.AlignmentFlag.AlignCenter,QFontMetrics(legend).elidedText(key.replace('_',' '),Qt.TextElideMode.ElideRight,int(r.width()-8)))
            p.setFont(font);p.setPen(QColor(c['text'] if action.get('action','none')!='none' else c['muted']));p.drawText(area,flags,text)
            self.hit.append((r,key,label,action));self.labels.append({'key':key,'code':code,'text':text,'area':area})
        if self.dial_rect is not None:
            r=self.dial_rect;d=min(r.width(),r.height())*.86;circle=QRectF(r.center().x()-d/2,r.center().y()-d/2,d,d)
            p.setBrush(QColor(c['surface']));p.setPen(QPen(QColor(c['line']),2));p.drawEllipse(circle)
            p.setPen(QColor(c['accent']));p.drawArc(circle.adjusted(7,7,-7,-7),35*16,105*16)
            code,font,area,text,flags=text_layout('旋鈕\n'+base.dial_caption(owner),circle.adjusted(9,9,-9,-9),False)
            p.setFont(font);p.setPen(QColor(c['text']));p.drawText(area,flags,text)
        p.end()
    def mouseMoveEvent(self,event):
        for r,key,label,action in self.hit:
            if r.contains(event.position()):
                self.setToolTip(label+'\n硬體按鍵：'+key.replace('_',' ')+('\n快捷鍵：'+action['keys'] if action.get('keys') else ''));return
        self.setToolTip('')

def install():
    base.Board=Board
    previous_init=base.Overlay.__init__;previous_resize=base.Overlay.resizeEvent;previous_lock=base.Overlay.set_locked
    def init(panel,*args,**kwargs):
        previous_init(panel,*args,**kwargs);panel.setMinimumSize(360,430)
        panel.title.setMinimumWidth(0);panel.title.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        panel.detail.setMinimumWidth(0);panel.detail.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        panel.hint.setWordWrap(True);panel.opacity.setMaximumWidth(120)
        panel.setToolTip('完整模式保持實體鍵盤排列；滑鼠停留可查看原按鍵名稱。')
        panel.pass_button=QPushButton('穿透：關');panel.pass_button.setCheckable(True)
        panel.pass_button.setToolTip('開啟後可直接點到底下的視窗。從主視窗底部「面板穿透」取消，即可操作面板。')
        panel.header.layout().insertWidget(2,panel.pass_button)
        panel.pass_button.toggled.connect(panel.set_locked)
        panel.set_locked(panel.locked,save=False)
    def paint(panel,event):paint_surface(panel,panel.owner._config,True)
    def resize(panel,event):
        previous_resize(panel,event)
        if hasattr(panel,'board'):panel.board.update()
    def locked(panel,*args,**kwargs):
        result=previous_lock(panel,*args,**kwargs)
        if hasattr(panel,'board'):native_backdrop(panel,panel.owner._config)
        for control in (getattr(panel,'pass_button',None),getattr(panel.owner,'_expanded_lock',None),getattr(panel.owner,'_glass_pass',None)):
            if control is not None:
                control.blockSignals(True);control.setChecked(panel.locked);control.blockSignals(False)
        if hasattr(panel,'pass_button'):panel.pass_button.setText('穿透：開' if panel.locked else '穿透：關')
        return result
    base.Overlay.__init__=init;base.Overlay.paintEvent=paint;base.Overlay.resizeEvent=resize;base.Overlay.set_locked=locked
