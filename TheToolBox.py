import tkinter as tk
from tkinter import ttk, scrolledtext
import os
import sys
import configparser
import winreg as reg
import subprocess
import threading
import time
import random
import math
import cmath

# Config for "stay closed"
CONFIG_FILE = 'toolbox_config.ini'
NOTES_FILE = 'my_notes.txt'

config = configparser.ConfigParser()

def load_config():
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        return config['SETTINGS'].getboolean('run', True)
    config['SETTINGS'] = {'run': 'True'}
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)
    return True

RUN_APP = load_config()
if not RUN_APP:
    sys.exit(0)

# Startup registry
def add_to_startup():
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER,
                          r"Software\Microsoft\Windows\CurrentVersion\Run",
                          0, reg.KEY_SET_VALUE)
        path = os.path.abspath(sys.argv[0])
        reg.SetValueEx(key, "FloatingBoxTool", 0, reg.REG_SZ, f'pythonw "{path}"')
        reg.CloseKey(key)
    except:
        pass

def remove_from_startup():
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER,
                          r"Software\Microsoft\Windows\CurrentVersion\Run",
                          0, reg.KEY_SET_VALUE)
        reg.DeleteValue(key, "FloatingBoxTool")
        reg.CloseKey(key)
    except:
        pass

if RUN_APP:
    add_to_startup()

# ─── Main Window ───────────────────────────────────────────────
root = tk.Tk()
root.overrideredirect(True)
root.attributes('-topmost', True)
root.geometry("80x80+200+200")
root.configure(bg="#000000")
root.attributes('-alpha', 0.85)

tools_visible = tk.BooleanVar(value=False)
tools_frame = None
notes_text = None
last_notes_content = ""

# Matrix rain elements
matrix_canvas = None
drops = []
animation_id = None

# Zeta visualization elements
zeta_canvas = None
zeta_points = []
zeta_t = 0
zeta_animation_id = None

matrix_chars = list("ｦｱｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")

def start_matrix_rain():
    global matrix_canvas, animation_id, drops
    if matrix_canvas:
        return

    matrix_canvas = tk.Canvas(root, bg="#000000", highlightthickness=0)
    matrix_canvas.place(x=0, y=0, relwidth=1, relheight=1)

    drops.clear()
    width = root.winfo_width()
    for _ in range(width // 20 + 1):
        x = random.randint(0, width)
        y = random.randint(-200, -50)
        speed = random.uniform(6, 18)
        trail = random.randint(8, 20)
        chars = [random.choice(matrix_chars) for _ in range(trail + 5)]
        drops.append([x, y, speed, trail, chars])

    def animate():
        global animation_id
        if not tools_visible.get():
            stop_matrix_rain()
            return

        width = root.winfo_width()
        height = root.winfo_height()
        matrix_canvas.delete("all")

        for drop in drops:
            x, y, speed, trail, chars = drop

            for i in range(trail):
                if y + i * 15 > height:
                    break
                alpha = 1 - (i / trail)
                color = f'#{int(0x00 + alpha * 0xFF):02x}FF00'
                char = chars[i % len(chars)]
                matrix_canvas.create_text(x, y + i * 15, text=char, fill=color,
                                          font=("Consolas", 12), anchor="center")

            matrix_canvas.create_text(x, y, text=chars[0], fill="#00FF00",
                                      font=("Consolas", 14, "bold"), anchor="center")

            drop[1] += speed

            if y > height + 100:
                drop[1] = random.randint(-150, -50)
                drop[0] = random.randint(0, width)
                drop[4] = [random.choice(matrix_chars) for _ in range(trail + 5)]

        animation_id = root.after(50, animate)

    animate()

def stop_matrix_rain():
    global matrix_canvas, animation_id
    if animation_id:
        root.after_cancel(animation_id)
        animation_id = None
    if matrix_canvas:
        matrix_canvas.destroy()
        matrix_canvas = None
    drops.clear()

# ─── Zeta Function Visualization ───────────────────────────────
def zeta_approx(s_real, s_imag, max_terms=50):
    """Approximate Riemann zeta function"""
    real_sum = 0
    imag_sum = 0
    
    for n in range(1, max_terms + 1):
        n_pow_s = n ** (-s_real)
        angle = -s_imag * math.log(n)
        real_sum += n_pow_s * math.cos(angle)
        imag_sum += n_pow_s * math.sin(angle)
    
    return real_sum, imag_sum

def hsl_to_rgb(h, s, l):
    """Convert HSL to RGB"""
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    
    return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)

