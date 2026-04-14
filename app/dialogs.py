from __future__ import annotations

import json
from io import BytesIO

from PyQt6.QtCore import QTimer, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from .state import AppState, THEMES, mix_color, rgba_color


class BiliLoginDialog(QDialog):
    login_succeeded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(320, 380)

        self.manager = QNetworkAccessManager(self)
        self.qrcode_key = ""
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_status)

        self.init_ui()
        self.apply_theme()
        self.fetch_qrcode()

    def init_ui(self):
        self.bg_frame = QFrame(self)
        self.bg_frame.setGeometry(0, 0, 320, 380)
        self.bg_frame.setObjectName("settingsBg")
        self.bg_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 8)
        self.bg_frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.bg_frame)
        layout.setContentsMargins(30, 25, 30, 25)

        self.title_label = QLabel("📱 B站扫码登录")
        self.title_label.setObjectName("settingsTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        layout.addSpacing(10)

        self.qr_label = QLabel("正在生成二维码...")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setFixedSize(200, 200)
        self.qr_label.setStyleSheet("background-color: white; border-radius: 15px; color: #555;")
        layout.addWidget(self.qr_label, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(15)
        self.status_label = QLabel("正在连接 B站 登录服务...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch(1)
        self.close_btn = QPushButton("先不用啦")
        self.close_btn.setObjectName("settingsBtn")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.setFixedHeight(38)
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)

    def apply_theme(self):
        mode = "dark" if AppState.is_dark_mode else "light"
        accent = THEMES[AppState.current_theme][mode]["accent"]
        bg_color = "rgba(40, 40, 45, 0.95)" if AppState.is_dark_mode else "rgba(255, 255, 255, 0.95)"
        text_color = "#E0E0E0" if AppState.is_dark_mode else "#5C4B51"
        accent_idle = accent
        accent_hover = mix_color(accent, "#FFFFFF", 0.10 if not AppState.is_dark_mode else 0.14)
        accent_pressed = mix_color(accent, "#FFFFFF", 0.22 if not AppState.is_dark_mode else 0.24)
        self.setStyleSheet(
            f"""
            QFrame#settingsBg {{ background-color: {bg_color}; border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.2); }}
            QLabel {{ color: {text_color}; font-weight: bold; background: transparent; border: none; font-size: 14px; }}
            QLabel#settingsTitle {{ color: {accent}; font-size: 18px; }}
            QPushButton#settingsBtn {{ background-color: {accent_idle}; color: white; border: 1px solid transparent; border-radius: 15px; padding: 8px; font-weight: bold; }}
            QPushButton#settingsBtn:hover {{ background-color: {accent_hover}; border: 1px solid transparent; }}
            QPushButton#settingsBtn:pressed {{ background-color: {accent_pressed}; border: 1px solid transparent; }}
            """
        )

    def fetch_qrcode(self):
        request = QNetworkRequest(QUrl("https://passport.bilibili.com/x/passport-login/web/qrcode/generate"))
        request.setRawHeader(b"User-Agent", b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        reply = self.manager.get(request)
        reply.finished.connect(self.on_fetch_finished)

    def on_fetch_finished(self):
        reply = self.sender()
        if not isinstance(reply, QNetworkReply):
            return

        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.status_label.setText("⚠️ 二维码生成失败，请稍后重试")
            reply.deleteLater()
            return

        try:
            payload = json.loads(bytes(reply.readAll()).decode("utf-8"))
            if payload.get("code") != 0:
                raise ValueError(payload.get("message") or "二维码生成失败")

            url = payload["data"]["url"]
            self.qrcode_key = payload["data"]["qrcode_key"]

            try:
                import qrcode
            except ModuleNotFoundError:
                self.status_label.setText("⚠️ 缺少 qrcode 依赖，请安装后再扫码")
                reply.deleteLater()
                return

            image = qrcode.make(url)
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            self.qr_label.setPixmap(
                pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
            self.status_label.setText("📱 请使用 B站 App 扫码登录")
            self.poll_timer.start(2000)
        except Exception:
            self.status_label.setText("⚠️ 二维码生成失败，请稍后重试")
        finally:
            reply.deleteLater()

    def poll_status(self):
        if not self.qrcode_key:
            return

        request = QNetworkRequest(
            QUrl(f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={self.qrcode_key}")
        )
        request.setRawHeader(b"User-Agent", b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        reply = self.manager.get(request)
        reply.finished.connect(self.on_poll_finished)

    def on_poll_finished(self):
        reply = self.sender()
        if not isinstance(reply, QNetworkReply):
            return

        if reply.error() != QNetworkReply.NetworkError.NoError:
            reply.deleteLater()
            return

        try:
            payload = json.loads(bytes(reply.readAll()).decode("utf-8"))
            data = payload.get("data", {})
            code = data.get("code")

            if code == 0:
                self.poll_timer.stop()
                cookies = dict(AppState.bili_cookies)
                cookie_list = reply.header(QNetworkRequest.KnownHeaders.SetCookieHeader) or []
                for cookie in cookie_list:
                    key = cookie.name().data().decode()
                    value = cookie.value().data().decode()
                    if key and value:
                        cookies[key] = value

                AppState.save_bili_cookies(cookies)
                self.status_label.setText("🎉 扫码成功，凭证已保存到 cook 文件夹")
                self.login_succeeded.emit()
                QTimer.singleShot(1200, self.accept)
            elif code == 86038:
                self.poll_timer.stop()
                self.status_label.setText("⚠️ 二维码已过期，正在重新生成...")
                self.fetch_qrcode()
            elif code == 86039:
                self.status_label.setText("⏳ 已扫码，请在手机上确认登录")
            elif code == 86101:
                self.status_label.setText("📱 等待扫码中...")
        except Exception:
            pass
        finally:
            reply.deleteLater()

    def closeEvent(self, event):
        self.poll_timer.stop()
        super().closeEvent(event)


class SettingsDialog(QDialog):
    theme_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(460, 500)
        self.theme_buttons: dict[str, QPushButton] = {}
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        self.bg_frame = QFrame(self)
        self.bg_frame.setGeometry(0, 0, 460, 500)
        self.bg_frame.setObjectName("settingsBg")
        self.bg_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 8)
        self.bg_frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.bg_frame)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)

        self.title_label = QLabel("✨ 魔法设置")
        self.title_label.setObjectName("settingsTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("🌓 昼夜模式："))
        self.mode_btn = QPushButton()
        self.mode_btn.setObjectName("settingsBtn")
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mode_btn.setFixedHeight(40)
        self.mode_btn.clicked.connect(self.toggle_mode)
        mode_layout.addWidget(self.mode_btn)
        layout.addLayout(mode_layout)

        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("🎨 主题色彩："))
        for theme_name in THEMES.keys():
            btn = QPushButton()
            btn.setFixedSize(26, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setToolTip(theme_name)
            btn.clicked.connect(lambda checked, t=theme_name: self.change_theme(t))
            self.theme_buttons[theme_name] = btn
            theme_layout.addWidget(btn)
        theme_layout.addStretch(1)
        layout.addLayout(theme_layout)

        cover_layout = QHBoxLayout()
        cover_layout.addWidget(QLabel("🖼 下载封面："))
        self.cover_toggle_btn = QPushButton()
        self.cover_toggle_btn.setObjectName("settingsBtn")
        self.cover_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cover_toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cover_toggle_btn.setFixedHeight(40)
        self.cover_toggle_btn.clicked.connect(self.toggle_cover_download)
        cover_layout.addWidget(self.cover_toggle_btn)
        layout.addLayout(cover_layout)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("📁 独立文件夹："))
        self.folder_toggle_btn = QPushButton()
        self.folder_toggle_btn.setObjectName("settingsBtn")
        self.folder_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folder_toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.folder_toggle_btn.setFixedHeight(40)
        self.folder_toggle_btn.clicked.connect(self.toggle_create_title_folder)
        folder_layout.addWidget(self.folder_toggle_btn)
        layout.addLayout(folder_layout)

        self.tips_label = QLabel("默认都关闭。开启后会把封面加入下载队列，或按标题新建专属文件夹。")
        self.tips_label.setObjectName("tipsLabel")
        self.tips_label.setWordWrap(True)
        layout.addWidget(self.tips_label)

        bili_layout = QHBoxLayout()
        bili_layout.addWidget(QLabel("📱 B站登录凭证："))
        self.bili_status_label = QLabel("✨ 已检测到 cook" if AppState.bili_cookies else "❌ 暂无可用 cookie")
        bili_layout.addWidget(self.bili_status_label)
        bili_layout.addStretch(1)

        self.bili_login_btn = QPushButton("📲 扫码登录")
        self.bili_login_btn.setObjectName("settingsBtn")
        self.bili_login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bili_login_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bili_login_btn.setFixedHeight(40)
        self.bili_login_btn.clicked.connect(self.open_bili_login)
        bili_layout.addWidget(self.bili_login_btn)
        layout.addLayout(bili_layout)

        layout.addWidget(QLabel("💾 魔法存档位置："))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit(str(AppState.save_path))
        self.path_input.setObjectName("settingsInput")
        self.path_input.setReadOnly(True)
        path_layout.addWidget(self.path_input)

        self.browse_btn = QPushButton("📂 更改")
        self.browse_btn.setObjectName("settingsBtn")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.browse_btn.setFixedHeight(40)
        self.browse_btn.clicked.connect(self.choose_directory)
        path_layout.addWidget(self.browse_btn)
        layout.addLayout(path_layout)

        layout.addStretch(1)
        self.close_btn = QPushButton("✨ 完成啦")
        self.close_btn.setObjectName("settingsBtn")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.setFixedHeight(40)
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

        self.refresh_toggle_text()
        self.refresh_mode_text()

    def refresh_mode_text(self):
        self.mode_btn.setText("切换至黑夜 🌙" if not AppState.is_dark_mode else "切换至白天 ☀️")

    def refresh_toggle_text(self):
        self.cover_toggle_btn.setText("开启中 ✨" if AppState.download_cover else "默认关闭")
        self.folder_toggle_btn.setText("开启中 ✨" if AppState.create_title_folder else "默认关闭")

    def open_bili_login(self):
        login_dialog = BiliLoginDialog(self)
        login_dialog.login_succeeded.connect(self.refresh_bili_status)
        geometry = login_dialog.geometry()
        geometry.moveCenter(self.geometry().center())
        login_dialog.setGeometry(geometry)
        login_dialog.exec()
        self.refresh_bili_status()

    def refresh_bili_status(self):
        AppState.refresh_bili_cookies()
        self.bili_status_label.setText("✨ 已检测到 cook" if AppState.bili_cookies else "❌ cook 中暂无可用 cookie")

    def toggle_mode(self):
        AppState.is_dark_mode = not AppState.is_dark_mode
        self.refresh_mode_text()
        self.apply_theme()
        self.theme_changed.emit()

    def change_theme(self, theme_name):
        AppState.current_theme = theme_name
        self.apply_theme()
        self.theme_changed.emit()

    def toggle_cover_download(self):
        AppState.download_cover = not AppState.download_cover
        self.refresh_toggle_text()

    def toggle_create_title_folder(self):
        AppState.create_title_folder = not AppState.create_title_folder
        self.refresh_toggle_text()

    def choose_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择保存文件夹", str(AppState.save_path))
        if dir_path:
            AppState.set_save_path(dir_path)
            self.path_input.setText(str(AppState.save_path))

    def apply_theme(self):
        mode = "dark" if AppState.is_dark_mode else "light"
        accent = THEMES[AppState.current_theme][mode]["accent"]
        bg_color = "rgba(40, 40, 45, 0.95)" if AppState.is_dark_mode else "rgba(255, 255, 255, 0.95)"
        text_color = "#E0E0E0" if AppState.is_dark_mode else "#5C4B51"
        input_bg = "rgba(10, 10, 15, 0.5)" if AppState.is_dark_mode else "rgba(240, 240, 245, 0.8)"
        tips_color = "#B9B9C3" if AppState.is_dark_mode else "#8A7A82"
        accent_idle = accent
        accent_hover = mix_color(accent, "#FFFFFF", 0.10 if not AppState.is_dark_mode else 0.14)
        accent_pressed = mix_color(accent, "#FFFFFF", 0.22 if not AppState.is_dark_mode else 0.24)
        swatch_idle_border = "rgba(255, 255, 255, 0.0)"
        swatch_hover_border = rgba_color(accent, 150 if not AppState.is_dark_mode else 190)
        swatch_selected_border = accent

        self.setStyleSheet(
            f"""
            QFrame#settingsBg {{ background-color: {bg_color}; border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.2); }}
            QLabel {{ color: {text_color}; font-weight: bold; background: transparent; border: none; }}
            QLabel#settingsTitle {{ color: {accent}; font-size: 18px; }}
            QLabel#tipsLabel {{ color: {tips_color}; font-size: 12px; font-weight: 600; }}
            QPushButton#settingsBtn {{ background-color: {accent_idle}; color: white; border: 1px solid transparent; border-radius: 15px; padding: 8px; font-weight: bold; }}
            QPushButton#settingsBtn:hover {{ background-color: {accent_hover}; border: 1px solid transparent; }}
            QPushButton#settingsBtn:pressed {{ background-color: {accent_pressed}; border: 1px solid transparent; }}
            QLineEdit#settingsInput {{ background-color: {input_bg}; color: {text_color}; border: none; border-radius: 15px; padding: 8px 15px; }}
            """
        )

        for theme_name, btn in self.theme_buttons.items():
            swatch_color = THEMES[theme_name]["light"]["accent"]
            border_color = swatch_selected_border if theme_name == AppState.current_theme else swatch_idle_border
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {swatch_color};
                    border-radius: 13px;
                    border: 2px solid {border_color};
                }}
                QPushButton:hover {{
                    border: 2px solid {swatch_hover_border};
                }}
                QPushButton:pressed {{
                    border: 2px solid {swatch_selected_border};
                }}
                """
            )
