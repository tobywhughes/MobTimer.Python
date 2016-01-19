import atexit
import os
import uuid
from tkinter import *
from tkinter import ttk

from Frames.MinimalScreenBlockerFrame import MinimalScreenBlockerFrame
from Frames.ScreenBlockerFrame import ScreenBlockerFrame
from Frames.TransparentCountdownFrame import TransparentCountdownFrame
from Infrastructure.CountdownManager import CountdownManager
from Infrastructure.MobberManager import MobberManager
from Infrastructure.PlatformUtility import PlatformUtility
from Infrastructure.ScreenUtility import ScreenUtility
from Infrastructure.SessionManager import SessionManager
from Infrastructure.SettingsManager import SettingsManager
from Infrastructure.ThemeManager import ThemeManager
from Infrastructure.TimeSettingsManager import TimeSettingsManager
from Infrastructure.TipsManager import TipsManager


class MobTimerController(Tk):
    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        self.transparent_frame_monitor_index = 0
        self.transparent_frame_position_index = 0
        self.settings_manager = SettingsManager()
        self.tips_manager = TipsManager()
        self.time_options_manager = TimeSettingsManager()
        self.mobber_manager = MobberManager(self.settings_manager.get_randomize_randomize_next_driver())
        self.countdown_manager = CountdownManager(self)
        self.session_manager = SessionManager(uuid)
        self.timer_extension_count = self.settings_manager.get_timer_extension_count()
        self.extensions_used = 0
        atexit.register(self.session_manager.clear_sessions)
        if self.session_manager.get_active_sessions().__len__() > 0:
            self.quit_and_destroy_session()

        self.session_manager.create_session()
        # self.iconbitmap(default='time-bomb.ico')
        self.countdown_manager.subscribe_to_time_changes(self.show_screen_blocker_when_session_interupted)

        self.theme_manager = ThemeManager()
        theme = self.settings_manager.get_general_theme()
        if not theme == 'none':
            self.theme_manager.set_theme(theme)

        num_monitors = ScreenUtility.get_monitors_or_default(self).__len__()
        self.containers = [self]
        for monitor_index in range(1, num_monitors):
            monitor_screen_blocker = Toplevel(self)
            self.containers.append(monitor_screen_blocker)
        self.frame_types = (ScreenBlockerFrame, TransparentCountdownFrame, MinimalScreenBlockerFrame)
        self.frames = {}
        for frame_type in self.frame_types:
            self.frames[frame_type] = []
        for container in self.containers:
            container.grid_rowconfigure(0, weight=1)
            container.grid_columnconfigure(0, weight=1)

            container_frame = ttk.Frame(container)

            container_frame.grid(row=0, column=0, sticky=(N, S, E, W))
            container_frame.grid_rowconfigure(0, weight=1)
            container_frame.grid_columnconfigure(0, weight=1)
            for frame_type in self.frame_types:
                frame_instance = frame_type(container_frame, self, self.time_options_manager, self.mobber_manager,
                                            self.countdown_manager, self.settings_manager, self.tips_manager, self.theme_manager)
                self.frames[frame_type].append(frame_instance)
                frame_instance.grid(row=0, column=0, sticky=(N, S, E, W))
                frame_instance.grid_rowconfigure(0, weight=1)
                frame_instance.grid_columnconfigure(0, weight=1)
        self.last_frame = None
        self.show_screen_blocker_frame()
        for frame_instance in self.frames[TransparentCountdownFrame]:
            frame_instance.bind("<Enter>", self.toggle_transparent_frame_position)
        self.transparent_frame_position = 0
        self.title("Mob Timer")
        self.bind_all("<Control-Return>", self.launch_transparent_countdown_if_blocking)
        self.time_options_manager.set_countdown_time(self.settings_manager.get_timer_minutes(), self.settings_manager.get_timer_seconds())

    def launch_transparent_countdown_if_blocking(self, event):
        if self.frame_is_screen_blocking():
            self.show_transparent_countdown_frame()

    def frame_is_screen_blocking(self):
        return self.last_frame == ScreenBlockerFrame or self.last_frame == MinimalScreenBlockerFrame

    def show_minimal_screen_blocker_frame(self):
        if self.last_frame != MinimalScreenBlockerFrame:
            self.launch_blocking_Frame(MinimalScreenBlockerFrame)
            self.mobber_manager.switch_next_driver()

    def quit_and_destroy_session(self):
        self.session_manager.clear_sessions()
        self.quit()
        sys.exit()

    def show_screen_blocker_when_session_interupted(self, days, minutes, seconds):
        if self.session_manager.get_active_sessions().__len__() == 0:
            self.show_screen_blocker_frame()
            self.session_manager.create_session()

    def show_frame(self, frame_class):
        switched_frames = False
        if self.last_frame != frame_class:
            for frame_instances in self.frames[frame_class]:
                frame_instances.tkraise()

            switched_frames = True
            self.focus_force()
            self.focus_set()
        self.last_frame = frame_class

        for container in self.containers:
            if isinstance(container, Toplevel):
                if self.frame_is_screen_blocking():
                    container.deiconify()
                else:
                    container.withdraw()

        return switched_frames

    def show_screen_blocker_frame(self):
        if self.last_frame != ScreenBlockerFrame:
            self.launch_blocking_Frame(ScreenBlockerFrame)

    def launch_blocking_Frame(self, frame):
        if self.show_frame(frame):
            self.set_full_screen_always_on_top()

    def show_transparent_countdown_frame(self, extend_amount=None):
        if self.show_frame(TransparentCountdownFrame):
            if extend_amount is None:
                self.extensions_used = 0
                self.countdown_manager.set_countdown_duration(self.time_options_manager.minutes,
                                                              self.time_options_manager.seconds)
                for minimal_frame in self.frames[MinimalScreenBlockerFrame]:
                    minimal_frame.show_extend_time_button()
            else:
                self.countdown_manager.set_countdown_duration(extend_amount, 0)
            self.set_partial_screen_transparent()

    def get_current_window_geometry(self):
        return "{0}x{1}+0+0".format(
                self.winfo_screenwidth(), self.winfo_screenheight())

    def disable_resizing(self):
        for container in self.containers:
            container.resizable(0, 0)

    def remove_title_bar(self):
        if PlatformUtility.platform_is_mac():
            return
        for container in self.containers:
            container.overrideredirect(1)

    def set_always_on_top(self):
        for container in self.containers:
            container.wm_attributes("-topmost", True)
            if PlatformUtility.platform_is_mac():
                os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
                self.focus_force()
                self.focus()
            container.focus_force()

    def set_full_screen_always_on_top(self):
        self.set_always_on_top()
        self.remove_title_bar()
        self.disable_resizing()
        monitors = ScreenUtility.get_monitors_or_default(self)

        for container, monitor in zip(self.containers, monitors):
            monitor_string = "{}x{}+{}+{}".format(monitor.width, monitor.height, monitor.x, monitor.y)
            container.geometry(monitor_string)
            if not PlatformUtility.platform_is_mac():
                container.wait_visibility(container)  # Mac removing this prevented the issue with the continue screen visibility
            container.attributes("-alpha", 1)

    def set_partial_screen_transparent(self):
        self.set_always_on_top()
        self.remove_title_bar()
        self.disable_resizing()
        for controller in self.containers:
            screenwidth = self.winfo_screenwidth()
            screenheight = self.winfo_screenheight()

            size_percentage = self.settings_manager.get_transparent_window_screen_size_percent()
            alpha = self.settings_manager.get_transparent_window_alpha_percent()
            window_width = int(screenwidth * size_percentage)
            window_height = int(screenheight * size_percentage)
            window_size = "{0}x{1}+0+0".format(window_width, window_height)
            controller.geometry(window_size)
            controller.attributes("-alpha", alpha)
        self.toggle_transparent_frame_position()

    def fade_app(self):
        for controller in self.containers:
            controller.attributes("-alpha", self.settings_manager.get_continue_screen_blocker_window_alpha_percent())

    def unfade_app(self):
        for controller in self.containers:
            controller.attributes("-alpha", 1)

    def toggle_transparent_frame_position(self, e=None):
        if self.state() == "withdrawn":
            return

        monitors = ScreenUtility.get_monitors_or_default(self)
        monitor = monitors[self.transparent_frame_monitor_index]

        screenwidth = monitor.width
        screenheight = monitor.height

        self.set_always_on_top()
        self.remove_title_bar()
        self.disable_resizing()

        size_percentage = self.settings_manager.get_transparent_window_screen_size_percent()

        window_width = int(screenwidth * size_percentage)
        window_height = int(screenheight * size_percentage)
        if self.transparent_frame_position_index == 0:
            self.transparent_frame_position = monitor.x + screenwidth - window_width
            self.transparent_frame_monitor_index = (self.transparent_frame_monitor_index + 1) % (monitors.__len__())
        else:
            self.transparent_frame_position = monitor.x + 0
        self.transparent_frame_position_index = (self.transparent_frame_position_index + 1) % 2

        bottom_left_screen = "{}x{}+{}+{}".format(window_width, window_height, self.transparent_frame_position, monitor.y +
                                                  screenheight - window_height)
        self.geometry(bottom_left_screen)

    def rewind_and_extend(self,minutes):
        self.extensions_used += 1
        self.mobber_manager.rewind_driver()
        result = self.show_transparent_countdown_frame(minutes)
        for minimal_frame in self.frames[MinimalScreenBlockerFrame]:
            minimal_frame.show_extend_time_button()
        return result