def start_zeta_visualization(canvas):
    global zeta_canvas, zeta_animation_id, zeta_points, zeta_t
    
    zeta_canvas = canvas
    zeta_points.clear()
    zeta_t = 0
    
    width = canvas.winfo_reqwidth() or 300
    height = canvas.winfo_reqheight() or 300
    center_x = width / 2
    center_y = height / 2
    scale = min(width, height) / 8
    
    def animate_zeta():
        global zeta_animation_id, zeta_t
        
        if not zeta_canvas or not zeta_canvas.winfo_exists():
            return
        
        # Only clear canvas every few frames to reduce overhead
        if len(zeta_points) % 3 == 0:
            zeta_canvas.delete("all")
            
            # Draw grid background
            grid_spacing = 40
            
            # Vertical lines
            for x in range(0, int(width), grid_spacing):
                zeta_canvas.create_line(x, 0, x, height, 
                                       fill="#003300", width=1)
            
            # Horizontal lines
            for y in range(0, int(height), grid_spacing):
                zeta_canvas.create_line(0, y, width, y, 
                                       fill="#003300", width=1)
            
            # Center axes (brighter)
            zeta_canvas.create_line(center_x, 0, center_x, height, 
                                   fill="#005500", width=2)
            zeta_canvas.create_line(0, center_y, width, center_y, 
                                   fill="#005500", width=2)
            
            # Center point
            zeta_canvas.create_oval(center_x - 2, center_y - 2,
                                   center_x + 2, center_y + 2,
                                   fill="#00aa00", outline="")
        
        # Calculate zeta(0.5 + it) - even fewer terms
        zeta_real, zeta_imag = zeta_approx(0.5, zeta_t, 25)
        
        # Check if near zero (within threshold)
        magnitude = math.sqrt(zeta_real**2 + zeta_imag**2)
        near_zero = magnitude < 0.5  # Threshold for "close to zero"
        
        # Map to screen
        x = center_x + zeta_real * scale
        y = center_y - zeta_imag * scale
        
        zeta_points.append((x, y, zeta_t))
        if len(zeta_points) > 60:  # Reduced from 100
            zeta_points.pop(0)
        
        # PULSE ANIMATION when near zero
        if near_zero:
            pulse_size = int(30 + 20 * math.sin(zeta_t * 10))  # Pulsing radius
            for radius in range(pulse_size, 10, -5):
                alpha = 1 - (pulse_size - radius) / pulse_size
                green_val = int(255 * alpha)
                pulse_color = f'#{green_val:02x}{green_val:02x}00'  # Yellow-green pulse
                zeta_canvas.create_oval(center_x - radius, center_y - radius,
                                       center_x + radius, center_y + radius,
                                       outline=pulse_color, width=2, fill="")
        
        # Draw trail - even more sparse, every 3rd point
        for i in range(3, len(zeta_points), 3):
            prev = zeta_points[i - 3]
            curr = zeta_points[i]
            alpha = i / len(zeta_points)
            
            # Simple green fade from dark to bright
            green_value = int(255 * alpha)
            color = f'#00{green_value:02x}00'
            line_width = 2
            
            zeta_canvas.create_line(prev[0], prev[1], curr[0], curr[1],
                                   fill=color, width=line_width)
        
        # Draw current point - simple green glow (brighter if near zero)
        if zeta_points:
            curr = zeta_points[-1]
            
            if near_zero:
                # Bright yellow-green glow when near zero
                zeta_canvas.create_oval(curr[0] - 10, curr[1] - 10,
                                       curr[0] + 10, curr[1] + 10,
                                       fill="#ffff00", outline="")
                zeta_canvas.create_oval(curr[0] - 5, curr[1] - 5,
                                       curr[0] + 5, curr[1] + 5,
                                       fill="#ffffff", outline="")
            else:
                # Normal green glow
                zeta_canvas.create_oval(curr[0] - 6, curr[1] - 6,
                                       curr[0] + 6, curr[1] + 6,
                                       fill="#00aa00", outline="")
                
                # Bright core point
                zeta_canvas.create_oval(curr[0] - 3, curr[1] - 3,
                                       curr[0] + 3, curr[1] + 3,
                                       fill="#00FF00", outline="")
        
        zeta_t += 0.2  # Even faster increment
        zeta_animation_id = root.after(100, animate_zeta)  # Even slower framerate (100ms = 10fps)
    
    animate_zeta()

