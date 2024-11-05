import os, math, json
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from tkinter.font import Font

from PIL import Image, ImageTk, ImageGrab

class PaletteDropdown(ttk.Combobox):
    def __init__(self, parent, palettes, selectcallback, **kwargs):
        super().__init__(parent, **kwargs)
        self.palettes = palettes
        self.selectcallback = selectcallback
        self.font = Font(family="Courier", size=12, weight="bold")
        self["state"] = "readonly"
        self.bind("<<ComboboxSelected>>", self.on_select)
        self.update_options()
    
    def update_options(self):
        self["values"] = [f"{name}" for name, colors in self.palettes]
    
    def on_select(self, event):
        if self.selectcallback:
            self.selectcallback(self.palettes[self.current()])

class App(object):
    def __init__(self, parent):
        self.parent = parent
        self.parent.title("Texmage")
        self.parent.geometry("1280x720")

        self.all_palettes = self.load_palettes_json()
        self.palette = self.all_palettes[0]

        self.is_dirty = False
        self.current_filename = "Untitled"

        self.create_widgets()
        #self.update_image()
        self.change_palette(self.palette)
    
    def load_palettes_json(self):
        if os.path.exists("palettes.json"):
            with open("palettes.json") as f:
                palettes = json.load(f)
            return [(entry["name"], entry["colors"]) for entry in palettes]
        return [
            ("PICO-8", [
                "000000",
                "1D2B53",
                "7E2553",
                "008751",
                "AB5236",
                "5F574F",
                "C2C3C7",
                "FFF1E8",
                "FF004D",
                "FFA300",
                "FFEC27",
                "00E436",
                "29ADFF",
                "83769C",
                "FF77A8",
                "FFCCAA"
            ])
        ]
            

    def create_widgets(self):
        self.paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        self.paned.pack(expand=True, fill='both')

        self.left_frame = ttk.Frame(self.paned)
        self.right_frame = ttk.Frame(self.paned)

        self.paned.add(self.left_frame, weight=1)
        self.paned.add(self.right_frame, weight=1)

        self.control_panel = ttk.Frame(self.right_frame)
        self.control_panel.pack(fill="x", padx=5, pady=5)

        self.palette_panel = ttk.Frame(self.control_panel)
        self.palette_panel.pack(side="left", padx=5)

        self.palette_selector = PaletteDropdown(self.palette_panel, self.all_palettes, self.change_palette)
        self.current_palette_display = tk.Canvas(self.palette_panel)
        self.current_palette_display.grid(column=0, row=0, padx=5, pady=5)
        self.palette_selector.grid(sticky="w", column=0, row=1, padx=5, pady=5)

        self.vis_mode = tk.StringVar(value="palette")
        self.mode_toggle = ttk.Checkbutton(self.control_panel, text="Use Palette Colors", variable=self.vis_mode, onvalue="palette", offvalue="direct", command=self.update_image)
        self.mode_toggle.pack(side="left", padx=5)

        self.dimension_mode = tk.StringVar(value="uniform")
        self.dimension_toggle = ttk.Checkbutton(self.control_panel, text="Use Uniform Dimensions", variable=self.dimension_mode, onvalue="uniform", offvalue="nonuniform", command=self.update_image)
        self.dimension_toggle.pack(side="left", padx=5)

        self.pot_mode = tk.StringVar(value="pot")
        self.pot_toggle = ttk.Checkbutton(self.control_panel, text="Use Power of Two", variable=self.pot_mode, onvalue="pot", offvalue="npot", command=self.update_image)
        self.pot_toggle.pack(side="left", padx=5)
        

        self.text_area = scrolledtext.ScrolledText(self.left_frame, wrap=tk.WORD, width=40, height=20, bg="white", fg="blue")
        self.text_area.pack(expand=True, fill='both', padx=5, pady=5)
        self.text_area.bind('<<Modified>>', self.on_text_change)

        self.text_area2 = scrolledtext.ScrolledText(self.left_frame, wrap=tk.WORD, width=40, height=20, bg="light gray", fg="black")
        self.text_area2.pack(expand=True, fill='both', padx=5, pady=5)
        self.text_area2.config(state="disabled")

        self.canvas = tk.Canvas(self.right_frame, bg="black")
        self.canvas.pack(expand=True, fill='both', padx=5, pady=5)

        self.menu_bar = tk.Menu(self.parent)
        self.parent.config(menu=self.menu_bar)

        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New", command=self.new_file)
        self.file_menu.add_command(label="Open", command=self.open_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save", command=self.save_file)
        self.file_menu.add_command(label="Save As...", command=self.save_file_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Export Image Unscaled", command=self.export_image_file_unscaled)
        self.file_menu.add_command(label="Export Image Scaled", command=self.export_image_file_scaled)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.parent.quit)

        self.view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        self.view_menu.add_checkbutton(label="Realtime Visualization", command=self.toggle_realtime_vis)
        self.view_menu.add_checkbutton(label="Console", command=self.toggle_console)
        self.view_menu.add_checkbutton(label="Options", command=self.toggle_options)
        self.status_bar_state = tk.IntVar(value=1)
        self.view_menu.add_checkbutton(label="Status Bar", command=self.toggle_status_bar, variable=self.status_bar_state)

        self.status_bar = ttk.Label(self.parent, text="Ready", relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x", pady=5, padx=5)
        self.status_bar_visisble = True


        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)

        self.update_title()
    
    def toggle_realtime_vis(self):
        pass

    def toggle_console(self):
        pass

    def toggle_options(self):
        pass

    def toggle_status_bar(self):
        if self.status_bar_visisble:
            self.status_bar_visisble = False
            self.status_bar.pack_forget()
        else:
            self.status_bar_visisble = True
            self.status_bar.pack(side="bottom", fill="x", pady=5, padx=5)


    def new_file(self):
        if self.is_dirty:
            if not self.confirm_save():
                return
        self.text_area.delete(1.0, tk.END)
        self.current_filename = "Untitled"
        self.is_dirty = False
        self.update_title()
    
    def save_file(self):
        if self.current_filename == "Untitled":
            self.save_file_as()
        else:
            self.write_file(self.current_filename, self.get_project_json())
            self.is_dirty = False
            self.update_title()

    def save_file_as(self):
        filename = filedialog.asksaveasfilename(defaultextension=".tmv", filetypes=[("Texmage Visualization Project Files", "*.tmv")])
        if filename:
            self.current_filename = os.path.basename(filename)
            self.write_file(filename, self.get_project_json())
            self.is_dirty = False
            self.update_title()

    def open_file(self):
        if self.is_dirty:
            if not self.confirm_save():
                return
        filename = filedialog.askopenfilename(defaultextension=".tmv", filetypes=[("Texmage Visualization Project Files", "*.tmv")])
        if filename:
            with open(filename, "r") as f:
                project = json.load(f)
            self.change_palette(project["palette"])
            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(tk.END, project["text"])
            self.current_filename = os.path.basename(filename)
            self.is_dirty = False
            self.update_title()

    def export_image_file_scaled(self):
        filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image Files", "*.png")])
        if filename:
            self.scaled_raster.save(filename)
    
    def export_image_file_unscaled(self):
        filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image Files", "*.png")])
        if filename:
            self.unscaled_raster.save(filename)


    def confirm_save(self):
        res = messagebox.askyesnocancel("Save Changes", f"Do you want to save changes to {self.current_filename}?")
        if res is None:
            return False
        if res:
            self.save_file()
        return True

    def get_project_json(self):
        return json.dumps({
            "text": self.text_area.get(1.0, tk.END).strip(),
            "options": {
                "vis_mode": self.vis_mode.get(),
                "dimension_mode": self.dimension_mode.get(),
                "pot_mode": self.pot_mode.get(),
            },
            "name": self.current_filename,
            "palette": self.palette
            })

    def write_file(self, filename, contents):
        with open(filename, "w") as f:
            f.write(contents)
    
    def on_text_change(self, event=None):
        self.is_dirty = True
        self.update_title()
        self.text_area.edit_modified(False)
        self.update_image()
    
    def update_title(self):
        if self.is_dirty:
            self.parent.title(f"{self.current_filename}* - Texmage")
        else:
            self.parent.title(f"{self.current_filename} - Texmage")
    
    def text_to_bytes(self, text):
        if not text.strip():
            return []
        return list(text.strip().encode('utf-8'))
    
    def calculate_image_dimensions(self, byte_data):
        total_pixels = len(byte_data)
        if self.pot_mode.get() == "pot":
            if self.dimension_mode.get() == "uniform":
                side = 1
                while side * side < total_pixels:
                    side = side * 2
                return side, side
            else:
                width = height = 1
                while width * height < total_pixels:
                    if width < height:
                        width *= 2
                    else:
                        height *= 2
                return width, height
        else:
            # non power of two
            if self.dimension_mode.get() == "uniform":
                side = 1
                while side * side < total_pixels:
                    side = side + 1
                return side, side
            else:
                # non uniform, non power of two
                width = height = 1
                while width * height < total_pixels:
                    if width < height:
                        width = width + 1
                    else:
                        height = height + 1
                return width, height


    
    def bytes_to_image_direct(self, byte_data):
        width, height = self.calculate_image_dimensions(byte_data)
        image_data = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(len(byte_data)):
            x = i % width
            y = i // width
            image_data[y, x, 0] = byte_data[i]
            image_data[y, x, 1] = byte_data[i]
            image_data[y, x, 2] = byte_data[i]
        return image_data, width, height
        
    def bytes_to_image_palette(self, byte_data):
        width, height = self.calculate_image_dimensions(byte_data)
        image_data = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(len(byte_data)):
            x = i % width
            y = i // width
            palette_idx = byte_data[i] % len(self.palette[1])
            image_data[y, x] = self.hex_to_rgb(self.palette[1][palette_idx])
        return image_data, width, height

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def bytes_to_image(self, byte_data):
        if self.vis_mode.get() == "palette":
            return self.bytes_to_image_palette(byte_data)
        return self.bytes_to_image_direct(byte_data)

    def change_palette(self, palette):
        #print(f"Changed palette to {palette}")
        self.palette = palette
        self.render_palette(palette)
        self.update_image()
    
    def render_palette(self, palette):
        swatch_size = 16
        canvas = self.current_palette_display
        canvas.delete("all")
        canvas.configure(width=swatch_size * len(palette[1]), height=swatch_size, bg="black")
        for i, color in enumerate(palette[1]):
            canvas.create_rectangle(i * swatch_size, 0, (i + 1) * swatch_size, swatch_size, fill=f"#{color}", outline=f"#{color}")

    def update_image(self):
        text_content = self.text_area.get(1.0, tk.END).strip()
        byte_data = self.text_to_bytes(text_content)
        image_data, image_width, image_height = self.bytes_to_image(byte_data)

        self.text_area2.config(state="normal")
        self.text_area2.delete(1.0, tk.END)
        self.text_area2.insert(tk.END, f"Image: {image_width}x{image_height}\nInput Length: {len(text_content)}\nInput Bytes:\n{byte_data}\nOutput Image Bytes: {image_data.ravel()}")
        self.text_area2.config(state="disabled")
        
        image = Image.fromarray(image_data)
        self.unscaled_raster = image
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width > 1 and canvas_height > 1:
            image = image.resize((canvas_width, canvas_height), Image.Resampling.NEAREST)
        self.image = ImageTk.PhotoImage(image)
        self.scaled_raster = image
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.image, anchor=tk.NW)
        pass

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
