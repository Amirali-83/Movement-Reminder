"""
Stand-up & Walk Reminder - Professional UI/UX Design
Modern dashboard layout with enhanced visual hierarchy and user experience.

Features:
- Professional two-column dashboard layout
- Enhanced visual hierarchy with prominent timer display
- NO ESMT LOGO (removed as requested)
- Standing icon used for both standing AND walking notifications
- Office stretches guide viewer button below statistics
- Responsive layout with scrolling for smaller screens
"""

import os
import sys
import time
import json
import threading
import platform
import ctypes
from tkinter import *
from tkinter import messagebox
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    WIN = platform.system() == "Windows"
except Exception:
    WIN = False


def lock_windows_screen():
    """Lock the Windows screen."""
    if WIN:
        try:
            ctypes.windll.user32.LockWorkStation()
        except Exception as e:
            messagebox.showerror("Error", f"Could not lock screen: {e}")


class Settings:
    """Manage persistent settings in user's home directory."""

    def __init__(self):
        self.config_dir = os.path.join(os.path.expanduser("~"), ".movement_reminder")
        self.config_file = os.path.join(self.config_dir, "settings.json")
        self.defaults = {
            "sit_mins": 45,
            "stand_mins": 10,
            "walk_mins": 5,
            "include_walk": False,
            "include_stand": True
        }
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
            except:
                pass

    def load(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return self.defaults.copy()

    def save(self, settings):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except:
            pass


class Phase:
    IDLE = "Idle"
    SITTING = "Sitting"
    STANDING = "Standing"
    WALKING = "Walking"


class TimerController:
    """Manages the timer logic with drift-free timing."""

    def __init__(self, on_tick, on_phase_complete):
        self.on_tick = on_tick
        self.on_phase_complete = on_phase_complete
        self.phase = Phase.IDLE
        self.sit_mins = 45
        self.stand_mins = 10
        self.walk_mins = 5
        self.include_walk = False
        self.include_stand = True
        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._end_time = None
        self._remaining_ms = 0
        self._running = False
        self._total_duration_ms = 0

    def configure(self, sit_mins, stand_mins, walk_mins, include_walk, include_stand):
        self.sit_mins = sit_mins
        self.stand_mins = stand_mins
        self.walk_mins = walk_mins
        self.include_walk = include_walk
        self.include_stand = include_stand

    def start(self):
        if self._running:
            self.stop()
        self._running = True
        self._stop_event.clear()
        self._pause_event.set()
        self._set_phase(Phase.SITTING, self.sit_mins)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        if self._running and not self._pause_event.is_set():
            self._end_time = time.time() * 1000 + self._remaining_ms
            self._pause_event.set()

    def stop(self):
        self._running = False
        self._stop_event.set()
        self._pause_event.set()
        if self._thread:
            self._thread.join(timeout=1)
        self.phase = Phase.IDLE
        self._remaining_ms = 0
        self.on_tick(self.phase, "00:00", 1.0)

    def _set_phase(self, phase, minutes):
        self.phase = phase
        duration_ms = max(1, minutes) * 60 * 1000
        self._end_time = time.time() * 1000 + duration_ms
        self._remaining_ms = duration_ms
        self._total_duration_ms = duration_ms

    def _run(self):
        while not self._stop_event.is_set():
            self._pause_event.wait()
            if self._stop_event.is_set():
                break
            now_ms = time.time() * 1000
            self._remaining_ms = max(0, self._end_time - now_ms)
            total_sec = int(self._remaining_ms / 1000)
            minutes = total_sec // 60
            seconds = total_sec % 60
            time_str = "{:02d}:{:02d}".format(minutes, seconds)
            progress = 1.0 - (self._remaining_ms / self._total_duration_ms) if self._total_duration_ms > 0 else 0
            self.on_tick(self.phase, time_str, progress)
            if self._remaining_ms <= 0:
                self._advance_phase()
            time.sleep(0.25)

    def _advance_phase(self):
        if self.phase == Phase.SITTING:
            if self.include_stand:
                next_phase = Phase.STANDING
                next_duration = self.stand_mins
            elif self.include_walk:
                next_phase = Phase.WALKING
                next_duration = self.walk_mins
            else:
                next_phase = Phase.SITTING
                next_duration = self.sit_mins
        elif self.phase == Phase.STANDING:
            if self.include_walk:
                next_phase = Phase.WALKING
                next_duration = self.walk_mins
            else:
                next_phase = Phase.SITTING
                next_duration = self.sit_mins
        elif self.phase == Phase.WALKING:
            next_phase = Phase.SITTING
            next_duration = self.sit_mins
        else:
            return
        self.on_phase_complete(next_phase, self.phase, next_duration)


class AnimatedHourglass(Canvas):
    """Enhanced hourglass with smooth sand animation."""

    def __init__(self, parent, size=180, **kwargs):
        Canvas.__init__(self, parent, width=size, height=size,
                        highlightthickness=0, bg=parent["bg"], **kwargs)
        self.hourglass_size = size
        self.progress = 0.0
        self._draw()

    def set_progress(self, progress):
        self.progress = progress
        self._draw()

    def _draw(self):
        self.delete("all")
        cx = self.hourglass_size / 2
        cy = self.hourglass_size / 2

        sand_color = "#F59E0B"
        frame_color = "#1E40AF"
        bg_color = "#F3F4F6"

        width = self.hourglass_size * 0.35
        height = self.hourglass_size * 0.65
        neck_width = self.hourglass_size * 0.08
        frame_thickness = 3

        top_y = cy - height / 2
        bottom_y = cy + height / 2

        shadow_offset = 2
        shadow_color = "#D1D5DB"

        self.create_rectangle(
            cx - width - frame_thickness + shadow_offset,
            top_y - frame_thickness * 2 + shadow_offset,
            cx + width + frame_thickness + shadow_offset,
            top_y + shadow_offset,
            fill=shadow_color, outline=""
        )

        self.create_rectangle(
            cx - width - frame_thickness, top_y - frame_thickness * 2,
            cx + width + frame_thickness, top_y,
            fill=frame_color, outline=""
        )

        self.create_rectangle(
            cx - width - frame_thickness, bottom_y,
            cx + width + frame_thickness, bottom_y + frame_thickness * 2,
            fill=frame_color, outline=""
        )

        self.create_rectangle(
            cx - width - frame_thickness, top_y,
            cx - width, bottom_y,
            fill=frame_color, outline=""
        )
        self.create_rectangle(
            cx + width, top_y,
            cx + width + frame_thickness, bottom_y,
            fill=frame_color, outline=""
        )

        self.create_polygon([
            cx - width, top_y,
            cx + width, top_y,
            cx + neck_width, cy,
            cx - neck_width, cy
        ], fill=bg_color, outline="")

        self.create_polygon([
            cx - neck_width, cy,
            cx + neck_width, cy,
            cx + width, bottom_y,
            cx - width, bottom_y
        ], fill=bg_color, outline="")

        top_chamber_height = cy - top_y
        slope = (width - neck_width) / top_chamber_height

        top_sand_height = (1.0 - self.progress) * (height / 2 - 10)
        if top_sand_height > 2:
            sand_y_start = top_y + 5
            sand_y_end = sand_y_start + top_sand_height
            distance_from_top_start = sand_y_start - top_y
            distance_from_top_end = sand_y_end - top_y
            sand_width_top = width - 5 - (slope * distance_from_top_start)
            sand_width_bottom = width - 5 - (slope * distance_from_top_end)
            sand_width_top = max(neck_width, sand_width_top)
            sand_width_bottom = max(neck_width, sand_width_bottom)
            self.create_polygon([
                cx - sand_width_top, sand_y_start,
                cx + sand_width_top, sand_y_start,
                cx + sand_width_bottom, sand_y_end,
                cx - sand_width_bottom, sand_y_end
            ], fill=sand_color, outline="")

        bottom_sand_height = self.progress * (height / 2 - 10)
        if bottom_sand_height > 2:
            sand_y_end = bottom_y - 5
            sand_y_start = sand_y_end - bottom_sand_height
            distance_from_center_start = sand_y_start - cy
            distance_from_center_end = sand_y_end - cy
            sand_width_top = neck_width + (slope * distance_from_center_start)
            sand_width_bottom = neck_width + (slope * distance_from_center_end)
            sand_width_top = min(width - 5, max(neck_width, sand_width_top))
            sand_width_bottom = min(width - 5, max(neck_width, sand_width_bottom))
            self.create_polygon([
                cx - sand_width_top, sand_y_start,
                cx + sand_width_top, sand_y_start,
                cx + sand_width_bottom, sand_y_end,
                cx - sand_width_bottom, sand_y_end
            ], fill=sand_color, outline="")

        self.create_line(cx - width, top_y, cx - neck_width, cy, fill=frame_color, width=2)
        self.create_line(cx + width, top_y, cx + neck_width, cy, fill=frame_color, width=2)
        self.create_line(cx - neck_width, cy, cx - width, bottom_y, fill=frame_color, width=2)
        self.create_line(cx + neck_width, cy, cx + width, bottom_y, fill=frame_color, width=2)


class ToggleSwitch(Canvas):
    """Modern toggle switch widget."""

    def __init__(self, parent, variable, command=None, **kwargs):
        Canvas.__init__(self, parent, width=50, height=26,
                        highlightthickness=0, bg=parent["bg"], **kwargs)
        self.variable = variable
        self.command = command
        self.bind("<Button-1>", self._toggle)
        self.variable.trace_add("write", lambda *args: self._draw())
        self._draw()

    def _toggle(self, event=None):
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        is_on = self.variable.get()

        if is_on:
            bg_color = "#10B981"
            knob_color = "#FFFFFF"
            knob_x = 37
        else:
            bg_color = "#D1D5DB"
            knob_color = "#FFFFFF"
            knob_x = 13

        self.create_oval(0, 0, 26, 26, fill=bg_color, outline="")
        self.create_oval(24, 0, 50, 26, fill=bg_color, outline="")
        self.create_rectangle(13, 0, 37, 26, fill=bg_color, outline="")

        self.create_oval(knob_x - 9, 4, knob_x + 11, 24, fill="#D1D5DB", outline="")
        self.create_oval(knob_x - 10, 3, knob_x + 10, 23, fill=knob_color, outline="")
        self.config(cursor="hand2")


class GradientButton(Canvas):
    """Enhanced button with hover effects and shadows."""

    def __init__(self, parent, text="", command=None,
                 gradient_start="#1d8c3f", gradient_end="#166d32",
                 fg="white", font=("Segoe UI", 11, "bold"),
                 width=140, height=45, **kwargs):
        Canvas.__init__(self, parent, width=width, height=height,
                        highlightthickness=0, bg=parent["bg"], **kwargs)
        self.text = text
        self.command = command
        self.gradient_start = gradient_start
        self.gradient_end = gradient_end
        self.fg = fg
        self.font = font
        self.width = width
        self.height = height
        self._state = NORMAL
        self._pressed = False
        self._hover = False

        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._draw()

    def _draw(self):
        self.delete("all")

        if self._state == DISABLED:
            start = "#9CA3AF"
            end = "#6B7280"
            text_color = "#D1D5DB"
        elif self._pressed:
            start = self.gradient_end
            end = self.gradient_start
            text_color = self.fg
        elif self._hover:
            start = self._lighten_color(self.gradient_start)
            end = self._lighten_color(self.gradient_end)
            text_color = self.fg
        else:
            start = self.gradient_start
            end = self.gradient_end
            text_color = self.fg

        if self._state == NORMAL and not self._pressed:
            shadow_color = "#D1D5DB"
            self.create_rectangle(2, 2, self.width, self.height,
                                fill=shadow_color, outline="")

        steps = 20
        for i in range(steps):
            ratio = i / steps
            color = self._interpolate_color(start, end, ratio)
            y1 = i * (self.height / steps)
            y2 = (i + 1) * (self.height / steps)
            offset = 2 if self._pressed else 0
            self.create_rectangle(offset, y1 + offset,
                                self.width - 2 + offset, y2 + offset,
                                fill=color, outline="")

        offset = 2 if self._pressed else 0
        self.create_text(
            self.width / 2 + offset, self.height / 2 + offset,
            text=self.text, fill=text_color, font=self.font
        )

        if self._hover and self._state == NORMAL:
            self.config(cursor="hand2")

    def _lighten_color(self, color):
        color = color.lstrip('#')
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))
        return f'#{r:02x}{g:02x}{b:02x}'

    def _interpolate_color(self, color1, color2, ratio):
        c1 = color1.lstrip('#')
        c2 = color2.lstrip('#')
        r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
        r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        return '#{:02x}{:02x}{:02x}'.format(r, g, b)

    def _on_click(self, event):
        if self._state == NORMAL:
            self._pressed = True
            self._draw()

    def _on_release(self, event):
        if self._state == NORMAL and self._pressed:
            self._pressed = False
            self._draw()
            if self.command:
                self.command()

    def _on_enter(self, event):
        if self._state == NORMAL:
            self._hover = True
            self._draw()

    def _on_leave(self, event):
        if self._pressed:
            self._pressed = False
        self._hover = False
        self._draw()
        self.config(cursor="")

    def config(self, **kwargs):
        if "state" in kwargs:
            self._state = kwargs["state"]
            self._draw()
        Canvas.config(self, **{k: v for k, v in kwargs.items() if k != "state"})


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class App:
    """Professional dashboard application."""

    def __init__(self, root):
        self.root = root
        self.root.title("Movement Reminder")
        self.root.geometry("900x650")
        self.root.minsize(700, 500)

        self.settings_mgr = Settings()
        self.settings = self.settings_mgr.load()
        self.daily_stats = {"sit_minutes": 0, "stand_minutes": 0, "walk_minutes": 0}

        self.bg_color = "#F3F4F6"
        self.card_bg = "#FFFFFF"
        self.card_shadow = "#E5E7EB"
        self.primary_color = "#1E40AF"
        self.accent_color = "#3B82F6"
        self.text_primary = "#111827"
        self.text_secondary = "#6B7280"
        self.text_light = "#9CA3AF"
        self.border_color = "#E5E7EB"

        self.root.configure(bg=self.bg_color)

        try:
            icon_path = resource_path("timer.png")
            if os.path.exists(icon_path):
                icon = PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon)
        except:
            pass

        self._build_ui()

        self.controller = TimerController(
            on_tick=self.on_timer_tick,
            on_phase_complete=self.on_phase_complete
        )

        self._is_paused = False
        self._notif_popup = None
        self._waiting_for_acknowledgment = False
        self._pending_phase = None
        self._pending_duration = None
        self._current_phase_before_popup = None

        self._update_button_states()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _create_card(self, parent, **kwargs):
        """Create a card with shadow effect."""
        shadow = Frame(parent, bg=self.card_shadow, **kwargs)
        card = Frame(shadow, bg=self.card_bg)
        card.pack(padx=(0, 2), pady=(0, 2), fill=BOTH, expand=True)
        return shadow, card

    def _build_ui(self):
        """Build the professional dashboard UI."""

        header_frame = Frame(self.root, bg=self.primary_color, height=80)
        header_frame.pack(fill=X, side=TOP)
        header_frame.pack_propagate(False)

        header_content = Frame(header_frame, bg=self.primary_color)
        header_content.pack(expand=True, fill=BOTH, padx=20, pady=15)

        # ═══════════════════════════════════════════════════════════════
        # CHANGE #1: NO ESMT LOGO - Title frame created directly
        # ═══════════════════════════════════════════════════════════════
        title_frame = Frame(header_content, bg=self.primary_color)
        title_frame.pack(side=LEFT, fill=BOTH, expand=True)

        Label(title_frame, text="Movement Reminder",
              bg=self.primary_color, fg="white",
              font=("Segoe UI", 24, "bold")).pack(anchor=W)

        Label(title_frame, text="Stay healthy with regular movement breaks",
              bg=self.primary_color, fg="#93C5FD",
              font=("Segoe UI", 11)).pack(anchor=W, pady=(2, 0))
        help_btn_frame = Frame(header_content, bg=self.primary_color)
        help_btn_frame.pack(side=RIGHT)

        self.help_btn = Canvas(help_btn_frame, width=40, height=40,
                               highlightthickness=0, bg=self.primary_color,
                               cursor="hand2")
        self.help_btn.pack()
        self.help_btn.create_oval(0, 0, 40, 40, fill="#3B82F6", outline="")
        self.help_btn.create_text(20, 20, text="?", fill="white",
                                  font=("Segoe UI", 20, "bold"))
        self.help_btn.bind("<Button-1>", lambda e: self._show_help())
        self._help_tooltip = None

        main_container = Frame(self.root, bg=self.bg_color)
        main_container.pack(fill=BOTH, expand=True)

        # Create canvas for scrolling
        canvas = Canvas(main_container, bg=self.bg_color, highlightthickness=0)
        scrollbar = Scrollbar(main_container, orient=VERTICAL, command=canvas.yview)
        scrollable_frame = Frame(canvas, bg=self.bg_color)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Enable mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Content frame inside scrollable area
        content_frame = Frame(scrollable_frame, bg=self.bg_color)
        content_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # LEFT COLUMN - Configuration only
        left_column = Frame(content_frame, bg=self.bg_color)
        left_column.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

        Label(left_column, text="⚙️ Configuration",
              bg=self.bg_color, fg=self.text_primary,
              font=("Segoe UI", 16, "bold")).pack(anchor=W, pady=(0, 12))

        settings_shadow, settings_card = self._create_card(left_column)
        settings_shadow.pack(fill=BOTH, expand=True)

        settings_inner = Frame(settings_card, bg=self.card_bg)
        settings_inner.pack(fill=BOTH, expand=True, padx=25, pady=25)

        self.sit_var = IntVar(value=self.settings.get("sit_mins", 45))
        self.stand_var = IntVar(value=self.settings.get("stand_mins", 10))
        self.walk_var = IntVar(value=self.settings.get("walk_mins", 5))
        self.walk_enabled = BooleanVar(value=self.settings.get("include_walk", False))
        self.stand_enabled = BooleanVar(value=self.settings.get("include_stand", True))

        self._create_setting_row(settings_inner, "💺 Sitting Duration",
                                 self.sit_var, "minutes", "Recommended: 45 minutes")

        self._create_setting_row(settings_inner, "🧍 Standing Duration",
                                 self.stand_var, "minutes", "Recommended: 10 minutes",
                                 toggle_var=self.stand_enabled, toggle_label="Enable standing phase")

        self._create_setting_row(settings_inner, "🚶 Walking Duration",
                                 self.walk_var, "minutes", "",
                                 toggle_var=self.walk_enabled, toggle_label="Enable walking phase")

        # RIGHT COLUMN - Timer, Stats, and Stretches Guide
        right_column = Frame(content_frame, bg=self.bg_color)
        right_column.pack(side=LEFT, fill=BOTH, expand=True, padx=(10, 0))

        # Create two sub-columns in right section
        right_top_frame = Frame(right_column, bg=self.bg_color)
        right_top_frame.pack(fill=BOTH, expand=True)

        # Timer section (left side of right column)
        timer_column = Frame(right_top_frame, bg=self.bg_color)
        timer_column.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

        Label(timer_column, text="⏱️ Timer",
              bg=self.bg_color, fg=self.text_primary,
              font=("Segoe UI", 16, "bold")).pack(anchor=W, pady=(0, 12))

        timer_shadow, timer_card = self._create_card(timer_column)
        timer_shadow.pack(fill=BOTH, expand=True)

        timer_inner = Frame(timer_card, bg=self.card_bg)
        timer_inner.pack(fill=BOTH, expand=True, padx=20, pady=20)

        self.phase_label = Label(timer_inner, text="Ready to start",
                                bg=self.card_bg, fg=self.accent_color,
                                font=("Segoe UI", 14, "bold"))
        self.phase_label.pack(pady=(0, 10))

        self.hourglass = AnimatedHourglass(timer_inner, size=100)
        self.hourglass.pack(pady=8)

        self.time_label = Label(timer_inner, text="00:00",
                               bg=self.card_bg, fg=self.primary_color,
                               font=("Consolas", 42, "bold"))
        self.time_label.pack(pady=10)

        btn_frame = Frame(timer_inner, bg=self.card_bg)
        btn_frame.pack(pady=(10, 0))

        self.start_btn = GradientButton(
            btn_frame, text="Start", command=self.start,
            gradient_start="#10B981", gradient_end="#059669",
            width=100, height=38
        )
        self.start_btn.grid(row=0, column=0, padx=3, pady=2)

        self.pause_btn = GradientButton(
            btn_frame, text="Pause", command=self.pause,
            gradient_start="#F59E0B", gradient_end="#D97706",
            width=100, height=38
        )
        self.pause_btn.grid(row=0, column=1, padx=3, pady=2)

        self.resume_btn = GradientButton(
            btn_frame, text="Resume", command=self.resume,
            gradient_start="#3B82F6", gradient_end="#1D4ED8",
            width=100, height=38
        )
        self.resume_btn.grid(row=0, column=2, padx=3, pady=2)

        self.reset_btn = GradientButton(
            btn_frame, text="Reset", command=self.reset,
            gradient_start="#EF4444", gradient_end="#DC2626",
            width=100, height=38
        )
        self.reset_btn.grid(row=1, column=0, columnspan=2, padx=3, pady=2, sticky="ew")

        self.walk_now_btn = GradientButton(
            btn_frame, text="🚶 Walk", command=self.walk_now,
            gradient_start="#8B5CF6", gradient_end="#7C3AED",
            width=100, height=38
        )
        self.walk_now_btn.grid(row=1, column=2, padx=3, pady=2)

        # Stats and Stretches column (right side of right column)
        stats_column = Frame(right_top_frame, bg=self.bg_color)
        stats_column.pack(side=LEFT, fill=BOTH, expand=True, padx=(10, 0))

        # Today's Activity section
        Label(stats_column, text="📊 Today's Activity",
              bg=self.bg_color, fg=self.text_primary,
              font=("Segoe UI", 16, "bold")).pack(anchor=W, pady=(0, 12))

        stats_shadow, stats_card = self._create_card(stats_column)
        stats_shadow.pack(fill=X, pady=(0, 20))

        stats_inner = Frame(stats_card, bg=self.card_bg)
        stats_inner.pack(fill=BOTH, expand=True, padx=15, pady=15)

        stats_grid = Frame(stats_inner, bg=self.card_bg)
        stats_grid.pack(fill=X)

        for i, (emoji, label, attr) in enumerate([
            ("💺", "Sitting", "sit"),
            ("🧍", "Standing", "stand"),
            ("🚶", "Walking", "walk")
        ]):
            stat_box = Frame(stats_grid, bg="#F9FAFB",
                           highlightbackground=self.border_color,
                           highlightthickness=1)
            stat_box.grid(row=i, column=0, pady=3, sticky="ew")
            stats_grid.columnconfigure(0, weight=1)

            inner_frame = Frame(stat_box, bg="#F9FAFB")
            inner_frame.pack(fill=X, padx=10, pady=8)

            Label(inner_frame, text=emoji, bg="#F9FAFB",
                 font=("Segoe UI", 16)).pack(side=LEFT, padx=(0, 8))

            text_frame = Frame(inner_frame, bg="#F9FAFB")
            text_frame.pack(side=LEFT, fill=X, expand=True)

            Label(text_frame, text=label, bg="#F9FAFB",
                 fg=self.text_secondary,
                 font=("Segoe UI", 9), anchor=W).pack(fill=X)

            stat_label = Label(text_frame, text="0 min", bg="#F9FAFB",
                             fg=self.text_primary,
                             font=("Segoe UI", 14, "bold"), anchor=W)
            stat_label.pack(fill=X)

            setattr(self, f"{attr}_stat_label", stat_label)

        # Office Stretches Guide button
        stretches_btn = GradientButton(
            stats_column, text="🤸 Office Stretches Guide",
            command=self._show_stretches_guide,
            gradient_start="#14B8A6", gradient_end="#0D9488",
            width=255, height=42,
            font=("Segoe UI", 11, "bold")
        )
        stretches_btn.pack(fill=X, pady=(0, 10))

        # Eye Rest Exercises button
        eye_rest_btn = GradientButton(
            stats_column, text="\u2003👁 Eye Rest Exercises (20-20-20)️",
            command=self._show_eye_rest_guide,
            gradient_start="#14B8A6", gradient_end="#0D9488",
            width=255, height=42,
            font=("Segoe UI", 11, "bold")
        )
        eye_rest_btn.pack(fill=X, pady=(0, 10))

        # Activity Chart button
        chart_btn = GradientButton(
            stats_column, text="📊 View Activity Chart",
            command=self._show_activity_chart,
            gradient_start="#8B5CF6", gradient_end="#7C3AED",
            width=255, height=42,
            font=("Segoe UI", 11, "bold")
        )
        chart_btn.pack(fill=X, pady=(0, 10))

    def _show_activity_chart(self):
        """Display today's activity as a pie chart in a new window."""
        chart_window = Toplevel(self.root)
        chart_window.title("Today's Activity Chart")
        chart_window.configure(bg=self.bg_color)
        chart_window.geometry("700x600")

        chart_window.update_idletasks()
        x = (chart_window.winfo_screenwidth() // 2) - 350
        y = (chart_window.winfo_screenheight() // 2) - 300
        chart_window.geometry(f"700x600+{x}+{y}")

        # Header
        header = Frame(chart_window, bg=self.primary_color, height=60)
        header.pack(fill=X, side=TOP)
        header.pack_propagate(False)

        header_content = Frame(header, bg=self.primary_color)
        header_content.pack(fill=BOTH, expand=True, padx=20)

        Label(header_content, text="📊 Today's Activity Distribution",
              bg=self.primary_color, fg="white",
              font=("Segoe UI", 18, "bold")).pack(side=LEFT, expand=True)

        # Main content
        content_frame = Frame(chart_window, bg=self.card_bg)
        content_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # Get the activity data
        sit_mins = self.daily_stats["sit_minutes"]
        stand_mins = self.daily_stats["stand_minutes"]
        walk_mins = self.daily_stats["walk_minutes"]
        total_mins = sit_mins + stand_mins + walk_mins

        # Create the pie chart
        fig = Figure(figsize=(8, 6), facecolor=self.card_bg)
        ax = fig.add_subplot(111)

        if total_mins > 0:
            # Data for pie chart
            sizes = [sit_mins, stand_mins, walk_mins]
            colors = ['#EF4444', '#10B981', '#3B82F6']  # Red, Green, Blue
            explode = (0.05, 0.05, 0.05)  # Slightly separate all slices

            # Custom autopct function to add emojis
            emojis = ['💺', '🧍', '🚶']

            def make_autopct(emoji):
                def my_autopct(pct):
                    return f'{emoji} {pct:.1f}%'

                return my_autopct

            # Create pie chart with emoji percentages
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=None,  # No labels
                colors=colors,
                autopct=lambda
                    pct: f'{emojis[0] if pct > sizes[1] / total_mins * 100 and pct > sizes[2] / total_mins * 100 else (emojis[1] if pct > sizes[2] / total_mins * 100 and pct < sizes[0] / total_mins * 100 else emojis[2])} {pct:.1f}%',
                startangle=90,
                explode=explode,
                shadow=True,
                textprops={'fontsize': 13, 'weight': 'bold'}
            )

            # Better approach - manually set the text for each wedge
            sit_pct = (sit_mins / total_mins) * 100
            stand_pct = (stand_mins / total_mins) * 100
            walk_pct = (walk_mins / total_mins) * 100

            autopct_texts = [f'💺 {sit_pct:.1f}%', f'🧍 {stand_pct:.1f}%', f'🚶 {walk_pct:.1f}%']

            for i, autotext in enumerate(autotexts):
                autotext.set_text(autopct_texts[i])
                autotext.set_color('white')
                autotext.set_fontsize(13)
                autotext.set_weight('bold')

            ax.axis('equal')  # Equal aspect ratio ensures circular pie

            # Add title
            ax.set_title(f'Total Active Time: {total_mins} minutes',
                         fontsize=14, weight='bold', color=self.text_primary, pad=20)
        else:
            # No data yet
            ax.text(0.5, 0.5, 'No activity data yet\n\nStart the timer to begin tracking!',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes,
                    fontsize=16,
                    color=self.text_secondary,
                    weight='bold')
            ax.axis('off')

        # Embed the chart in tkinter
        canvas = FigureCanvasTkAgg(fig, content_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=True, pady=10)

        # Statistics summary below chart
        summary_frame = Frame(content_frame, bg=self.card_bg)
        summary_frame.pack(fill=X, pady=(10, 0))

        if total_mins > 0:
            # Calculate percentages
            sit_pct = (sit_mins / total_mins) * 100
            stand_pct = (stand_mins / total_mins) * 100
            walk_pct = (walk_mins / total_mins) * 100

            summary_text = f"💺 Sitting: {sit_mins} min ({sit_pct:.1f}%)  |  🧍 Standing: {stand_mins} min ({stand_pct:.1f}%)  |  🚶 Walking: {walk_mins} min ({walk_pct:.1f}%)"
        else:
            summary_text = "Start your movement timer to see activity breakdown"

        Label(summary_frame, text=summary_text,
              bg=self.card_bg, fg=self.text_secondary,
              font=("Segoe UI", 11, "bold")).pack(pady=10)

        # Close button
        btn_frame = Frame(chart_window, bg=self.bg_color)
        btn_frame.pack(fill=X, padx=20, pady=(0, 20))

        close_btn = GradientButton(
            btn_frame, text="Close", command=chart_window.destroy,
            gradient_start="#6B7280", gradient_end="#4B5563",
            width=150, height=40
        )
        close_btn.pack(side=RIGHT)

    def _create_setting_row(self, parent, label_text, value_var, unit,
                           help_text="", toggle_var=None, toggle_label=""):
        """Create a setting row with label, input, and optional toggle."""
        row_frame = Frame(parent, bg=self.card_bg)
        row_frame.pack(fill=X, pady=(0, 20))

        Label(row_frame, text=label_text, bg=self.card_bg,
             fg=self.text_primary,
             font=("Segoe UI", 12, "bold")).pack(anchor=W, pady=(0, 8))

        input_frame = Frame(row_frame, bg=self.card_bg)
        input_frame.pack(anchor=W, pady=(0, 5))

        entry = Entry(input_frame, textvariable=value_var,
                     bg="#F9FAFB", fg=self.text_primary,
                     font=("Segoe UI", 14, "bold"), width=8,
                     justify=CENTER, relief=SOLID, borderwidth=1,
                     insertbackground=self.accent_color,
                     highlightthickness=1, highlightcolor=self.accent_color,
                     highlightbackground=self.border_color)
        entry.pack(side=LEFT, padx=(0, 10))
        value_var.trace_add("write", lambda *args: self._save_settings())

        Label(input_frame, text=unit, bg=self.card_bg,
             fg=self.text_secondary,
             font=("Segoe UI", 11)).pack(side=LEFT)

        if help_text:
            Label(row_frame, text=help_text, bg=self.card_bg,
                 fg=self.text_light,
                 font=("Segoe UI", 9)).pack(anchor=W, pady=(0, 8))

        if toggle_var:
            toggle_frame = Frame(row_frame, bg=self.card_bg)
            toggle_frame.pack(anchor=W)

            toggle = ToggleSwitch(toggle_frame, toggle_var,
                                command=self._save_settings)
            toggle.pack(side=LEFT, padx=(0, 10))

            Label(toggle_frame, text=toggle_label, bg=self.card_bg,
                 fg=self.text_secondary,
                 font=("Segoe UI", 10)).pack(side=LEFT)

    def _show_stretches_guide(self):
        """Display the office stretches guide in a new window with zoom capability."""
        stretches_path = resource_path("office-stretches.png")

        if not os.path.exists(stretches_path):
            messagebox.showwarning(
                "Image Not Found",
                "The office-stretches.png file could not be found.\n\n"
                "Please ensure the file is in the same directory as the application.",
                parent=self.root
            )
            return

        stretches_window = Toplevel(self.root)
        stretches_window.title("Office Stretches Guide")
        stretches_window.configure(bg=self.bg_color)

        # Start with a good default size
        stretches_window.geometry("1000x700")
        stretches_window.update_idletasks()

        x = (stretches_window.winfo_screenwidth() // 2) - 500
        y = (stretches_window.winfo_screenheight() // 2) - 350
        stretches_window.geometry(f"1000x700+{x}+{y}")

        header = Frame(stretches_window, bg=self.primary_color, height=60)
        header.pack(fill=X, side=TOP)
        header.pack_propagate(False)

        header_content = Frame(header, bg=self.primary_color)
        header_content.pack(fill=BOTH, expand=True, padx=20)

        Label(header_content, text="🤸 Office Stretches Guide",
              bg=self.primary_color, fg="white",
              font=("Segoe UI", 18, "bold")).pack(side=LEFT, expand=True)

        # Zoom controls in header
        zoom_frame = Frame(header_content, bg=self.primary_color)
        zoom_frame.pack(side=RIGHT)

        zoom_state = {"scale": 0.5, "original_img": None, "display_img": None, "canvas_img_id": None}

        def update_zoom():
            if zoom_state["original_img"] and zoom_state["canvas_img_id"]:
                orig = zoom_state["original_img"]
                scale = zoom_state["scale"]

                # Always use subsample for scaling
                if scale < 1.0:
                    factor = max(1, int(1.0 / scale))
                    zoomed = orig.subsample(factor, factor)
                else:
                    # At 100%, show original image
                    zoomed = orig

                zoom_state["display_img"] = zoomed
                canvas.itemconfig(zoom_state["canvas_img_id"], image=zoomed)
                canvas.configure(scrollregion=canvas.bbox("all"))
                zoom_label.config(text=f"{int(scale * 100)}%")

        def zoom_in():
            zoom_state["scale"] = min(1.0, zoom_state["scale"] + 0.25)
            update_zoom()

        def zoom_out():
            zoom_state["scale"] = max(0.25, zoom_state["scale"] - 0.25)
            update_zoom()

        def zoom_reset():
            zoom_state["scale"] = 0.5
            update_zoom()

        # Zoom buttons
        zoom_out_btn = Canvas(zoom_frame, width=30, height=30,
                             highlightthickness=0, bg=self.primary_color,
                             cursor="hand2")
        zoom_out_btn.pack(side=LEFT, padx=2)
        zoom_out_btn.create_oval(2, 2, 28, 28, fill="#3B82F6", outline="")
        zoom_out_btn.create_text(15, 15, text="−", fill="white",
                                font=("Segoe UI", 16, "bold"))
        zoom_out_btn.bind("<Button-1>", lambda e: zoom_out())

        zoom_label = Label(zoom_frame, text="100%",
                          bg=self.primary_color, fg="white",
                          font=("Segoe UI", 11, "bold"), width=6)
        zoom_label.pack(side=LEFT, padx=5)

        zoom_in_btn = Canvas(zoom_frame, width=30, height=30,
                            highlightthickness=0, bg=self.primary_color,
                            cursor="hand2")
        zoom_in_btn.pack(side=LEFT, padx=2)
        zoom_in_btn.create_oval(2, 2, 28, 28, fill="#3B82F6", outline="")
        zoom_in_btn.create_text(15, 15, text="+", fill="white",
                               font=("Segoe UI", 16, "bold"))
        zoom_in_btn.bind("<Button-1>", lambda e: zoom_in())

        reset_btn = Canvas(zoom_frame, width=30, height=30,
                          highlightthickness=0, bg=self.primary_color,
                          cursor="hand2")
        reset_btn.pack(side=LEFT, padx=(10, 0))
        reset_btn.create_oval(2, 2, 28, 28, fill="#3B82F6", outline="")
        reset_btn.create_text(15, 15, text="⟲", fill="white",
                             font=("Segoe UI", 14, "bold"))
        reset_btn.bind("<Button-1>", lambda e: zoom_reset())

        content_frame = Frame(stretches_window, bg=self.card_bg)
        content_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # Canvas with scrollbars for zooming
        canvas = Canvas(content_frame, bg=self.card_bg, highlightthickness=0)
        v_scrollbar = Scrollbar(content_frame, orient=VERTICAL, command=canvas.yview)
        h_scrollbar = Scrollbar(content_frame, orient=HORIZONTAL, command=canvas.xview)

        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        v_scrollbar.pack(side=RIGHT, fill=Y)
        h_scrollbar.pack(side=BOTTOM, fill=X)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)

        try:
            # Load original image
            stretches_img = PhotoImage(file=stretches_path)
            stretches_window.stretches_image = stretches_img
            zoom_state["original_img"] = stretches_img

            # Set initial scale to 50%
            zoom_state["scale"] = 0.5

            # Create display image at 50% scale
            factor = 2  # subsample by 2 for 50%
            display_img = stretches_img.subsample(factor, factor)
            zoom_state["display_img"] = display_img

            # Display image centered
            canvas.update()
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()

            img_id = canvas.create_image(
                canvas_width // 2, canvas_height // 2,
                anchor=CENTER, image=zoom_state["display_img"]
            )
            zoom_state["canvas_img_id"] = img_id

            canvas.configure(scrollregion=canvas.bbox("all"))
            zoom_label.config(text="50%")

            # Mouse wheel zoom
            def on_mousewheel(event):
                if event.state & 0x0004:  # Ctrl key is pressed
                    if event.delta > 0:
                        zoom_in()
                    else:
                        zoom_out()
                else:
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")

            canvas.bind_all("<MouseWheel>", on_mousewheel)

            def on_closing():
                canvas.unbind_all("<MouseWheel>")
                stretches_window.destroy()

            stretches_window.protocol("WM_DELETE_WINDOW", on_closing)

        except Exception as e:
            messagebox.showerror(
                "Error Loading Image",
                f"Could not load the stretches guide image:\n{str(e)}",
                parent=stretches_window
            )
            stretches_window.destroy()
            return

        btn_frame = Frame(stretches_window, bg=self.bg_color)
        btn_frame.pack(fill=X, padx=20, pady=(0, 20))

        info_label = Label(btn_frame,
                          text="💡 Tip: Use Ctrl+Scroll or the +/− buttons to zoom",
                          bg=self.bg_color, fg=self.text_secondary,
                          font=("Segoe UI", 9))
        info_label.pack(side=LEFT, padx=10)

        close_btn = GradientButton(
            btn_frame, text="Close", command=stretches_window.destroy,
            gradient_start="#6B7280", gradient_end="#4B5563",
            width=150, height=40
        )
        close_btn.pack(side=RIGHT)

    def _show_eye_rest_guide(self):
        """Display the eye rest exercises guide in a new window with zoom capability."""
        eye_rest_path = resource_path("eyerest.png")

        if not os.path.exists(eye_rest_path):
            messagebox.showwarning(
                "Image Not Found",
                "The eyerest.png file could not be found.\n\n"
                "Please ensure the file is in the same directory as the application.",
                parent=self.root
            )
            return

        eye_window = Toplevel(self.root)
        eye_window.title("Eye Rest Exercises (20-20-20 Rule)")
        eye_window.configure(bg=self.bg_color)

        # Start with a good default size
        eye_window.geometry("1000x700")
        eye_window.update_idletasks()

        x = (eye_window.winfo_screenwidth() // 2) - 500
        y = (eye_window.winfo_screenheight() // 2) - 350
        eye_window.geometry(f"1000x700+{x}+{y}")

        header = Frame(eye_window, bg=self.primary_color, height=60)
        header.pack(fill=X, side=TOP)
        header.pack_propagate(False)

        header_content = Frame(header, bg=self.primary_color)
        header_content.pack(fill=BOTH, expand=True, padx=20)

        Label(header_content, text="👁️ Eye Rest Exercises (20-20-20 Rule)",
              bg=self.primary_color, fg="white",
              font=("Segoe UI", 18, "bold")).pack(side=LEFT, expand=True)

        # Zoom controls in header
        zoom_frame = Frame(header_content, bg=self.primary_color)
        zoom_frame.pack(side=RIGHT)

        zoom_state = {"scale": 0.75, "original_img": None, "display_img": None, "canvas_img_id": None}

        def update_zoom():
            if zoom_state["original_img"] and zoom_state["canvas_img_id"]:
                orig = zoom_state["original_img"]
                scale = zoom_state["scale"]

                if scale == 1.0:
                    # Show original image at 100%
                    zoomed = orig
                elif scale == 0.75:
                    # For 75%, manually subsample
                    zoomed = orig.subsample(1, 1)  # Show at near-original, will look like 75%
                elif scale == 0.5:
                    # For 50%, subsample by 2
                    zoomed = orig.subsample(2, 2)
                elif scale == 0.25:
                    # For 25%, subsample by 4
                    zoomed = orig.subsample(4, 4)
                else:
                    # Fallback
                    factor = max(1, int(1.0 / scale))
                    zoomed = orig.subsample(factor, factor)

                zoom_state["display_img"] = zoomed
                canvas.itemconfig(zoom_state["canvas_img_id"], image=zoomed)
                canvas.configure(scrollregion=canvas.bbox("all"))
                zoom_label.config(text=f"{int(scale * 100)}%")

        def zoom_in():
            zoom_state["scale"] = min(1.0, zoom_state["scale"] + 0.25)
            update_zoom()

        def zoom_out():
            zoom_state["scale"] = max(0.25, zoom_state["scale"] - 0.25)
            update_zoom()

        def zoom_reset():
            zoom_state["scale"] = 0.75
            update_zoom()

        # Zoom buttons
        zoom_out_btn = Canvas(zoom_frame, width=30, height=30,
                             highlightthickness=0, bg=self.primary_color,
                             cursor="hand2")
        zoom_out_btn.pack(side=LEFT, padx=2)
        zoom_out_btn.create_oval(2, 2, 28, 28, fill="#3B82F6", outline="")
        zoom_out_btn.create_text(15, 15, text="−", fill="white",
                                font=("Segoe UI", 16, "bold"))
        zoom_out_btn.bind("<Button-1>", lambda e: zoom_out())

        zoom_label = Label(zoom_frame, text="75%",
                          bg=self.primary_color, fg="white",
                          font=("Segoe UI", 11, "bold"), width=6)
        zoom_label.pack(side=LEFT, padx=5)

        zoom_in_btn = Canvas(zoom_frame, width=30, height=30,
                            highlightthickness=0, bg=self.primary_color,
                            cursor="hand2")
        zoom_in_btn.pack(side=LEFT, padx=2)
        zoom_in_btn.create_oval(2, 2, 28, 28, fill="#3B82F6", outline="")
        zoom_in_btn.create_text(15, 15, text="+", fill="white",
                               font=("Segoe UI", 16, "bold"))
        zoom_in_btn.bind("<Button-1>", lambda e: zoom_in())

        reset_btn = Canvas(zoom_frame, width=30, height=30,
                          highlightthickness=0, bg=self.primary_color,
                          cursor="hand2")
        reset_btn.pack(side=LEFT, padx=(10, 0))
        reset_btn.create_oval(2, 2, 28, 28, fill="#3B82F6", outline="")
        reset_btn.create_text(15, 15, text="⟲", fill="white",
                             font=("Segoe UI", 14, "bold"))
        reset_btn.bind("<Button-1>", lambda e: zoom_reset())

        content_frame = Frame(eye_window, bg=self.card_bg)
        content_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # Canvas with scrollbars for zooming
        canvas = Canvas(content_frame, bg=self.card_bg, highlightthickness=0)
        v_scrollbar = Scrollbar(content_frame, orient=VERTICAL, command=canvas.yview)
        h_scrollbar = Scrollbar(content_frame, orient=HORIZONTAL, command=canvas.xview)

        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        v_scrollbar.pack(side=RIGHT, fill=Y)
        h_scrollbar.pack(side=BOTTOM, fill=X)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)

        try:
            # Load original image
            eye_img = PhotoImage(file=eye_rest_path)
            eye_window.eye_image = eye_img
            zoom_state["original_img"] = eye_img

            # Set initial scale to 75%
            zoom_state["scale"] = 0.75

            # Create display image at 75% scale - show original for now
            display_img = eye_img.subsample(1, 1)
            zoom_state["display_img"] = display_img

            # Display image centered
            canvas.update()
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()

            img_id = canvas.create_image(
                canvas_width // 2, canvas_height // 2,
                anchor=CENTER, image=zoom_state["display_img"]
            )
            zoom_state["canvas_img_id"] = img_id

            canvas.configure(scrollregion=canvas.bbox("all"))
            zoom_label.config(text="75%")

            # Mouse wheel zoom
            def on_mousewheel(event):
                if event.state & 0x0004:  # Ctrl key is pressed
                    if event.delta > 0:
                        zoom_in()
                    else:
                        zoom_out()
                else:
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")

            canvas.bind_all("<MouseWheel>", on_mousewheel)

            def on_closing():
                canvas.unbind_all("<MouseWheel>")
                eye_window.destroy()

            eye_window.protocol("WM_DELETE_WINDOW", on_closing)

        except Exception as e:
            messagebox.showerror(
                "Error Loading Image",
                f"Could not load the eye rest guide image:\n{str(e)}",
                parent=eye_window
            )
            eye_window.destroy()
            return

        btn_frame = Frame(eye_window, bg=self.bg_color)
        btn_frame.pack(fill=X, padx=20, pady=(0, 10))

        info_label = Label(btn_frame,
                          text="💡 Tip: Use Ctrl+Scroll or the +/− buttons to zoom",
                          bg=self.bg_color, fg=self.text_secondary,
                          font=("Segoe UI", 9))
        info_label.pack(side=LEFT, padx=10)

        close_btn = GradientButton(
            btn_frame, text="Close", command=eye_window.destroy,
            gradient_start="#6B7280", gradient_end="#4B5563",
            width=150, height=40
        )
        close_btn.pack(side=RIGHT)

        # Add distance conversion note at the bottom
        note_frame = Frame(eye_window, bg=self.bg_color)
        note_frame.pack(fill=X, padx=20, pady=(0, 20))

        note_text = "📏 20 feet = 6 meters | Look at something 20 feet (6 meters) away for 20 seconds every 20 minutes"
        note_label = Label(note_frame, text=note_text,
                          bg=self.bg_color, fg=self.text_primary,
                          font=("Segoe UI", 10, "bold"),
                          wraplength=950, justify=CENTER)
        note_label.pack()

    def _save_settings(self):
        try:
            self.settings = {
                "sit_mins": self.sit_var.get(),
                "stand_mins": self.stand_var.get(),
                "walk_mins": self.walk_var.get(),
                "include_walk": self.walk_enabled.get(),
                "include_stand": self.stand_enabled.get()
            }
            self.settings_mgr.save(self.settings)
        except:
            pass

    def _update_button_states(self):
        is_running = self.controller._running

        if not is_running:
            self.start_btn.config(state=NORMAL)
            self.pause_btn.config(state=DISABLED)
            self.resume_btn.config(state=DISABLED)
            self.reset_btn.config(state=DISABLED)
        elif self._is_paused:
            self.start_btn.config(state=DISABLED)
            self.pause_btn.config(state=DISABLED)
            self.resume_btn.config(state=NORMAL)
            self.reset_btn.config(state=NORMAL)
        else:
            self.start_btn.config(state=DISABLED)
            self.pause_btn.config(state=NORMAL)
            self.resume_btn.config(state=DISABLED)
            self.reset_btn.config(state=NORMAL)

    def on_timer_tick(self, phase, time_str, progress):
        def update():
            if phase == Phase.IDLE:
                self.phase_label.config(text="Ready to start")
            else:
                self.phase_label.config(text=phase)
            self.time_label.config(text=time_str)
            self.hourglass.set_progress(progress)
        self.root.after(0, update)

    def on_phase_complete(self, new_phase, old_phase, duration):
        if old_phase == Phase.SITTING:
            self.daily_stats["sit_minutes"] += self.sit_var.get()
        elif old_phase == Phase.STANDING:
            self.daily_stats["stand_minutes"] += self.stand_var.get()
        elif old_phase == Phase.WALKING:
            self.daily_stats["walk_minutes"] += self.walk_var.get()

        self.sit_stat_label.config(text=f"{self.daily_stats['sit_minutes']} min")
        self.stand_stat_label.config(text=f"{self.daily_stats['stand_minutes']} min")
        self.walk_stat_label.config(text=f"{self.daily_stats['walk_minutes']} min")

        def show():
            self._pending_phase = new_phase
            self._pending_duration = duration
            self._current_phase_before_popup = old_phase
            self._waiting_for_acknowledgment = True
            self.controller.pause()
            self._show_notification(new_phase, old_phase)
        self.root.after(0, show)

    def start(self):
        self._save_settings()
        self.controller.configure(
            self.sit_var.get(), self.stand_var.get(), self.walk_var.get(),
            self.walk_enabled.get(), self.stand_enabled.get()
        )
        self.controller.start()
        self._is_paused = False
        self._update_button_states()

    def pause(self):
        self.controller.pause()
        self._is_paused = True
        self._update_button_states()

    def resume(self):
        self.controller.resume()
        self._is_paused = False
        self._update_button_states()

    def reset(self):
        self.controller.stop()
        self._is_paused = False
        self._update_button_states()
        self._close_notification()

    def walk_now(self):
        mins = self.walk_var.get()

        # Check if timer is currently running and pause it
        was_running = self.controller._running and not self._is_paused
        if was_running:
            self.controller.pause()
            self._is_paused = True
            self._update_button_states()

        walk_popup = Toplevel(self.root)
        walk_popup.title("Walk Timer")
        walk_popup.configure(bg=self.bg_color)
        walk_popup.geometry("450x320")
        walk_popup.resizable(False, False)
        walk_popup.attributes("-topmost", True)

        walk_popup.update_idletasks()
        x = (walk_popup.winfo_screenwidth() // 2) - 225
        y = (walk_popup.winfo_screenheight() // 2) - 160
        walk_popup.geometry(f"450x320+{x}+{y}")

        content = Frame(walk_popup, bg=self.card_bg)
        content.pack(fill=BOTH, expand=True, padx=15, pady=15)

        Label(content, text="🚶 Walk Time!", bg=self.card_bg,
              fg=self.accent_color,
              font=("Segoe UI", 22, "bold")).pack(pady=(20, 10))

        time_display = Label(content, text=f"{mins:02d}:00",
                             bg=self.card_bg, fg=self.primary_color,
                             font=("Consolas", 48, "bold"))
        time_display.pack(pady=(10, 20))

        def on_walk_complete():
            """Handle walk completion - update stats and resume timer"""
            # Add walk time to daily statistics
            self.daily_stats["walk_minutes"] += mins
            self.walk_stat_label.config(text=f"{self.daily_stats['walk_minutes']} min")

            # Resume the main timer if it was running
            if was_running:
                self.controller.resume()
                self._is_paused = False
                self._update_button_states()

            walk_popup.destroy()
            messagebox.showinfo("Walk Complete",
                                "Great job! Walk complete.",
                                parent=self.root)

        def on_walk_cancel():
            """Handle walk cancellation - resume timer without updating stats"""
            if was_running:
                self.controller.resume()
                self._is_paused = False
                self._update_button_states()
            walk_popup.destroy()

        def update_walk_timer():
            remaining = [mins * 60]

            def countdown():
                if remaining[0] > 0 and walk_popup.winfo_exists():
                    mins_left = remaining[0] // 60
                    secs_left = remaining[0] % 60
                    time_display.config(text=f"{mins_left:02d}:{secs_left:02d}")
                    remaining[0] -= 1
                    walk_popup.after(1000, countdown)
                elif remaining[0] == 0 and walk_popup.winfo_exists():
                    on_walk_complete()

            countdown()

        btn_frame = Frame(content, bg=self.card_bg)
        btn_frame.pack(pady=(10, 10))

        cancel_btn = GradientButton(
            btn_frame, text="Cancel", command=on_walk_cancel,
            gradient_start="#EF4444", gradient_end="#DC2626",
            width=130, height=45
        )
        cancel_btn.pack(side=LEFT, padx=5)

        if WIN:
            def lock_and_start():
                walk_popup.after(100, update_walk_timer)
                walk_popup.after(500, lock_windows_screen)

            lock_btn = GradientButton(
                btn_frame, text="🔒 Lock & Walk", command=lock_and_start,
                gradient_start="#3B82F6", gradient_end="#1D4ED8",
                width=150, height=45
            )
            lock_btn.pack(side=LEFT, padx=5)
        else:
            walk_popup.after(100, update_walk_timer)

        # Handle window close button (X)
        walk_popup.protocol("WM_DELETE_WINDOW", on_walk_cancel)

    def _show_notification(self, phase, old_phase):
        """Show notification with standing icon for both standing and walking."""
        if self._notif_popup:
            return

        # Check if screen sharing is active (Windows only)
        if WIN:
            try:
                import win32gui
                import win32con

                def is_sharing_screen():
                    # Check for common screen sharing window titles
                    sharing_keywords = [
                        "is sharing", "screen share", "presenting",
                        "zoom meeting", "teams meeting", "webex",
                        "google meet", "sharing screen"
                    ]

                    def callback(hwnd, windows):
                        if win32gui.IsWindowVisible(hwnd):
                            title = win32gui.GetWindowText(hwnd).lower()
                            for keyword in sharing_keywords:
                                if keyword in title:
                                    windows.append(True)
                                    return False
                        return True

                    windows = []
                    try:
                        win32gui.EnumWindows(callback, windows)
                        return len(windows) > 0
                    except:
                        return False

                # If screen sharing detected, don't show popup
                if is_sharing_screen():
                    # Auto-accept the phase change silently
                    self.controller._set_phase(self._pending_phase,
                                              self._pending_duration)
                    self.controller.resume()
                    self._is_paused = False
                    self._update_button_states()
                    self._waiting_for_acknowledgment = False
                    self._pending_phase = None
                    self._pending_duration = None
                    self._current_phase_before_popup = None
                    return
            except ImportError:
                pass  # win32gui not available, continue with normal notification
            except:
                pass  # Any error, continue with normal notification

        messages = {
            Phase.STANDING: ("Time to stand up!",
                           f"Stand for {self.stand_var.get()} minute(s)."),
            Phase.WALKING: ("Quick walk 🚶",
                          f"Walk for {self.walk_var.get()} minute(s)."),
            Phase.SITTING: ("You can sit again",
                          f"Next sit: {self.sit_var.get()} minute(s).")
        }

        title, body = messages.get(phase, ("Phase change", ""))

        # Get all monitors and show notification on each
        self._notif_popup = []

        try:
            from screeninfo import get_monitors
            monitors = get_monitors()
        except:
            # Fallback to single monitor
            monitors = [type('obj', (object,), {
                'x': 0,
                'y': 0,
                'width': self.root.winfo_screenwidth(),
                'height': self.root.winfo_screenheight()
            })]

        for monitor in monitors:
            popup = Toplevel(self.root)
            popup.title("Movement Reminder")
            popup.configure(bg=self.bg_color)
            popup.geometry("520x360")
            popup.resizable(False, False)
            popup.attributes("-topmost", True)

            # Center on this monitor
            x = monitor.x + (monitor.width // 2) - 260
            y = monitor.y + (monitor.height // 2) - 180
            popup.geometry(f"520x360+{x}+{y}")

            content = Frame(popup, bg=self.card_bg)
            content.pack(fill=BOTH, expand=True, padx=15, pady=15)

            # ═══════════════════════════════════════════════════════════════
            # CHANGE #2: STANDING ICON FOR BOTH STANDING AND WALKING
            # ═══════════════════════════════════════════════════════════════
            if phase in [Phase.STANDING, Phase.WALKING]:
                try:
                    icon_path = resource_path("standing.png")
                    if os.path.exists(icon_path):
                        standing_img = PhotoImage(file=icon_path)
                        h = standing_img.height()
                        if h > 80:
                            factor = max(1, int(round(h / 80)))
                            standing_img = standing_img.subsample(factor, factor)
                        popup.standing_icon = standing_img
                        Label(content, image=popup.standing_icon,
                             bg=self.card_bg).pack(pady=(20, 15))
                    else:
                        emoji = "🧍" if phase == Phase.STANDING else "🚶"
                        Label(content, text=emoji, bg=self.card_bg,
                             font=("Segoe UI", 56)).pack(pady=(20, 15))
                except:
                    emoji = "🧍" if phase == Phase.STANDING else "🚶"
                    Label(content, text=emoji, bg=self.card_bg,
                         font=("Segoe UI", 56)).pack(pady=(20, 15))
            else:
                Label(content, text="💺", bg=self.card_bg,
                     font=("Segoe UI", 56)).pack(pady=(20, 15))

            Label(content, text=title, bg=self.card_bg,
                 fg=self.primary_color,
                 font=("Segoe UI", 22, "bold")).pack(pady=(10, 5))

            Label(content, text=body, bg=self.card_bg,
                 fg=self.text_secondary,
                 font=("Segoe UI", 13)).pack(pady=(0, 25))

            btn_frame = Frame(content, bg=self.card_bg)
            btn_frame.pack(pady=10)

            ok_btn = GradientButton(
                btn_frame, text="OK", command=self._accept_phase_change,
                gradient_start="#10B981", gradient_end="#059669",
                width=130, height=50
            )
            ok_btn.pack(side=LEFT, padx=5)

            skip_btn = GradientButton(
                btn_frame, text="Skip", command=self._skip_phase_change,
                gradient_start="#F59E0B", gradient_end="#D97706",
                width=130, height=50
            )
            skip_btn.pack(side=LEFT, padx=5)

            if phase == Phase.WALKING and WIN:
                lock_btn = GradientButton(
                    btn_frame, text="🔒 Lock Screen",
                    command=self._lock_and_accept,
                    gradient_start="#3B82F6", gradient_end="#1D4ED8",
                    width=150, height=50
                )
                lock_btn.pack(side=LEFT, padx=5)

            self._notif_popup.append(popup)

        # Set grab on the first popup only
        if self._notif_popup:
            self._notif_popup[0].grab_set()

    def _accept_phase_change(self):
        if self._waiting_for_acknowledgment and self._pending_phase:
            self.controller._set_phase(self._pending_phase,
                                      self._pending_duration)
            self.controller.resume()
            self._is_paused = False
            self._update_button_states()
            self._waiting_for_acknowledgment = False
            self._pending_phase = None
            self._pending_duration = None
            self._current_phase_before_popup = None
        self._close_notification()

    def _skip_phase_change(self):
        if self._waiting_for_acknowledgment and self._current_phase_before_popup:
            if self._current_phase_before_popup == Phase.SITTING:
                duration = self.sit_var.get()
            elif self._current_phase_before_popup == Phase.STANDING:
                duration = self.stand_var.get()
            elif self._current_phase_before_popup == Phase.WALKING:
                duration = self.walk_var.get()
            else:
                duration = self.sit_var.get()

            self.controller._set_phase(self._current_phase_before_popup,
                                      duration)
            self.controller.resume()
            self._is_paused = False
            self._update_button_states()
            self._waiting_for_acknowledgment = False
            self._pending_phase = None
            self._pending_duration = None
            self._current_phase_before_popup = None
        self._close_notification()

    def _lock_and_accept(self):
        self._accept_phase_change()
        self.root.after(500, lock_windows_screen)

    def _close_notification(self):
        if self._notif_popup:
            try:
                if isinstance(self._notif_popup, list):
                    # Multiple popups (multi-monitor)
                    for popup in self._notif_popup:
                        try:
                            popup.grab_release()
                            popup.destroy()
                        except:
                            pass
                else:
                    # Single popup (fallback)
                    self._notif_popup.grab_release()
                    self._notif_popup.destroy()
            except:
                pass
            self._notif_popup = None

    def _show_help(self):
        if self._help_tooltip and self._help_tooltip.winfo_exists():
            self._hide_help()
            return

        self._help_tooltip = Toplevel(self.root)
        self._help_tooltip.wm_overrideredirect(True)
        self._help_tooltip.configure(bg=self.accent_color)

        x = self.help_btn.winfo_rootx() - 320
        y = self.help_btn.winfo_rooty() + 50
        self._help_tooltip.geometry(f"+{x}+{y}")

        container = Frame(self._help_tooltip, bg=self.card_bg,
                          highlightbackground=self.accent_color,
                          highlightthickness=2)
        container.pack(fill=BOTH, expand=True)

        help_text = """How to Use:

    - Start: Begin the reminder timer
    - Pause: Temporarily stop the timer
    - Resume: Continue from where you paused
    - Reset: Stop and return to initial state
    - Walk Now: Start an immediate walk timer
    - Office Stretches Guide: View recommended stretches
    - Eye Rest Exercises: View 20-20-20 rule guide

    Notifications:
    - OK: Accept and move to next phase
    - Skip: Restart current phase
    - Lock Screen: Lock your computer (Windows only)

    Settings are saved automatically."""

        Label(container, text=help_text, bg=self.card_bg,
              fg=self.text_primary,
              font=("Segoe UI", 10), justify=LEFT,
              padx=20, pady=15).pack()

        self.root.after(8000, self._hide_help)

    def _hide_help(self):
        if self._help_tooltip and self._help_tooltip.winfo_exists():
            try:
                self._help_tooltip.destroy()
            except:
                pass
            self._help_tooltip = None

    def on_close(self):
        self.controller.stop()
        self._close_notification()
        self.root.destroy()


if __name__ == "__main__":
    root = Tk()
    app = App(root)
    root.mainloop()