def stop_zeta_visualization():
    global zeta_animation_id, zeta_canvas
    if zeta_animation_id:
        root.after_cancel(zeta_animation_id)
        zeta_animation_id = None
    zeta_canvas = None
    zeta_points.clear()

# ─── Notes Auto-Save ───────────────────────────────────────────
def save_notes():
    global last_notes_content
    if notes_text:
        current = notes_text.get("1.0", tk.END).strip()
        if current != last_notes_content:
            try:
                with open(NOTES_FILE, 'w', encoding='utf-8') as f:
                    f.write(current)
                last_notes_content = current
            except:
                pass

def auto_save_loop():
    while True:
        save_notes()
        time.sleep(5)

threading.Thread(target=auto_save_loop, daemon=True).start()

if os.path.exists(NOTES_FILE):
    try:
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            last_notes_content = f.read().strip()
    except:
        last_notes_content = ""

# ─── Draggable ─────────────────────────────────────────────────
def start_drag(event):
    root._offsetx = event.x
    root._offsety = event.y

def do_drag(event):
    x = root.winfo_x() + (event.x - root._offsetx)
    y = root.winfo_y() + (event.y - root._offsety)
    root.geometry(f"+{x}+{y}")

root.bind("<Button-1>", start_drag)
root.bind("<B1-Motion>", do_drag)

