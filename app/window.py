from __future__ import annotations

import random

from PyQt6.QtCore import QTimer, Qt, QUrl
from PyQt6.QtGui import QColor, QPalette, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .dialogs import SettingsDialog
from .downloads import (
    build_download_headers,
    extract_share_url,
    get_preview_url,
    get_resource_count,
    normalize_download_url,
)
from .state import AppState, THEMES, mix_color, rgba_color
from .workers import DownloadThread, ParseThread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.parse_thread = None
        self.download_thread = None
        self.cover_reply = None
        self.current_result = None
        self.pending_result = None
        self.pending_error = None
        self.progress_val = 0
        self.is_video = False
        self.download_target = ""
        self.cover_loader = QNetworkAccessManager(self)
        bg_color = QApplication.palette().color(QPalette.ColorRole.Window)
        AppState.is_dark_mode = bg_color.lightness() < 128

        self.init_ui()
        self.apply_theme()
        QTimer.singleShot(500, self.check_clipboard)

    def init_ui(self):
        self.setWindowTitle("✨ 萌趣提取器")
        self.resize(650, 560)
        self.setMinimumSize(580, 500)

        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(35, 20, 35, 30)

        top_bar = QHBoxLayout()
        self.quote_label = QLabel(AppState.get_new_quote())
        self.quote_label.setObjectName("quoteLabel")
        top_bar.addWidget(self.quote_label)
        top_bar.addStretch(1)

        self.settings_btn = QPushButton("🪄 设置")
        self.settings_btn.setObjectName("topSettingsBtn")
        self.settings_btn.setFixedSize(92, 34)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.settings_btn.clicked.connect(self.open_settings)
        top_bar.addWidget(self.settings_btn)
        main_layout.addLayout(top_bar)
        main_layout.addSpacing(10)

        self.glass_card = QFrame()
        self.glass_card.setObjectName("glassCard")
        self.glass_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(35)
        self.shadow.setOffset(0, 10)
        self.glass_card.setGraphicsEffect(self.shadow)

        card_layout = QVBoxLayout(self.glass_card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(20)
        card_layout.addStretch(1)

        self.url_input = QLineEdit()
        self.url_input.setObjectName("urlInput")
        self.url_input.setPlaceholderText("🎀 在这里粘贴链接哟 (或复制链接自动填入)")
        self.url_input.setFixedHeight(55)

        self.clear_btn = QPushButton("🧹")
        self.clear_btn.setObjectName("clearBtn")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setFixedSize(35, 35)
        self.clear_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.clear_btn.setToolTip("一键魔法清空")
        self.clear_btn.clicked.connect(self.clear_input_box)

        input_inner_layout = QHBoxLayout(self.url_input)
        input_inner_layout.setContentsMargins(0, 0, 10, 0)
        input_inner_layout.addStretch(1)
        input_inner_layout.addWidget(self.clear_btn)
        card_layout.addWidget(self.url_input)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        card_layout.addWidget(self.progress_bar)

        self.parse_btn = QPushButton("🚀 施展魔法解析")
        self.parse_btn.setObjectName("parseBtn")
        self.parse_btn.setFixedHeight(55)
        self.parse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.parse_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.parse_btn.clicked.connect(self.start_parsing)
        card_layout.addWidget(self.parse_btn)

        self.result_card = QFrame()
        self.result_card.setObjectName("resultCard")
        self.result_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.result_card.hide()

        rc_layout = QHBoxLayout(self.result_card)
        rc_layout.setContentsMargins(15, 15, 15, 15)
        rc_layout.setSpacing(15)

        self.cover_label = QLabel("🖼")
        self.cover_label.setObjectName("coverLabel")
        self.cover_label.setFixedSize(85, 85)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rc_layout.addWidget(self.cover_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        self.title_label = QLabel("")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label)

        self.author_label = QLabel("")
        self.author_label.setObjectName("authorLabel")
        info_layout.addWidget(self.author_label)

        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(8)

        self.tag_type = QLabel("")
        self.tag_quality = QLabel("")
        self.tag_extra = QLabel("")
        for tag in (self.tag_type, self.tag_quality, self.tag_extra):
            tag.setObjectName("tagLabel")
            tags_layout.addWidget(tag)

        tags_layout.addStretch(1)
        info_layout.addLayout(tags_layout)

        rc_layout.addLayout(info_layout)
        card_layout.addWidget(self.result_card)

        self.download_btn = QPushButton("")
        self.download_btn.setObjectName("downloadBtn")
        self.download_btn.setFixedHeight(55)
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.download_btn.hide()
        self.download_btn.clicked.connect(self.do_download)
        card_layout.addWidget(self.download_btn)

        self.download_progress_bar = QProgressBar()
        self.download_progress_bar.setObjectName("downloadProgressBar")
        self.download_progress_bar.setFixedHeight(6)
        self.download_progress_bar.setTextVisible(False)
        self.download_progress_bar.setRange(0, 100)
        self.download_progress_bar.setValue(0)
        self.download_progress_bar.hide()
        card_layout.addWidget(self.download_progress_bar)

        card_layout.addStretch(1)
        main_layout.addWidget(self.glass_card)

        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)

    def clear_input_box(self):
        self.progress_timer.stop()
        self.pending_result = None
        self.pending_error = None
        self.current_result = None
        self.abort_cover_loading()
        self.url_input.clear()
        self.progress_bar.hide()
        self.download_progress_bar.hide()
        self.download_progress_bar.setValue(0)
        self.result_card.hide()
        self.download_btn.hide()
        self.download_btn.setEnabled(True)
        self.set_cover_placeholder("🖼")
        self.parse_btn.setEnabled(True)
        self.parse_btn.setText("🚀 施展魔法解析")
        self.url_input.setFocus()

    def check_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        share_url = extract_share_url(text)
        if share_url and not self.url_input.text():
            self.url_input.setText(share_url)
            self.parse_btn.setText("✨ 发现链接！点我立刻解析")
            self.url_input.setStyleSheet(self.url_input.styleSheet() + "border: 2px solid #FFD700;")
            QTimer.singleShot(800, self.apply_theme)

    def open_settings(self):
        AppState.refresh_bili_cookies()
        dialog = SettingsDialog(self)
        dialog.theme_changed.connect(self.apply_theme)
        geometry = dialog.geometry()
        geometry.moveCenter(self.geometry().center())
        dialog.setGeometry(geometry)
        dialog.exec()
        if self.current_result is not None:
            self.populate_result_card(self.current_result)

    def apply_theme(self):
        mode = "dark" if AppState.is_dark_mode else "light"
        theme_data = THEMES[AppState.current_theme][mode]
        accent = theme_data["accent"]
        bg_gradient = theme_data["bg"]
        dl_accent = THEMES["薄荷绿" if AppState.current_theme != "薄荷绿" else "奶昔橘"][mode]["accent"]
        accent_idle = accent
        accent_hover = mix_color(accent, "#FFFFFF", 0.10 if not AppState.is_dark_mode else 0.14)
        accent_pressed = mix_color(accent, "#FFFFFF", 0.22 if not AppState.is_dark_mode else 0.24)
        dl_idle = dl_accent
        dl_hover = mix_color(dl_accent, "#FFFFFF", 0.10 if not AppState.is_dark_mode else 0.14)
        dl_pressed = mix_color(dl_accent, "#FFFFFF", 0.22 if not AppState.is_dark_mode else 0.24)

        if AppState.is_dark_mode:
            glass_bg = "rgba(35, 35, 40, 0.7)"
            glass_border = "rgba(255, 255, 255, 0.15)"
            text_color = "#E5E5E5"
            sub_text_color = "#AAAAAA"
            input_bg = "rgba(15, 15, 20, 0.6)"
            shadow_color = QColor(0, 0, 0, 180)
            card_bg = "rgba(0, 0, 0, 0.3)"
            cover_bg = "rgba(255, 255, 255, 0.1)"
            tag_bg = "rgba(255, 255, 255, 0.08)"
        else:
            glass_bg = "rgba(255, 255, 255, 0.65)"
            glass_border = "rgba(255, 255, 255, 0.95)"
            text_color = "#333333"
            sub_text_color = "#777777"
            input_bg = "rgba(255, 255, 255, 0.85)"
            shadow_color = QColor(accent)
            shadow_color.setAlpha(60)
            card_bg = "rgba(255, 255, 255, 0.6)"
            cover_bg = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {accent}44, stop:1 {accent}11)"
            tag_bg = "rgba(0, 0, 0, 0.05)"

        top_btn_bg = rgba_color(accent_idle, 36 if not AppState.is_dark_mode else 82)
        top_btn_hover_bg = rgba_color(accent_hover, 56 if not AppState.is_dark_mode else 106)
        top_btn_pressed_bg = rgba_color(accent_pressed, 78 if not AppState.is_dark_mode else 128)
        clear_hover_bg = rgba_color(accent, 38 if not AppState.is_dark_mode else 54)
        clear_pressed_bg = rgba_color(accent, 72 if not AppState.is_dark_mode else 94)

        self.shadow.setColor(shadow_color)
        self.quote_label.setText(AppState.get_new_quote())

        self.setStyleSheet(
            f"""
            QWidget#centralWidget {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {bg_gradient}); }}
            QFrame#glassCard {{
                background-color: {glass_bg};
                border: 1.5px solid transparent;
                border-top: 1.5px solid {glass_border};
                border-left: 1.5px solid {glass_border};
                border-radius: 30px;
            }}
            QLabel#quoteLabel {{ color: {accent}; font-size: 16px; font-weight: 800; background: transparent; }}
            QPushButton#topSettingsBtn {{
                background-color: {top_btn_bg};
                color: {accent_idle};
                border: 1px solid transparent;
                border-radius: 16px;
                font-weight: bold;
                font-size: 14px;
                padding: 0 14px;
            }}
            QPushButton#topSettingsBtn:hover {{ background-color: {top_btn_hover_bg}; color: {accent_hover}; border: 1px solid transparent; }}
            QPushButton#topSettingsBtn:pressed {{ background-color: {top_btn_pressed_bg}; color: {accent_pressed}; border: 1px solid transparent; }}
            QLineEdit#urlInput {{
                background-color: {input_bg};
                border: 2px solid transparent;
                border-radius: 27px;
                padding: 0px 45px 0px 25px;
                color: {text_color};
                font-size: 15px;
            }}
            QLineEdit#urlInput:focus {{ border: 2px solid {accent}; }}
            QPushButton#clearBtn {{ background-color: transparent; border: none; border-radius: 16px; color: {sub_text_color}; font-size: 18px; padding: 0px; }}
            QPushButton#clearBtn:hover {{ background-color: {clear_hover_bg}; color: {accent}; }}
            QPushButton#clearBtn:pressed {{ background-color: {clear_pressed_bg}; color: {accent_pressed}; }}
            QProgressBar#progressBar {{ background-color: {input_bg}; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ background-color: {accent}; border-radius: 3px; }}
            QProgressBar#downloadProgressBar {{ background-color: {input_bg}; border: none; border-radius: 3px; }}
            QProgressBar#downloadProgressBar::chunk {{ background-color: {dl_accent}; border-radius: 3px; }}
            QPushButton#parseBtn {{ background-color: {accent_idle}; color: white; border: 1px solid transparent; border-radius: 27px; font-size: 16px; font-weight: bold; padding: 0 20px; }}
            QPushButton#parseBtn:hover {{ background-color: {accent_hover}; border: 1px solid transparent; }}
            QPushButton#parseBtn:pressed {{ background-color: {accent_pressed}; border: 1px solid transparent; }}
            QPushButton#parseBtn:disabled {{ background-color: {input_bg}; color: gray; border: 1px solid transparent; }}
            QPushButton#downloadBtn {{ background-color: {dl_idle}; color: white; border: 1px solid transparent; border-radius: 27px; font-size: 16px; font-weight: bold; padding: 0 20px; }}
            QPushButton#downloadBtn:hover {{ background-color: {dl_hover}; border: 1px solid transparent; }}
            QPushButton#downloadBtn:pressed {{ background-color: {dl_pressed}; border: 1px solid transparent; }}
            QFrame#resultCard {{ background-color: {card_bg}; border-radius: 18px; }}
            QLabel#coverLabel {{ background: {cover_bg}; border-radius: 12px; font-size: 40px; }}
            QLabel#titleLabel {{ color: {text_color}; font-size: 15px; font-weight: bold; }}
            QLabel#authorLabel {{ color: {sub_text_color}; font-size: 12px; }}
            QLabel#tagLabel {{ background-color: {tag_bg}; color: {accent}; font-size: 11px; font-weight: bold; padding: 4px 8px; border-radius: 6px; }}
            """
        )

    def start_parsing(self):
        AppState.refresh_bili_cookies()
        raw_text = self.url_input.text().strip()
        share_url = extract_share_url(raw_text)
        if share_url is None:
            self.url_input.setPlaceholderText("🎀 请粘贴完整分享链接后再来施展魔法哟~")
            return

        self.url_input.setText(share_url)

        if self.parse_thread is not None and self.parse_thread.isRunning():
            return

        self.pending_result = None
        self.pending_error = None
        self.current_result = None
        self.abort_cover_loading()
        self.parse_btn.setEnabled(False)
        self.download_btn.hide()
        self.download_btn.setEnabled(True)
        self.download_progress_bar.hide()
        self.download_progress_bar.setValue(0)
        self.result_card.hide()

        self.progress_val = 0
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_timer.start(30)

        self.parse_thread = ParseThread(share_url, self)
        self.parse_thread.result_ready.connect(self.on_parse_success)
        self.parse_thread.error_occurred.connect(self.on_parse_error)
        self.parse_thread.finished.connect(self.on_parse_thread_finished)
        self.parse_thread.start()

    def update_progress(self):
        if self.pending_result is not None or self.pending_error is not None:
            self.progress_timer.stop()
            self.progress_bar.setValue(100)
            QTimer.singleShot(180, self.finish_parsing)
            return

        if self.progress_val < 85:
            self.progress_val += random.randint(1, 3)
        elif self.progress_val < 95:
            self.progress_val += random.randint(0, 1)

        self.progress_bar.setValue(self.progress_val)

        dots = "." * ((self.progress_val // 10) % 4)
        if self.progress_val < 50:
            self.parse_btn.setText(f"🐾 骑着小黄车赶去服务器{dots}")
        else:
            self.parse_btn.setText(f"✨ 魔法阵正在全力提取{dots}")

        if self.progress_val >= 95:
            self.progress_timer.stop()
            if self.pending_result is not None or self.pending_error is not None:
                QTimer.singleShot(120, self.finish_parsing)

    def finish_parsing(self):
        self.progress_bar.setValue(100)
        QTimer.singleShot(200, self.progress_bar.hide)
        self.parse_btn.setEnabled(True)
        self.parse_btn.setText("🔁 换个链接，重新魔法")

        if self.pending_error is not None:
            self.abort_cover_loading()
            self.set_cover_placeholder("⚠️")
            self.title_label.setText("这次解析没有成功")
            self.author_label.setText(self.pending_error)
            self.tag_type.setText("❌ 失败")
            self.tag_quality.setText("请换一个链接")
            self.tag_extra.setText("")
            self.result_card.show()
            self.download_btn.hide()
            self.pending_error = None
            return

        if self.pending_result is not None:
            self.populate_result_card(self.pending_result)
            self.pending_result = None

    def on_parse_success(self, result: dict):
        self.pending_result = result
        self.pending_error = None
        if not self.progress_timer.isActive():
            self.finish_parsing()

    def on_parse_error(self, message: str):
        self.pending_result = None
        self.pending_error = message or "解析失败"
        if not self.progress_timer.isActive():
            self.finish_parsing()

    def on_parse_thread_finished(self):
        if self.parse_thread is not None:
            self.parse_thread.deleteLater()
            self.parse_thread = None

    def abort_cover_loading(self):
        if self.cover_reply is not None:
            self.cover_reply.abort()
            self.cover_reply.deleteLater()
            self.cover_reply = None

    def set_cover_placeholder(self, emoji: str):
        self.cover_label.clear()
        self.cover_label.setPixmap(QPixmap())
        self.cover_label.setText(emoji)

    def load_cover_preview(self, image_url: str, fallback_emoji: str):
        self.abort_cover_loading()
        self.set_cover_placeholder(fallback_emoji)
        if not image_url:
            return

        normalized_url = normalize_download_url(image_url)
        request = QNetworkRequest(QUrl(normalized_url))
        for header_name, header_value in build_download_headers(normalized_url).items():
            request.setRawHeader(header_name.encode("utf-8"), header_value.encode("utf-8"))
        self.cover_reply = self.cover_loader.get(request)
        self.cover_reply.finished.connect(lambda emoji=fallback_emoji: self.on_cover_preview_finished(emoji))

    def on_cover_preview_finished(self, fallback_emoji: str):
        reply = self.sender()
        if not isinstance(reply, QNetworkReply):
            return

        if self.cover_reply is reply:
            self.cover_reply = None

        if reply.error() != QNetworkReply.NetworkError.NoError:
            reply.deleteLater()
            self.set_cover_placeholder(fallback_emoji)
            return

        pixmap = QPixmap()
        pixmap.loadFromData(reply.readAll())
        reply.deleteLater()

        if pixmap.isNull():
            self.set_cover_placeholder(fallback_emoji)
            return

        scaled_pixmap = pixmap.scaled(
            self.cover_label.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.cover_label.clear()
        self.cover_label.setPixmap(scaled_pixmap)

    def populate_result_card(self, result: dict):
        self.current_result = result
        self.is_video = bool(result.get("video_url"))
        author_name = (result.get("author") or {}).get("name") or "未知作者"
        resource_count = get_resource_count(result)
        image_count = len(result.get("images", []))
        preview_url = get_preview_url(result)
        quality_label = result.get("video_quality_label") or "无水印资源"

        self.title_label.setText(result.get("title") or "未命名资源")
        self.author_label.setText(f"发布者：{author_name}")

        if self.is_video:
            fallback_emoji = random.choice(["🎬", "🖼", "📱", "🎞️"])
            self.tag_type.setText("🎬 视频")
            self.tag_quality.setText(f"✨ {quality_label}")
            self.download_btn.setText(
                random.choice(
                    [
                        "🖼 视频已经准备好啦，点我抱走",
                        "🎁 高清视频已就绪，点我下载",
                    ]
                )
            )
        else:
            fallback_emoji = random.choice(["🖼️", "📷", "🗂", "🎨"])
            self.tag_type.setText("🖼️ 图文")
            self.tag_quality.setText("✨ 原图资源")
            self.download_btn.setText(
                random.choice(
                    [
                        f"🖼️ 已整理 {image_count or resource_count} 份图片资源，点我下载",
                        f"📷 图集已就绪，共 {image_count or resource_count} 项内容",
                    ]
                )
            )

        self.tag_extra.setText(f"📦 共 {resource_count} 项资源")
        self.download_target = f"{resource_count} 项资源"
        self.load_cover_preview(preview_url, fallback_emoji)
        self.result_card.show()
        self.download_btn.setVisible(resource_count > 0)
        self.download_btn.setEnabled(resource_count > 0)

    def do_download(self):
        if not self.current_result:
            return

        if self.download_thread is not None and self.download_thread.isRunning():
            return

        resource_count = get_resource_count(self.current_result)
        if resource_count == 0:
            self.download_btn.hide()
            return

        self.download_btn.setText(f"💾 正在保存到 {AppState.save_path.name}...")
        self.download_btn.setEnabled(False)
        self.download_progress_bar.setValue(0)
        self.download_progress_bar.show()

        self.download_thread = DownloadThread(AppState.save_path, self.current_result, self)
        self.download_thread.progress_changed.connect(self.on_download_progress)
        self.download_thread.finished_ok.connect(self.on_download_finished)
        self.download_thread.error_occurred.connect(self.on_download_error)
        self.download_thread.finished.connect(self.on_download_thread_finished)
        self.download_thread.start()

    def on_download_progress(self, progress: int, status_text: str):
        self.download_progress_bar.setValue(max(0, min(progress, 100)))
        self.download_btn.setText(f"💾 {status_text}")

    def on_download_finished(self, saved_files: list):
        saved_count = len(saved_files)
        self.download_progress_bar.setValue(100)
        self.download_btn.setEnabled(True)
        self.download_btn.setText(f"✨ 已保存 {saved_count} 项到 {AppState.save_path.name}")
        QTimer.singleShot(1200, self.download_progress_bar.hide)

    def on_download_error(self, message: str):
        self.download_progress_bar.hide()
        self.download_progress_bar.setValue(0)
        self.download_btn.setEnabled(True)
        self.download_btn.setText("⚠️ 保存失败，点我再试一次")
        self.author_label.setText(message or "资源保存失败")

    def on_download_thread_finished(self):
        if self.download_thread is not None:
            self.download_thread.deleteLater()
            self.download_thread = None

    def closeEvent(self, event):
        self.progress_timer.stop()
        self.abort_cover_loading()
        super().closeEvent(event)
