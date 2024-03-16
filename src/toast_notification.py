import math
import os
from qtpy.QtGui import QGuiApplication
from qtpy.QtCore import Qt, QPropertyAnimation, QPoint, QTimer, QSize, QMargins, QRect, Signal
from qtpy.QtGui import QPixmap, QIcon, QColor, QFont, QImage, qRgba, QFontMetrics
from qtpy.QtWidgets import QDialog, QPushButton, QLabel, QGraphicsOpacityEffect, QWidget
from .toast_enums import ToastPreset, ToastIcon, ToastPosition, ToastButtonAlignment


class ToastNotification(QDialog):

    # Static attributes
    __maximum_on_screen = 3
    __spacing = 10
    __offset_x = 20
    __offset_y = 45
    __always_on_main_screen = False
    __position = ToastPosition.BOTTOM_RIGHT

    __currently_shown = []
    __queue = []

    # Constants
    __DURATION_BAR_UPDATE_INTERVAL = 10
    __DROP_SHADOW_SIZE = 5
    __SUCCESS_ACCENT_COLOR = QColor('#3E9141')
    __WARNING_ACCENT_COLOR = QColor('#E8B849')
    __ERROR_ACCENT_COLOR = QColor('#BA2626')
    __INFORMATION_ACCENT_COLOR = QColor('#007FFF')
    __DEFAULT_ACCENT_COLOR = QColor('#5C5C5C')
    __DEFAULT_BACKGROUND_COLOR = QColor('#E7F4F9')
    __DEFAULT_TITLE_COLOR = QColor('#000000')
    __DEFAULT_TEXT_COLOR = QColor('#5C5C5C')
    __DEFAULT_ICON_SEPARATOR_COLOR = QColor('#D9D9D9')
    __DEFAULT_CLOSE_BUTTON_COLOR = QColor('#000000')
    __DEFAULT_BACKGROUND_COLOR_DARK = QColor('#292929')
    __DEFAULT_TITLE_COLOR_DARK = QColor('#FFFFFF')
    __DEFAULT_TEXT_COLOR_DARK = QColor('#D0D0D0')
    __DEFAULT_ICON_SEPARATOR_COLOR_DARK = QColor('#585858')
    __DEFAULT_CLOSE_BUTTON_COLOR_DARK = QColor('#C9C9C9')

    # Close event
    closed = Signal()

    def __init__(self, parent):

        super(ToastNotification, self).__init__(parent)

        # Init attributes
        self.__duration = 5000
        self.__show_duration_bar = True
        self.__title = ''
        self.__text = ''
        self.__icon = self.__get_icon_from_enum(ToastIcon.INFORMATION)
        self.__show_icon = False
        self.__icon_size = QSize(18, 18)
        self.__border_radius = 0
        self.__fade_in_duration = 250
        self.__fade_out_duration = 250
        self.__reset_countdown_on_hover = True
        self.__stay_on_top = False
        self.__background_color = ToastNotification.__DEFAULT_BACKGROUND_COLOR
        self.__title_color = ToastNotification.__DEFAULT_TITLE_COLOR
        self.__text_color = ToastNotification.__DEFAULT_TEXT_COLOR
        self.__icon_color = ToastNotification.__DEFAULT_ACCENT_COLOR
        self.__icon_separator_color = ToastNotification.__DEFAULT_ICON_SEPARATOR_COLOR
        self.__close_button_icon_color = ToastNotification.__DEFAULT_CLOSE_BUTTON_COLOR
        self.__duration_bar_color = ToastNotification.__DEFAULT_ACCENT_COLOR
        self.__title_font = QFont()
        self.__title_font.setFamily('Arial')
        self.__title_font.setPointSize(9)
        self.__title_font.setBold(True)
        self.__text_font = QFont()
        self.__text_font.setFamily('Arial')
        self.__text_font.setPointSize(9)
        self.__close_button_icon = self.__get_icon_from_enum(ToastIcon.CLOSE)
        self.__close_button_icon_size = QSize(10, 10)
        self.__close_button_size = QSize(24, 24)
        self.__close_button_alignment = ToastButtonAlignment.TOP
        self.__margins = QMargins(20, 18, 10, 18)
        self.__icon_margins = QMargins(0, 0, 15, 0)
        self.__icon_section_margins = QMargins(0, 0, 15, 0)
        self.__text_section_margins = QMargins(0, 0, 15, 0)
        self.__close_button_margins = QMargins(0, -8, 0, -8)
        self.__text_section_spacing = 10

        self.__elapsed_time = 0
        self.__fading_out = False

        # Window settings
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)

        # Notification widget (QLabel because QWidget has weird behaviour with stylesheets)
        self.__notification = QLabel(self)

        # Drop shadow (has to be drawn manually since only one graphics effect can be applied)
        self.__drop_shadow_layer_1 = QWidget(self)
        self.__drop_shadow_layer_1.setObjectName('toast-drop-shadow-layer-1')

        self.__drop_shadow_layer_2 = QWidget(self)
        self.__drop_shadow_layer_2.setObjectName('toast-drop-shadow-layer-2')

        self.__drop_shadow_layer_3 = QWidget(self)
        self.__drop_shadow_layer_3.setObjectName('toast-drop-shadow-layer-3')

        self.__drop_shadow_layer_4 = QWidget(self)
        self.__drop_shadow_layer_4.setObjectName('toast-drop-shadow-layer-4')

        self.__drop_shadow_layer_5 = QWidget(self)
        self.__drop_shadow_layer_5.setObjectName('toast-drop-shadow-layer-5')

        # Opacity effect for fading animations
        self.__opacity_effect = QGraphicsOpacityEffect()
        self.__opacity_effect.setOpacity(1)
        self.setGraphicsEffect(self.__opacity_effect)

        # Close button
        self.__close_button = QPushButton(self.__notification)
        self.__close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.__close_button.clicked.connect(self.hide)
        self.__close_button.setObjectName('toast-close-button')

        # Title label
        self.__title_label = QLabel(self.__notification)

        # Text label
        self.__text_label = QLabel(self.__notification)

        # Icon (QPushButton instead of QLabel to get better icon quality)
        self.__icon_widget = QPushButton(self.__notification)
        self.__icon_widget.setObjectName('toast-icon-widget')

        # Icon separator
        self.__icon_separator = QWidget(self.__notification)
        self.__icon_separator.setFixedWidth(2)

        # Duration bar container (used to make border radius possible on 4 px high widget)
        self.__duration_bar_container = QWidget(self.__notification)
        self.__duration_bar_container.setFixedHeight(4)
        self.__duration_bar_container.setStyleSheet('background: transparent;')

        # Duration bar
        self.__duration_bar = QWidget(self.__duration_bar_container)
        self.__duration_bar.setFixedHeight(20)
        self.__duration_bar.move(0, -16)

        # Duration bar chunk
        self.__duration_bar_chunk = QWidget(self.__duration_bar_container)
        self.__duration_bar_chunk.setFixedHeight(20)
        self.__duration_bar_chunk.move(0, -16)

        # Set default colors
        self.setIcon(self.__icon)
        self.setIconSize(self.__icon_size)
        self.setIconColor(self.__icon_color)
        self.setBackgroundColor(self.__background_color)
        self.setTitleColor(self.__title_color)
        self.setTextColor(self.__text_color)
        self.setBorderRadius(self.__border_radius)
        self.setIconSeparatorColor(self.__icon_separator_color)
        self.setCloseButtonIconColor(self.__close_button_icon_color)
        self.setDurationBarColor(self.__duration_bar_color)
        self.setTitleFont(self.__title_font)
        self.setTextFont(self.__text_font)
        self.setCloseButtonIcon(self.__close_button_icon)
        self.setCloseButtonIconSize(self.__close_button_icon_size)
        self.setCloseButtonSize(self.__close_button_size)
        self.setCloseButtonAlignment(self.__close_button_alignment)

        # Timer for hiding the notification after set duration
        self.__duration_timer = QTimer(self)
        self.__duration_timer.timeout.connect(self.hide)

        # Timer for updating the duration bar
        self.__duration_bar_timer = QTimer(self)
        self.__duration_bar_timer.timeout.connect(self.__update_duration_bar)

        # Apply stylesheet
        self.setStyleSheet(open(self.__get_directory() + '/css/toast_notification.css').read())

    def enterEvent(self, event):
        # Reset timer if hovered and resetting is enabled
        if self.__duration != 0 and self.__duration_timer.isActive() and self.__reset_countdown_on_hover:
            self.__duration_timer.stop()

            # Reset duration bar if enabled
            if self.__show_duration_bar:
                self.__duration_bar_timer.stop()
                self.__duration_bar_chunk.setFixedWidth(self.width())
                self.__elapsed_time = 0

    def leaveEvent(self, event):
        # Start timer again when leaving notification and reset is enabled
        if self.__duration != 0 and not self.__duration_timer.isActive() and self.__reset_countdown_on_hover:
            self.__duration_timer.start(self.__duration)

            # Restart duration bar animation if enabled
            if self.__show_duration_bar:
                self.__duration_bar_timer.start(ToastNotification.__DURATION_BAR_UPDATE_INTERVAL)

    def show(self):
        # Setup UI
        self.__setup_ui()

        # If max notifications on screen not reached, show notification
        if ToastNotification.__maximum_on_screen > len(ToastNotification.__currently_shown):
            ToastNotification.__currently_shown.append(self)

            # Start duration timer
            if self.__duration != 0:
                self.__duration_timer.start(self.__duration)

            # Start duration bar update timer
            if self.__duration != 0 and self.__show_duration_bar:
                self.__duration_bar_timer.start(ToastNotification.__DURATION_BAR_UPDATE_INTERVAL)

            # Calculate position and show (animate position too if not first notification)
            x, y = self.__calculate_position()

            if len(ToastNotification.__currently_shown) != 1:
                if (ToastNotification.__position == ToastPosition.BOTTOM_RIGHT
                        or ToastNotification.__position == ToastPosition.BOTTOM_LEFT
                        or ToastNotification.__position == ToastPosition.BOTTOM_MIDDLE):
                    self.move(x, y - int(self.height() / 1.5))

                elif (ToastNotification.__position == ToastPosition.TOP_RIGHT
                      or ToastNotification.__position == ToastPosition.TOP_LEFT
                      or ToastNotification.__position == ToastPosition.TOP_MIDDLE):
                    self.move(x, y + int(self.height() / 1.5))

                self.pos_animation = QPropertyAnimation(self, b"pos")
                self.pos_animation.setEndValue(QPoint(x, y))
                self.pos_animation.setDuration(self.__fade_in_duration)
                self.pos_animation.start()
            else:
                self.move(x, y)

            # Fade in
            super().show()
            self.fade_in_animation = QPropertyAnimation(self.__opacity_effect, b"opacity")
            self.fade_in_animation.setDuration(self.__fade_in_duration)
            self.fade_in_animation.setStartValue(0)
            self.fade_in_animation.setEndValue(1)
            self.fade_in_animation.start()

            # Make sure title bar of parent is not grayed out
            self.parent().activateWindow()

            # Update every other currently shown notification
            for n in ToastNotification.__currently_shown:
                n.__update_position_xy()
        else:
            # Add notification to queue instead
            ToastNotification.__queue.append(self)

    def hide(self):
        if not self.__fading_out:
            if self.__duration != 0:
                self.__duration_timer.stop()
                self.__fading_out = True
            self.__fade_out()

    def __fade_out(self):
        self.fade_out_animation = QPropertyAnimation(self.__opacity_effect, b"opacity")
        self.fade_out_animation.setDuration(self.__fade_out_duration)
        self.fade_out_animation.setStartValue(1)
        self.fade_out_animation.setEndValue(0)
        self.fade_out_animation.finished.connect(self.__hide)
        self.fade_out_animation.start()

    def __hide(self):
        self.close()

        if self in ToastNotification.__currently_shown:
            ToastNotification.__currently_shown.remove(self)
            self.__elapsed_time = 0
            self.__fading_out = False

            # Emit signal
            self.closed.emit()

            # Update every other currently shown notification
            for n in ToastNotification.__currently_shown:
                n.__update_position_y()

            # Show next item from queue after updating
            timer = QTimer(self)
            timer.timeout.connect(self.__handle_queue)
            timer.start(self.__fade_in_duration)

    def __update_duration_bar(self):
        self.__elapsed_time += ToastNotification.__DURATION_BAR_UPDATE_INTERVAL

        if self.__elapsed_time >= self.__duration:
            self.__duration_bar_timer.stop()
            return

        new_chunk_width = int(self.width() - self.__elapsed_time / self.__duration * self.width())
        self.__duration_bar_chunk.setFixedWidth(new_chunk_width)

    def __update_position_xy(self):
        x, y = self.__calculate_position()

        # Animate position change
        self.pos_animation = QPropertyAnimation(self, b"pos")
        self.pos_animation.setEndValue(QPoint(x, y))
        self.pos_animation.setDuration(self.__fade_out_duration)
        self.pos_animation.start()

    def __update_position_y(self):
        x, y = self.__calculate_position()

        # Animate position change
        self.pos_animation = QPropertyAnimation(self, b"pos")
        self.pos_animation.setEndValue(QPoint(self.x(), y))
        self.pos_animation.setDuration(self.__fade_out_duration)
        self.pos_animation.start()

    def __handle_queue(self):
        if len(ToastNotification.__queue) > 0:
            n = ToastNotification.__queue.pop()
            n.show()

    def __calculate_position(self):
        # Calculate vertical space taken up by all the currently showing notifications
        y_offset = 0
        for n in ToastNotification.__currently_shown:
            if n == self:
                break
            y_offset += n.__notification.height() + ToastNotification.__spacing

        # Get screen
        primary_screen = QGuiApplication.primaryScreen()
        current_screen = None

        if ToastNotification.__always_on_main_screen:
            current_screen = primary_screen
        else:
            screens = QGuiApplication.screens()
            for screen in screens:
                if self.parent().geometry().intersects(screen.geometry()):
                    if current_screen is None:
                        current_screen = screen
                    else:
                        current_screen = primary_screen
                        break

        # Calculate x and y position of notification
        x = 0
        y = 0

        if ToastNotification.__position == ToastPosition.BOTTOM_RIGHT:
            x = (current_screen.geometry().width() - self.__notification.width()
                 - ToastNotification.__offset_x + current_screen.geometry().x())
            y = (current_screen.geometry().height()
                 - ToastNotification.__currently_shown[0].__notification.height()
                 - ToastNotification.__offset_y + current_screen.geometry().y() - y_offset)

        elif ToastNotification.__position == ToastPosition.BOTTOM_LEFT:
            x = current_screen.geometry().x() + ToastNotification.__offset_x
            y = (current_screen.geometry().height()
                 - ToastNotification.__currently_shown[0].__notification.height()
                 - ToastNotification.__offset_y + current_screen.geometry().y() - y_offset)

        elif ToastNotification.__position == ToastPosition.BOTTOM_MIDDLE:
            x = (current_screen.geometry().x()
                 + current_screen.geometry().width() / 2 - self.__notification.width() / 2)
            y = (current_screen.geometry().height()
                 - ToastNotification.__currently_shown[0].__notification.height()
                 - ToastNotification.__offset_y + current_screen.geometry().y() - y_offset)

        elif ToastNotification.__position == ToastPosition.TOP_RIGHT:
            x = (current_screen.geometry().width() - self.__notification.width()
                 - ToastNotification.__offset_x + current_screen.geometry().x())
            y = (current_screen.geometry().y()
                 + ToastNotification.__offset_y + y_offset)

        elif ToastNotification.__position == ToastPosition.TOP_LEFT:
            x = current_screen.geometry().x() + ToastNotification.__offset_x
            y = (current_screen.geometry().y()
                 + ToastNotification.__offset_y + y_offset)

        elif ToastNotification.__position == ToastPosition.TOP_MIDDLE:
            x = (current_screen.geometry().x()
                 + current_screen.geometry().width() / 2
                 - self.__notification.width() / 2)
            y = (current_screen.geometry().y()
                 + ToastNotification.__offset_y + y_offset)

        x = int(x - ToastNotification.__DROP_SHADOW_SIZE)
        y = int(y - ToastNotification.__DROP_SHADOW_SIZE)

        return x, y

    def __setup_ui(self):
        # Calculate title and text width and height
        title_font_metrics = QFontMetrics(self.__title_font)
        title_width = title_font_metrics.width(self.__title_label.text())
        title_height = title_font_metrics.tightBoundingRect(self.__title_label.text()).height()
        text_font_metrics = QFontMetrics(self.__text_font)
        text_width = text_font_metrics.width(self.__text_label.text())
        text_height = text_font_metrics.boundingRect(self.__text_label.text()).height()

        text_section_height = (self.__text_section_margins.top()
                               + title_height + self.__text_section_spacing
                               + text_height + self.__text_section_margins.bottom())

        # Calculate duration bar height
        duration_bar_height = 0 if not self.__show_duration_bar else self.__duration_bar_container.height()

        # Calculate icon section width and height
        icon_section_width = 0
        icon_section_height = 0

        if self.__show_icon:
            icon_section_width = (self.__icon_section_margins.left()
                                  + self.__icon_margins.left() + self.__icon_widget.width()
                                  + self.__icon_margins.right() + self.__icon_separator.width()
                                  + self.__icon_section_margins.right())
            icon_section_height = (self.__icon_section_margins.top() + self.__icon_margins.top()
                                   + self.__icon_widget.height() + self.__icon_margins.bottom()
                                   + self.__icon_section_margins.bottom())

        # Calculate height and close button section
        close_button_section_height = (self.__close_button_margins.top()
                                       + self.__close_button.height()
                                       + self.__close_button_margins.bottom())

        # Calculate needed width and height
        width = (self.__margins.left() + icon_section_width + self.__text_section_margins.left()
                 + max(title_width, text_width) + self.__text_section_margins.right()
                 + self.__close_button_margins.left() + self.__close_button.width()
                 + self.__close_button_margins.right() + self.__margins.right())

        height = (self.__margins.top()
                  + max(icon_section_height, text_section_height, close_button_section_height)
                  + self.__margins.bottom() + duration_bar_height)

        forced_additional_height = 0
        forced_reduced_height = 0

        # Handle width greater than maximum width
        if width > self.maximumWidth():
            # Enable line break for title and text and recalculate size
            title_width = text_width = title_width - (width - self.maximumWidth())

            self.__title_label.setMinimumWidth(title_width)
            self.__title_label.setWordWrap(True)
            title_height = self.__title_label.sizeHint().height()
            self.__title_label.resize(title_width, title_height)

            self.__text_label.setMinimumWidth(text_width)
            self.__text_label.setWordWrap(True)
            text_height = self.__text_label.sizeHint().height()
            self.__text_label.resize(text_width, text_height)

            # Recalculate width and height
            width = self.maximumWidth()

            text_section_height = (self.__text_section_margins.top()
                                   + title_height + self.__text_section_spacing
                                   + text_height + self.__text_section_margins.bottom())

            height = (self.__margins.top()
                      + max(icon_section_height, text_section_height, close_button_section_height)
                      + self.__margins.bottom() + duration_bar_height)

        # Handle height less than minimum height
        if height < self.minimumHeight():
            # Enable word wrap for title and text labels
            self.__title_label.setWordWrap(True)
            self.__text_label.setWordWrap(True)

            # Calculate height with initial label width
            title_width = (self.__title_label.fontMetrics().boundingRect(
                QRect(0, 0, 0, 0), Qt.TextWordWrap, self.__title_label.text()).width())
            text_width = (self.__text_label.fontMetrics().boundingRect(
                QRect(0, 0, 0, 0), Qt.TextWordWrap, self.__text_label.text()).width())
            temp_width = max(title_width, text_width)

            title_width = (self.__title_label.fontMetrics().boundingRect(
                QRect(0, 0, temp_width, 0), Qt.TextWordWrap, self.__title_label.text()).width())
            title_height = (self.__title_label.fontMetrics().boundingRect(
                QRect(0, 0, temp_width, 0), Qt.TextWordWrap, self.__title_label.text()).height())
            text_width = (self.__text_label.fontMetrics().boundingRect(
                QRect(0, 0, temp_width, 0), Qt.TextWordWrap, self.__text_label.text()).width())
            text_height = (self.__text_label.fontMetrics().boundingRect(
                QRect(0, 0, temp_width, 0), Qt.TextWordWrap, self.__text_label.text()).height())

            text_section_height = (self.__text_section_margins.top()
                                   + title_height + self.__text_section_spacing
                                   + text_height + self.__text_section_margins.bottom())

            height = (self.__margins.top()
                      + max(icon_section_height, text_section_height, close_button_section_height)
                      + self.__margins.bottom() + duration_bar_height)

            while temp_width <= width:
                # Recalculate height with different text widths to find optimal value
                temp_title_width = (self.__title_label.fontMetrics().boundingRect(
                    QRect(0, 0, temp_width, 0), Qt.TextWordWrap, self.__title_label.text()).width())
                temp_title_height = (self.__title_label.fontMetrics().boundingRect(
                    QRect(0, 0, temp_width, 0), Qt.TextWordWrap, self.__title_label.text()).height())
                temp_text_width = (self.__text_label.fontMetrics().boundingRect(
                    QRect(0, 0, temp_width, 0), Qt.TextWordWrap, self.__text_label.text()).width())
                temp_text_height = (self.__text_label.fontMetrics().boundingRect(
                    QRect(0, 0, temp_width, 0), Qt.TextWordWrap, self.__text_label.text()).height())

                temp_text_section_height = (self.__text_section_margins.top()
                                            + temp_title_height + self.__text_section_spacing
                                            + temp_text_height + self.__text_section_margins.bottom())

                temp_height = (self.__margins.top()
                               + max(icon_section_height, temp_text_section_height,
                                     close_button_section_height)
                               + self.__margins.bottom() + duration_bar_height)

                # Store values if calculated height is greater than or equal to min height
                if temp_height >= self.minimumHeight():
                    title_width = temp_title_width
                    title_height = temp_title_height
                    text_width = temp_text_width
                    text_height = temp_text_height
                    text_section_height = temp_text_section_height
                    height = temp_height
                    temp_width += 1

                # Exit loop if calculated height is less than min height
                else:
                    break

            # Recalculate width
            width = (self.__margins.left() + icon_section_width + self.__text_section_margins.left()
                     + max(title_width, text_width) + self.__text_section_margins.right()
                     + self.__close_button_margins.left() + self.__close_button.width()
                     + self.__close_button_margins.right() + self.__margins.right())

            # If min height not met, set height to min height
            if height < self.minimumHeight():
                forced_additional_height = self.minimumHeight() - height
                height = self.minimumHeight()

        # Handle width less than minimum width
        if width < self.minimumWidth():
            width = self.minimumWidth()

        # Handle height greater than maximum height
        if height > self.maximumHeight():
            forced_reduced_height = height - self.maximumHeight()
            height = self.maximumHeight()

        # Calculate width and height including space for drop shadow
        total_width = width + (ToastNotification.__DROP_SHADOW_SIZE * 2)
        total_height = height + (ToastNotification.__DROP_SHADOW_SIZE * 2)

        # Resize drop shadow
        self.__drop_shadow_layer_1.resize(total_width, total_height)
        self.__drop_shadow_layer_1.move(0, 0)
        self.__drop_shadow_layer_2.resize(total_width - 2, total_height - 2)
        self.__drop_shadow_layer_2.move(1, 1)
        self.__drop_shadow_layer_3.resize(total_width - 4, total_height - 4)
        self.__drop_shadow_layer_3.move(2, 2)
        self.__drop_shadow_layer_4.resize(total_width - 6, total_height - 6)
        self.__drop_shadow_layer_4.move(3, 3)
        self.__drop_shadow_layer_5.resize(total_width - 8, total_height - 8)
        self.__drop_shadow_layer_5.move(4, 4)

        # Resize window
        self.resize(total_width, total_height)
        self.__notification.setFixedSize(width, height)
        self.__notification.move(ToastNotification.__DROP_SHADOW_SIZE,
                                 ToastNotification.__DROP_SHADOW_SIZE)
        self.__notification.raise_()

        # Calculate difference between height and height of icon section
        height_icon_section_height_difference = (max(icon_section_height,
                                                     text_section_height,
                                                     close_button_section_height)
                                                 - icon_section_height)

        if self.__show_icon:
            # Move icon
            self.__icon_widget.move(self.__margins.left()
                                    + self.__icon_section_margins.left()
                                    + self.__icon_margins.left(),
                                    self.__margins.top()
                                    + self.__icon_section_margins.top()
                                    + self.__icon_margins.top()
                                    + math.ceil(height_icon_section_height_difference / 2)
                                    + math.ceil(forced_additional_height / 2)
                                    - math.floor(forced_reduced_height / 2))

            # Move and resize icon separator
            self.__icon_separator.setFixedHeight(text_section_height)
            self.__icon_separator.move(self.__margins.left()
                                       + self.__icon_section_margins.left()
                                       + self.__icon_margins.left()
                                       + self.__icon_widget.width()
                                       + self.__icon_margins.right(),
                                       self.__margins.top()
                                       + self.__icon_section_margins.top()
                                       + math.ceil(forced_additional_height / 2)
                                       - math.floor(forced_reduced_height / 2))

            # Show icon section
            self.__icon_widget.setVisible(True)
            self.__icon_separator.setVisible(True)
        else:
            # Hide icon section
            self.__icon_widget.setVisible(False)
            self.__icon_separator.setVisible(False)

        # Calculate difference between height and height of text section
        height_text_section_height_difference = (max(icon_section_height,
                                                     text_section_height,
                                                     close_button_section_height)
                                                 - text_section_height)

        # Resize title and text labels
        self.__title_label.resize(title_width, title_height)
        self.__text_label.resize(text_width, text_height)

        # Move title and text labels
        if self.__show_icon:
            self.__title_label.move(self.__margins.left()
                                    + self.__icon_section_margins.left()
                                    + self.__icon_margins.left()
                                    + self.__icon_widget.width()
                                    + self.__icon_margins.right()
                                    + self.__icon_section_margins.right()
                                    + self.__text_section_margins.left(),
                                    self.__margins.top()
                                    + self.__text_section_margins.top()
                                    + math.ceil(height_text_section_height_difference / 2)
                                    + math.ceil(forced_additional_height / 2)
                                    - math.floor(forced_reduced_height / 2))

            self.__text_label.move(self.__margins.left()
                                   + self.__icon_section_margins.left()
                                   + self.__icon_margins.left()
                                   + self.__icon_widget.width()
                                   + self.__icon_margins.right()
                                   + self.__icon_section_margins.right()
                                   + self.__text_section_margins.left(),
                                   self.__margins.top()
                                   + self.__text_section_margins.top()
                                   + title_height + self.__text_section_spacing
                                   + math.ceil(height_text_section_height_difference / 2)
                                   + math.ceil(forced_additional_height / 2)
                                   - math.floor(forced_reduced_height / 2))

        # Position is different if icon hidden
        else:
            self.__title_label.move(self.__margins.left()
                                    + self.__text_section_margins.left(),
                                    self.__margins.top()
                                    + self.__text_section_margins.top()
                                    + math.ceil(height_text_section_height_difference / 2)
                                    + math.ceil(forced_additional_height / 2)
                                    - math.floor(forced_reduced_height / 2))

            self.__text_label.move(self.__margins.left()
                                   + self.__text_section_margins.left(),
                                   self.__margins.top()
                                   + self.__text_section_margins.top()
                                   + title_height + self.__text_section_spacing
                                   + math.ceil(height_text_section_height_difference / 2)
                                   + math.ceil(forced_additional_height / 2)
                                   - math.floor(forced_reduced_height / 2))

        # Adjust label position if either title or text is empty
        if self.__title == '' and self.__text != '':
            self.__text_label.move(self.__text_label.x(),
                                   int((height - text_height - duration_bar_height) / 2))

        elif self.__title != '' and self.__text == '':
            self.__title_label.move(self.__title_label.x(),
                                    int((height - title_height - duration_bar_height) / 2))

        # Move close button to top, middle, or bottom position
        if self.__close_button_alignment == ToastButtonAlignment.TOP:
            self.__close_button.move(width - self.__close_button.width()
                                     - self.__close_button_margins.right() - self.__margins.right(),
                                     self.__margins.top() + self.__close_button_margins.top())
        elif self.__close_button_alignment == ToastButtonAlignment.MIDDLE:
            self.__close_button.move(width - self.__close_button.width()
                                     - self.__close_button_margins.right() - self.__margins.right(),
                                     math.ceil((height - self.__close_button.height()
                                               - duration_bar_height) / 2))
        elif self.__close_button_alignment == ToastButtonAlignment.BOTTOM:
            self.__close_button.move(width - self.__close_button.width()
                                     - self.__close_button_margins.right() - self.__margins.right(),
                                     height - self.__close_button.height()
                                     - self.__margins.bottom()
                                     - self.__close_button_margins.bottom() - duration_bar_height)

        # Resize, move, and show duration bar if enabled
        if self.__show_duration_bar:
            self.__duration_bar_container.setFixedWidth(width)
            self.__duration_bar_container.move(0, height - duration_bar_height)
            self.__duration_bar.setFixedWidth(width)
            self.__duration_bar_chunk.setFixedWidth(width)
            self.__duration_bar_container.setVisible(True)
        else:
            self.__duration_bar_container.setVisible(False)

    def getDuration(self) -> int:
        return self.__duration

    def setDuration(self, duration: int):
        self.__duration = duration

    def isShowDurationBar(self) -> bool:
        return self.__show_duration_bar

    def setShowDurationBar(self, on: bool):
        self.__show_duration_bar = on

    def getTitle(self) -> str:
        return self.__title

    def setTitle(self, title: str):
        self.__title = title
        self.__title_label.setText(title)

    def getText(self) -> str:
        return self.__text

    def setText(self, text: str):
        self.__text = text
        self.__text_label.setText(text)

    def getIcon(self) -> QPixmap:
        return self.__icon_widget.pixmap()

    def setIcon(self, icon: QPixmap | ToastIcon):
        if type(icon) == ToastIcon:
            self.__icon = self.__get_icon_from_enum(icon)
        else:
            self.__icon = icon

        self.__icon_widget.setIcon(QIcon(self.__icon))
        self.setIconColor(self.__icon_color)

    def isShowIcon(self) -> bool:
        return self.__show_icon

    def setShowIcon(self, on: bool):
        self.__show_icon = on

    def getIconSize(self) -> QSize:
        return self.__icon_size

    def setIconSize(self, size: QSize):
        self.__icon_size = size
        self.__icon_widget.setFixedSize(size)
        self.__icon_widget.setIconSize(size)
        self.setIcon(self.__icon)

    def getBorderRadius(self) -> int:
        return self.__border_radius

    def setBorderRadius(self, border_radius: int):
        self.__border_radius = border_radius
        self.__update_stylesheet()

    def getFadeInDuration(self) -> int:
        return self.__fade_in_duration

    def setFadeInDuration(self, duration: int):
        self.__fade_in_duration = duration

    def getFadeOutDuration(self) -> int:
        return self.__fade_out_duration

    def setFadeOutDuration(self, duration: int):
        self.__fade_out_duration = duration

    def isResetCountdownOnHover(self) -> bool:
        return self.__reset_countdown_on_hover

    def setResetCountdownOnHover(self, on: bool):
        self.__reset_countdown_on_hover = on

    def isStayOnTop(self) -> bool:
        return self.__stay_on_top

    def setStayOnTop(self, on: bool):
        self.__stay_on_top = on
        if on:
            self.setWindowFlags(Qt.Window |
                                Qt.CustomizeWindowHint |
                                Qt.FramelessWindowHint |
                                Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(Qt.Window |
                                Qt.CustomizeWindowHint |
                                Qt.FramelessWindowHint)

    def getBackgroundColor(self) -> QColor:
        return self.__background_color

    def setBackgroundColor(self, color: QColor):
        self.__background_color = color
        self.__update_stylesheet()

    def getTitleColor(self) -> QColor:
        return self.__title_color

    def setTitleColor(self, color: QColor):
        self.__title_color = color
        self.__update_stylesheet()

    def getTextColor(self) -> QColor:
        return self.__text_color

    def setTextColor(self, color: QColor):
        self.__text_color = color
        self.__update_stylesheet()

    def getIconColor(self) -> QColor:
        return self.__icon_color

    def setIconColor(self, color: QColor):
        self.__icon_color = color

        recolored_image = self.__recolor_image(self.__icon_widget.icon().pixmap(
                                               self.__icon_widget.iconSize()).toImage(),
                                               self.__icon_widget.iconSize().width(),
                                               self.__icon_widget.iconSize().height(),
                                               color)
        self.__icon_widget.setIcon(QIcon(QPixmap(recolored_image)))

    def getIconSeparatorColor(self) -> QColor:
        return self.__icon_separator_color

    def setIconSeparatorColor(self, color: QColor):
        self.__icon_separator_color = color
        self.__update_stylesheet()

    def getCloseButtonColor(self) -> QColor:
        return self.__close_button_icon_color

    def setCloseButtonIconColor(self, color: QColor):
        self.__close_button_icon_color = color

        recolored_image = self.__recolor_image(self.__close_button.icon().pixmap(
                                               self.__close_button.iconSize()).toImage(),
                                               self.__close_button.iconSize().width(),
                                               self.__close_button.iconSize().height(),
                                               color)
        self.__close_button.setIcon(QIcon(QPixmap(recolored_image)))

    def getDurationBarColor(self) -> QColor:
        return self.__duration_bar_color

    def setDurationBarColor(self, color: QColor):
        self.__duration_bar_color = color
        self.__update_stylesheet()

    def getTitleFont(self) -> QFont:
        return self.__title_font

    def setTitleFont(self, font: QFont):
        self.__title_font = font
        self.__title_label.setFont(font)

    def getTextFont(self) -> QFont:
        return self.__text_font

    def setTextFont(self, font: QFont):
        self.__text_font = font
        self.__text_label.setFont(font)

    def getCloseButtonIcon(self) -> QPixmap:
        return self.__close_button_icon

    def setCloseButtonIcon(self, icon: QPixmap | ToastIcon):
        if type(icon) == ToastIcon:
            self.__close_button_icon = self.__get_icon_from_enum(icon)
        else:
            self.__close_button_icon = icon

        self.__close_button.setIcon(QIcon(self.__close_button_icon))
        self.setCloseButtonIconColor(self.__close_button_icon_color)

    def getCloseButtonIconSize(self) -> QSize:
        return self.__close_button_icon_size

    def setCloseButtonIconSize(self, size: QSize):
        self.__close_button_icon_size = size
        self.__close_button.setIconSize(size)
        self.setCloseButtonIcon(self.__close_button_icon)

    def getCloseButtonSize(self) -> QSize:
        return self.__close_button_size

    def setCloseButtonSize(self, size: QSize):
        self.__close_button_size = size
        self.__close_button.setFixedSize(size)

    def getCloseButtonWidth(self) -> int:
        return self.__close_button_size.width()

    def setCloseButtonWidth(self, width: int):
        self.__close_button_size.setWidth(width)
        self.__close_button.setFixedSize(self.__close_button_size)

    def getCloseButtonHeight(self) -> int:
        return self.__close_button_size.height()

    def setCloseButtonHeight(self, height: int):
        self.__close_button_size.setHeight(height)
        self.__close_button.setFixedSize(self.__close_button_size)

    def getCloseButtonAlignment(self) -> ToastButtonAlignment:
        return self.__close_button_alignment

    def setCloseButtonAlignment(self, alignment: ToastButtonAlignment):
        if (alignment == ToastButtonAlignment.TOP
                or alignment == ToastButtonAlignment.MIDDLE
                or alignment == ToastButtonAlignment.BOTTOM):
            self.__close_button_alignment = alignment

    def getMargins(self) -> QMargins:
        return self.__margins

    def setMargins(self, margins: QMargins):
        self.__margins = margins

    def getMarginLeft(self) -> int:
        return self.__margins.left()

    def setMarginLeft(self, margin: int):
        self.__margins.setLeft(margin)

    def getMarginTop(self) -> int:
        return self.__margins.top()

    def setMarginTop(self, margin: int):
        self.__margins.setTop(margin)

    def getMarginRight(self) -> int:
        return self.__margins.right()

    def setMarginRight(self, margin: int):
        self.__margins.setRight(margin)

    def getMarginBottom(self) -> int:
        return self.__margins.bottom()

    def setMarginBottom(self, margin: int):
        self.__margins.setBottom(margin)

    def getIconMargins(self) -> QMargins:
        return self.__icon_margins

    def setIconMargins(self, margins: QMargins):
        self.__icon_margins = margins

    def getIconMarginLeft(self) -> int:
        return self.__icon_margins.left()

    def setIconMarginLeft(self, margin: int):
        self.__icon_margins.setLeft(margin)

    def getIconMarginTop(self) -> int:
        return self.__icon_margins.top()

    def setIconMarginTop(self, margin: int):
        self.__icon_margins.setTop(margin)

    def getIconMarginRight(self) -> int:
        return self.__icon_margins.right()

    def setIconMarginRight(self, margin: int):
        self.__icon_margins.setRight(margin)

    def getIconMarginBottom(self) -> int:
        return self.__icon_margins.bottom()

    def setIconMarginBottom(self, margin: int):
        self.__icon_margins.setBottom(margin)

    def getIconSectionMargins(self) -> QMargins:
        return self.__icon_section_margins

    def setIconSectionMargins(self, margins: QMargins):
        self.__icon_section_margins = margins

    def getIconSectionMarginLeft(self) -> int:
        return self.__icon_section_margins.left()

    def setIconSectionMarginLeft(self, margin: int):
        self.__icon_section_margins.setLeft(margin)

    def getIconSectionMarginTop(self) -> int:
        return self.__icon_section_margins.top()

    def setIconSectionMarginTop(self, margin: int):
        self.__icon_section_margins.setTop(margin)

    def getIconSectionMarginRight(self) -> int:
        return self.__icon_section_margins.right()

    def setIconSectionMarginRight(self, margin: int):
        self.__icon_section_margins.setRight(margin)

    def getIconSectionMarginBottom(self) -> int:
        return self.__icon_section_margins.bottom()

    def setIconSectionMarginBottom(self, margin: int):
        self.__icon_section_margins.setBottom(margin)

    def getTextSectionMargins(self) -> QMargins:
        return self.__text_section_margins

    def setTextSectionMargins(self, margins: QMargins):
        self.__text_section_margins = margins

    def getTextSectionMarginLeft(self) -> int:
        return self.__text_section_margins.left()

    def setTextSectionMarginLeft(self, margin: int):
        self.__text_section_margins.setLeft(margin)

    def getTextSectionMarginTop(self) -> int:
        return self.__text_section_margins.top()

    def setTextSectionMarginTop(self, margin: int):
        self.__text_section_margins.setTop(margin)

    def getTextSectionMarginRight(self) -> int:
        return self.__text_section_margins.right()

    def setTextSectionMarginRight(self, margin: int):
        self.__text_section_margins.setRight(margin)

    def getTextSectionMarginBottom(self) -> int:
        return self.__text_section_margins.bottom()

    def setTextSectionMarginBottom(self, margin: int):
        self.__text_section_margins.setBottom(margin)

    def getCloseButtonMargins(self) -> QMargins:
        return self.__close_button_margins

    def setCloseButtonMargins(self, margins: QMargins):
        self.__close_button_margins = margins

    def getCloseButtonMarginLeft(self) -> int:
        return self.__close_button_margins.left()

    def setCloseButtonMarginLeft(self, margin: int):
        self.__close_button_margins.setLeft(margin)

    def getCloseButtonMarginTop(self) -> int:
        return self.__close_button_margins.top()

    def setCloseButtonMarginTop(self, margin: int):
        self.__close_button_margins.setTop(margin)

    def getCloseButtonMarginRight(self) -> int:
        return self.__close_button_margins.right()

    def setCloseButtonMarginRight(self, margin: int):
        self.__close_button_margins.setRight(margin)

    def getCloseButtonMarginBottom(self) -> int:
        return self.__close_button_margins.bottom()

    def setCloseButtonMarginBottom(self, margin: int):
        self.__close_button_margins.setBottom(margin)

    def getTextSectionSpacing(self) -> int:
        return self.__text_section_spacing

    def setTextSectionSpacing(self, spacing: int):
        self.__text_section_spacing = spacing

    def applyPreset(self, preset: ToastPreset):
        if preset == ToastPreset.SUCCESS or preset == ToastPreset.SUCCESS_DARK:
            self.setIcon(ToastIcon.SUCCESS)
            self.setIconColor(ToastNotification.__SUCCESS_ACCENT_COLOR)
            self.setDurationBarColor(ToastNotification.__SUCCESS_ACCENT_COLOR)

        elif preset == ToastPreset.WARNING or preset == ToastPreset.WARNING_DARK:
            self.setIcon(ToastIcon.WARNING)
            self.setIconColor(ToastNotification.__WARNING_ACCENT_COLOR)
            self.setDurationBarColor(ToastNotification.__WARNING_ACCENT_COLOR)

        elif preset == ToastPreset.ERROR or preset == ToastPreset.ERROR_DARK:
            self.setIcon(ToastIcon.ERROR)
            self.setIconColor(ToastNotification.__ERROR_ACCENT_COLOR)
            self.setDurationBarColor(ToastNotification.__ERROR_ACCENT_COLOR)

        elif preset == ToastPreset.INFORMATION or preset == ToastPreset.INFORMATION_DARK:
            self.setIcon(ToastIcon.INFORMATION)
            self.setIconColor(ToastNotification.__INFORMATION_ACCENT_COLOR)
            self.setDurationBarColor(ToastNotification.__INFORMATION_ACCENT_COLOR)

        if (preset == ToastPreset.SUCCESS
                or preset == ToastPreset.WARNING
                or preset == ToastPreset.ERROR
                or preset == ToastPreset.INFORMATION):
            self.setBackgroundColor(ToastNotification.__DEFAULT_BACKGROUND_COLOR)
            self.setCloseButtonIconColor(ToastNotification.__DEFAULT_CLOSE_BUTTON_COLOR)
            self.__show_icon = True
            self.setIconSeparatorColor(ToastNotification.__DEFAULT_ICON_SEPARATOR_COLOR)
            self.setShowDurationBar(True)
            self.setTitleColor(ToastNotification.__DEFAULT_TITLE_COLOR)
            self.setTextColor(ToastNotification.__DEFAULT_TEXT_COLOR)

        elif (preset == ToastPreset.SUCCESS_DARK
                or preset == ToastPreset.WARNING_DARK
                or preset == ToastPreset.ERROR_DARK
                or preset == ToastPreset.INFORMATION_DARK):
            self.setBackgroundColor(ToastNotification.__DEFAULT_BACKGROUND_COLOR_DARK)
            self.setCloseButtonIconColor(ToastNotification.__DEFAULT_CLOSE_BUTTON_COLOR_DARK)
            self.__show_icon = True
            self.setIconSeparatorColor(ToastNotification.__DEFAULT_ICON_SEPARATOR_COLOR_DARK)
            self.setShowDurationBar(True)
            self.setTitleColor(ToastNotification.__DEFAULT_TITLE_COLOR_DARK)
            self.setTextColor(ToastNotification.__DEFAULT_TEXT_COLOR_DARK)

    def __update_stylesheet(self):
        self.__notification.setStyleSheet('background: {};'
                                        'border-radius: {}px;'
                                          .format(self.__background_color.name(),
                                                self.__border_radius))

        self.__duration_bar.setStyleSheet('background: rgba({}, {}, {}, 100);'
                                        'border-radius: {}px;'
                                          .format(self.__duration_bar_color.red(),
                                                self.__duration_bar_color.green(),
                                                self.__duration_bar_color.blue(),
                                                self.__border_radius))

        self.__duration_bar_chunk.setStyleSheet('background: rgba({}, {}, {}, 255);'
                                              'border-bottom-left-radius: {}px;'
                                              'border-bottom-right-radius: {}px;'
                                                .format(self.__duration_bar_color.red(),
                                                      self.__duration_bar_color.green(),
                                                      self.__duration_bar_color.blue(),
                                                      self.__border_radius,
                                                      self.__border_radius if self.__duration == 0 else 0))

        self.__icon_separator.setStyleSheet('background: {};'
                                            .format(self.__icon_separator_color.name()))

        self.__title_label.setStyleSheet('color: {};'.format(self.__title_color.name()))
        self.__text_label.setStyleSheet('color: {};'.format(self.__text_color.name()))

    @staticmethod
    def __recolor_image(image: QImage, width: int, height: int, color: QColor):
        # Loop through every pixel
        for x in range(0, width):
            for y in range(0, height):
                # Get current color of the pixel
                current_color = image.pixelColor(x, y)
                # Replace the rgb values with rgb of new color and keep alpha the same
                new_color_r = color.red()
                new_color_g = color.green()
                new_color_b = color.blue()
                new_color = QColor.fromRgba(
                    qRgba(new_color_r, new_color_g, new_color_b, current_color.alpha()))
                image.setPixelColor(x, y, new_color)
        return image

    @staticmethod
    def __get_directory():
        return os.path.dirname(os.path.realpath(__file__))

    @staticmethod
    def __get_icon_from_enum(enum_icon: ToastIcon):
        if enum_icon == ToastIcon.SUCCESS:
            return QPixmap(ToastNotification.__get_directory() + '/icons/success.png')
        elif enum_icon == ToastIcon.WARNING:
            return QPixmap(ToastNotification.__get_directory() + '/icons/warning.png')
        elif enum_icon == ToastIcon.ERROR:
            return QPixmap(ToastNotification.__get_directory() + '/icons/error.png')
        elif enum_icon == ToastIcon.INFORMATION:
            return QPixmap(ToastNotification.__get_directory() + '/icons/information.png')
        elif enum_icon == ToastIcon.CLOSE:
            return QPixmap(ToastNotification.__get_directory() + '/icons/close.png')
        else:
            return None

    @staticmethod
    def getMaximumOnScreen():
        return ToastNotification.__maximum_on_screen

    @staticmethod
    def setMaximumOnScreen(maximum_on_screen: int):
        ToastNotification.__maximum_on_screen = maximum_on_screen

    @staticmethod
    def getSpacing():
        return ToastNotification.__spacing

    @staticmethod
    def setSpacing(spacing: int):
        ToastNotification.__spacing = spacing

    @staticmethod
    def getOffsetX() -> int:
        return ToastNotification.__offset_x

    @staticmethod
    def setOffsetX(offset_x: int):
        ToastNotification.__offset_x = offset_x

    @staticmethod
    def getOffsetY() -> int:
        return ToastNotification.__offset_y

    @staticmethod
    def setOffsetY(offset_y: int):
        ToastNotification.__offset_y = offset_y

    @staticmethod
    def getOffset() -> tuple[int, int]:
        return ToastNotification.__offset_x, ToastNotification.__offset_y

    @staticmethod
    def setOffset(offset_x: int, offset_y: int):
        ToastNotification.__offset_x = offset_x
        ToastNotification.__offset_y = offset_y

    @staticmethod
    def isAlwaysOnMainScreen() -> bool:
        return ToastNotification.__always_on_main_screen

    @staticmethod
    def setAlwaysOnMainScreen(on: bool):
        ToastNotification.__always_on_main_screen = on

    @staticmethod
    def getPosition() -> ToastPosition:
        return ToastNotification.__position

    @staticmethod
    def setPosition(position: int):
        if (position == ToastPosition.BOTTOM_RIGHT
                or position == ToastPosition.BOTTOM_LEFT
                or position == ToastPosition.BOTTOM_MIDDLE
                or position == ToastPosition.TOP_RIGHT
                or position == ToastPosition.TOP_LEFT
                or position == ToastPosition.TOP_MIDDLE):
            ToastNotification.__position = position

    @staticmethod
    def getCount() -> int:
        return len(ToastNotification.__currently_shown) + len(ToastNotification.__queue)

    @staticmethod
    def getVisibleCount() -> int:
        return len(ToastNotification.__currently_shown)

    @staticmethod
    def getQueueCount() -> int:
        return len(ToastNotification.__queue)