# ─── Toggle tools with TABS ────────────────────────────────────
def toggle_tools():
    global tools_frame, notes_text
    if tools_visible.get():
        save_notes()
        stop_matrix_rain()
        stop_zeta_visualization()
        tools_visible.set(False)
        root.geometry("80x80")
        if tools_frame:
            tools_frame.destroy()
            tools_frame = None
            notes_text = None
    else:
        tools_visible.set(True)
        root.geometry("400x480")
        
        start_matrix_rain()
        
        # Create the tools container
        tools_frame = tk.Frame(root, bg="#000800")
        tools_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.92, relheight=0.92)
        tools_frame.lift()
        
        # Create notebook (tabbed interface)
        style = ttk.Style()
        style.theme_use('default')
        style.configure('Matrix.TNotebook', background='#000800', borderwidth=0)
        style.configure('Matrix.TNotebook.Tab', 
                       background='#001a00', 
                       foreground='#00FF00',
                       padding=[10, 5],
                       font=('Consolas', 10, 'bold'))
        style.map('Matrix.TNotebook.Tab',
                 background=[('selected', '#004d00')],
                 foreground=[('selected', '#00FF00')])
        
        notebook = ttk.Notebook(tools_frame, style='Matrix.TNotebook')
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # ═══ TAB 1: Search & Notes ═══
        tab1 = tk.Frame(notebook, bg="#000800")
        notebook.add(tab1, text="Tools")
        
        tk.Label(tab1, text="Search:", bg="#000800", fg="#00FF00", 
                font=("Consolas", 12, "bold")).pack(anchor="w", pady=(15, 5), padx=10)
        
        search_entry = tk.Entry(tab1, width=35, 
                                bg="#001a00", fg="#00FF99", insertbackground="#00FF00",
                                font=("Consolas", 11), relief="flat", borderwidth=1)
        search_entry.pack(pady=6, padx=10, fill="x")
        
        def do_search():
            q = search_entry.get().strip()
            if q:
                url = f"https://www.bing.com/search?q={q}"
                subprocess.Popen(['start', 'msedge', url], shell=True)
                search_entry.delete(0, tk.END)
        
        tk.Button(tab1, text="Search in Edge", command=do_search,
                  bg="#004d00", fg="#00FF00", activebackground="#006600",
                  font=("Consolas", 10, "bold"), relief="raised").pack(pady=10)
        
        tk.Label(tab1, text="Notes:", bg="#000800", fg="#00FF00", 
                font=("Consolas", 12, "bold")).pack(anchor="w", pady=(15, 5), padx=10)
        
        notes_text = scrolledtext.ScrolledText(
            tab1, width=38, height=10,
            bg="#001a00", fg="#00FF88", insertbackground="#00FF00",
            font=("Consolas", 11), wrap=tk.WORD, relief="flat", borderwidth=1
        )
        notes_text.pack(pady=6, padx=10, fill=tk.BOTH, expand=True)
        notes_text.insert(tk.END, last_notes_content)
        
        # ═══ TAB 2: Zeta Visualization ═══
        tab2 = tk.Frame(notebook, bg="#050510")
        notebook.add(tab2, text="ζ(s)")
        
        tk.Label(tab2, text="Riemann Zeta Function ζ(0.5 + it)", 
                bg="#050510", fg="#00FF00",
                font=("Consolas", 11, "bold")).pack(pady=10)
        
        zeta_display = tk.Canvas(tab2, bg="#050510", highlightthickness=0,
                                width=360, height=320)
        zeta_display.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Start visualization when tab is visible
        def on_tab_change(event):
            selected_tab = event.widget.index("current")
            if selected_tab == 1:  # Zeta tab
                start_zeta_visualization(zeta_display)
            else:
                stop_zeta_visualization()
        
        notebook.bind("<<NotebookTabChanged>>", on_tab_change)
        
        # Bottom buttons
        btn_frame = tk.Frame(tools_frame, bg="#000800")
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="Close Tools", command=toggle_tools,
                  bg="#004d00", fg="#00FF00", activebackground="#006600",
                  font=("Consolas", 9, "bold")).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Stay Closed Forever", command=quit_permanently,
                  bg="#4d0000", fg="#FF4444", activebackground="#660000",
                  font=("Consolas", 9, "bold")).pack(side="right", padx=10)
        
        if matrix_canvas:
            matrix_canvas.lower()

# ─── Quit permanently ──────────────────────────────────────────
def quit_permanently():
    save_notes()
    stop_matrix_rain()
    stop_zeta_visualization()
    config['SETTINGS']['run'] = 'False'
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)
    remove_from_startup()
    root.quit()

# ─── Icon (🧰 style) ───────────────────────────────────────────
canvas = tk.Canvas(root, width=80, height=80, bg="#000000", highlightthickness=0)
canvas.pack()

canvas.create_rectangle(20, 25, 60, 55, fill="#004d00", outline="#00FF00", width=3)
canvas.create_rectangle(30, 15, 50, 25, fill="#004d00", outline="#00FF00", width=3)
canvas.create_line(40, 10, 40, 15, fill="#00aa00", width=5)

canvas.bind("<Button-1>", lambda e: toggle_tools())

def on_right_click(e):
    if tools_visible.get():
        toggle_tools()

root.bind("<Button-3>", on_right_click)

def keep_on_top():
    root.lift()
    root.after(3000, keep_on_top)

keep_on_top()

root.mainloop()
