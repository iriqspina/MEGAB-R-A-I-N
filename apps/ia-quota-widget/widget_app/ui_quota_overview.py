"""All returned windows share a single full-width, left-aligned scale."""
import json
from datetime import timezone, timedelta
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import (QApplication,QDialog,QLabel,QPushButton,QScrollArea,QVBoxLayout,
    QHBoxLayout,QWidget,QProgressBar,QComboBox,QFrame,QSizePolicy)
from . import theme, paths
from .formatting import parse_iso,reset_label,age_label
from .quota_focus import duration_label,is_reserve,focus_window,general_windows
from .observed_info import observed_info,observed_sections,balance_evidence_sections
from .provider_brand import brand_pixmap,provider_name

BRT=timezone(timedelta(hours=-3))


def precise(value):
    return '—' if value is None else f'{value:.2f}'.rstrip('0').rstrip('.').replace('.',',')+'%'


def date_brt(value):
    parsed=parse_iso(value)
    return parsed.astimezone(BRT).strftime('%d/%m/%Y %H:%M:%S BRT') if parsed and parsed.tzinfo else 'não informado com fuso'


class QuotaOverview(QDialog):
    def __init__(self,owner,anchor):
        super().__init__(owner)
        self.owner,self.anchor=owner,anchor
        self.setWindowTitle('Cotas IA · comparar todas as barras')
        self.setWindowFlag(Qt.WindowStaysOnTopHint,owner.settings.always_on_top)
        self.root=QVBoxLayout(self)
        self.title=QLabel('Todas as barras · mesma escala de 0 a 100%')
        self.title.setWordWrap(True);self.root.addWidget(self.title)
        actions=QHBoxLayout()
        self.mode=QComboBox();self.mode.addItems(['Usado','Disponível'])
        self.mode.setCurrentIndex(1 if owner.settings.number_mode == 'remaining' else 0)
        self.mode.setAccessibleName('Comparação das barras: usado ou disponível')
        actions.addWidget(self.mode)
        self.refresh_button=QPushButton('↻ Atualizar');self.refresh_button.clicked.connect(owner.manual_refresh)
        self.copy_button=QPushButton('⧉ Copiar');self.copy_button.clicked.connect(self.copy_data)
        actions.addWidget(self.refresh_button);actions.addWidget(self.copy_button);actions.addStretch()
        self.root.addLayout(actions)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.root.addWidget(self.scroll,1)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.close_button=QPushButton('Fechar · Esc');self.close_button.clicked.connect(self.reject);self.root.addWidget(self.close_button)
        self.rows=[];self.bars=[];self.last_signature=None;self.copy_text=''
        self.mode.currentIndexChanged.connect(lambda _:self.refresh(force=True))
        self.refresh()

    def label(self,text,parent_layout):
        label=QLabel(text);label.setTextFormat(Qt.PlainText);label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        parent_layout.addWidget(label);return label

    def bar(self,layout,value,group):
        bar=QProgressBar();bar.setRange(0,10000);bar.setTextVisible(False);bar.setFixedHeight(12)
        bar.setValue(round(value*100) if value is not None else 0)
        bar.setProperty('metric_group',group);bar.setProperty('raw_percent',value)
        bar.setAccessibleName(f'{group}: {precise(value)}'+(' · sem dado' if value is None else ''))
        bar.setToolTip(bar.accessibleName())
        color={'session':'#66afe8','weekly':'#bd9ff0','other':'#7fc7b2','share':'#e1b773','credit':'#92c98c'}.get(group,'#7fc7b2')
        bar.setStyleSheet('QProgressBar{border:0;border-radius:5px;background:#394353;}QProgressBar::chunk{border-radius:5px;background:'+color+';}')
        layout.addWidget(bar);self.bars.append(bar)
        return bar

    def refresh(self,force=False):
        data=[(row,self.owner.store.display(theme.row_source(row)) or {}) for row in self.owner.provider_ids if self.owner.settings.is_visible(row)]
        evidence_versions=[]
        for name in ('account_balance_observed.json','balance_refresh.json'):
            try:evidence_versions.append((paths.DATA_DIR/name).stat().st_mtime_ns)
            except OSError:evidence_versions.append(None)
        signature=json.dumps([data,self.mode.currentIndex(),self.owner.settings.surface_preset,sorted(self.owner._querying),evidence_versions],sort_keys=True,default=str)
        if signature==self.last_signature and not force:return
        old_value=self.scroll.verticalScrollBar().value()
        self.last_signature=signature;self.rows=[];self.bars=[];self.copy_text=''
        body=QWidget();layout=QVBoxLayout(body);layout.setContentsMargins(14,12,14,16);layout.setSpacing(9)
        palette=self.owner._palette();bg=self.owner._preset()['bg']
        self.setStyleSheet(f'QDialog,QScrollArea,QScrollArea>QWidget>QWidget{{background:{bg};}}QLabel{{color:{palette["text"]};font:14px "Segoe UI";}}QPushButton,QComboBox{{padding:7px;background:{bg};color:{palette["text"]};}}')
        self.label('◷ 5 horas  ·  ◷ semana  ·  ◎ cota específica\nPercentuais são proporções da própria cota; não equivalem ao mesmo número de tokens entre empresas.',layout)
        for row,display in data:
            line=QHBoxLayout();logo=QLabel();logo.setPixmap(brand_pixmap(row,24));logo.setFixedSize(26,26);line.addWidget(logo)
            title=QLabel(provider_name(row,self.owner._canonical_labels));title.setStyleSheet('font-size:20px;font-weight:600;');line.addWidget(title);line.addStretch()
            detail=QPushButton('ⓘ Detalhes');detail.setAccessibleName('Detalhes de '+title.text());detail.clicked.connect(lambda checked=False,key=row:self.owner.open_quota_details(key));line.addWidget(detail);layout.addLayout(line)
            state='consultando' if theme.row_source(row) in self.owner._querying else (theme.STATUS_SHORT_LABEL.get(display.get('status')) or display.get('status') or 'aguardando')
            freshness=' · leitura antiga' if display.get('stale') or display.get('status')!='ok' else ''
            text=f'● {state}{freshness} · consulta {date_brt(display.get("fetched_at"))}'
            self.label(text,layout);self.copy_text+='\n'+title.text()+'\n'+text+'\n'
            windows=display.get('windows') or []
            # Spark only shows its own windows; Codex does not duplicate Spark.
            if row=='spark':windows=[w for w in windows if theme.is_spark_window(w)]
            elif row in ('codex','codex_gpt2'):windows=[w for w in windows if not theme.is_spark_window(w)]
            focus=focus_window(general_windows(windows,row))
            for window in windows:
                used=window.get('used_percent');remaining=100-used if used is not None else None
                amount=remaining if self.mode.currentIndex()==1 else used
                kind='Reserva' if is_reserve(window) else 'Cota específica' if ':' in str(window.get('id','')) and str(window.get('id','')).startswith('weekly_scoped') else 'Cota geral'
                duration=duration_label(window);highlight=' · ★ destaque da faixa' if window is focus else ''
                text=f'{window.get("label") or window.get("id")} · {duration} · {kind}{highlight}\n↑ {precise(used)} usado  ·  ↓ {precise(remaining)} disponível'
                self.rows.append(self.label(text,layout))
                group='session' if window.get('duration_minutes')==300 else 'weekly' if window.get('duration_minutes')==10080 else 'other'
                self.bar(layout,amount,group)
                reset=f'↻ {date_brt(window.get("resets_at"))} · {reset_label(window.get("resets_at"))}'
                self.label(reset,layout);self.copy_text+=text+'\n'+reset+'\n'
            if not windows:self.label('— Nenhuma janela retornada nesta leitura.',layout)
            extras=display.get('details') or {}
            for item in extras.get('resets') or []:
                condition='estoque informado; uso sujeito à elegibilidade da conta' if item.get('kind')=='account' else 'disponível agora' if item.get('usable') else 'indisponível agora'
                text=f'♻ {item["title"]} · {item["count"]} restante(s) · '+condition
                if item.get('expires_at'):text+='\n◷ Validade '+date_brt(item['expires_at'])
                self.label(text,layout);self.copy_text+=text+'\n'
            if not extras.get('resets'):self.label('♻ Quantidade de resets: não informada por esta fonte.',layout)
            if extras.get('product_shares'):
                self.label('◉ Participação no consumo semanal · soma das partes, não cota restante',layout)
                for item in extras['product_shares']:
                    text=f'{item["name"]} · {precise(item["percent"])} do consumo';self.label(text,layout);self.bar(layout,item['percent'],'share');self.copy_text+=text+'\n'
            for item in extras.get('financial') or []:
                amount=item.get('amount');unit=item.get('currency','')
                value=f'{unit} {amount:,.2f}'.replace(',',' ').replace('.',',') if amount is not None else 'não informado pela consulta'
                text=f'$ {item.get("title","Saldo")} · {value}\n{item.get("note","")}'
                if item.get('expires_at'):text+='\n◷ Expira '+date_brt(item['expires_at'])
                self.label(text,layout);self.copy_text+=text+'\n'
                total=item.get('total')
                if isinstance(total,(int,float)) and total>0 and amount is not None:
                    self.bar(layout,min(100,max(0,amount/total*100)),'credit')
            for note in extras.get('notes') or []:
                self.label('ℹ '+note,layout);self.copy_text+='ℹ '+note+'\n'
            if row=='zai' and not extras.get('financial'):
                self.label('$ Saldo monetário: não exposto pelo leitor de cotas. Zero não é presumido.',layout)
            for heading,text in balance_evidence_sections(row):
                self.label(heading+'\n'+text,layout);self.copy_text+=heading+'\n'+text+'\n'
            if row=='claude':
                toggle=QPushButton('📷 Evidência dos prints ▸');toggle.setCheckable(True);layout.addWidget(toggle)
                evidence=QWidget();el=QVBoxLayout(evidence);el.setContentsMargins(0,0,0,0)
                for heading,text in observed_sections(observed_info(row)):self.label(heading+'\n'+text,el)
                evidence.hide();toggle.toggled.connect(evidence.setVisible);layout.addWidget(evidence)
            separator=QFrame();separator.setFrameShape(QFrame.HLine);layout.addWidget(separator)
        layout.addStretch();old=self.scroll.takeWidget()
        if old is not None:old.deleteLater()
        self.scroll.setWidget(body);self.scroll.verticalScrollBar().setValue(old_value)
        self.refresh_button.setEnabled(not self.owner._manual_refresh_locked and not self.owner._querying)

    def copy_data(self):
        QApplication.clipboard().setText('Cotas IA · '+self.mode.currentText()+'\n'+self.copy_text)
        self.copy_button.setText('✓ Copiado');QTimer.singleShot(1800,self,lambda:self.copy_button.setText('⧉ Copiar'))

    def clamp(self):
        area=(self.anchor.screen() or self.owner.screen()).availableGeometry()
        frame=self.frameGeometry();dx=area.left()-frame.left() if frame.left()<area.left() else min(0,area.right()-frame.right())
        dy=area.top()-frame.top() if frame.top()<area.top() else min(0,area.bottom()-frame.bottom())
        if dx or dy:self.move(self.pos()+QPoint(dx,dy))

    def open_at_anchor(self):
        area=(self.anchor.screen() or self.owner.screen()).availableGeometry()
        self.setMaximumSize(max(300,area.width()-40),max(200,area.height()-80))
        self.resize(min(760,self.maximumWidth()),min(820,self.maximumHeight()))
        self.move(area.center()-self.rect().center());self.show();self.clamp();QTimer.singleShot(0,self,self.clamp);QTimer.singleShot(50,self,self.clamp)

    def done(self,result):
        super().done(result)
        self.owner.raise_();self.owner.activateWindow()
