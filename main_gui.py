# === main_gui.py =
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import tempfile
import threading

from main import create_mosaic


class MosaicApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mosaic Generator")

        self.input_path = None
        self.tiles_path = None
        self.output_path = None

        # параметры
        tk.Label(root, text="Grid size (px):").pack()
        self.grid_entry = tk.Entry(root)
        self.grid_entry.insert(0, "30")
        self.grid_entry.pack()

        tk.Label(root, text="Stride (px) — шаг сетки (по умолчанию = grid size):").pack()
        self.stride_entry = tk.Entry(root)
        self.stride_entry.insert(0, "")  # пусто = использовать grid_size
        self.stride_entry.pack()

        tk.Label(root, text="Blend (0.0 - 1.0):").pack()
        self.blend_entry = tk.Entry(root)
        self.blend_entry.insert(0, "0.0")
        self.blend_entry.pack()

        tk.Label(root, text="Color correction (0.0 - 1.0):").pack()
        self.color_corr_entry = tk.Entry(root)
        self.color_corr_entry.insert(0, "0.0")
        self.color_corr_entry.pack()

        tk.Label(root, text="Seam smoothing (0.0 - 1.0):").pack()
        self.seam_entry = tk.Entry(root)
        self.seam_entry.insert(0, "0.0")
        self.seam_entry.pack()

        # выбор метрик
        tk.Label(root, text="Metric:").pack()
        self.metric_combo = ttk.Combobox(root, values=["color", "color+grad"], state="readonly")
        self.metric_combo.set("color")
        self.metric_combo.pack()

        # чекбокс поворота и максимальное использование
        self.rotate_var = tk.BooleanVar(value=False)
        tk.Checkbutton(root, text="Разрешить поворот тайлов (0°/90°/180°/270°)", variable=self.rotate_var).pack(anchor="w", padx=10)

        tk.Label(root, text="Max usage (0 = no limit):").pack()
        self.max_usage_entry = tk.Entry(root)
        self.max_usage_entry.insert(0, "0")
        self.max_usage_entry.pack()

        # кнопки
        tk.Button(root, text="Выбрать исходное изображение", command=self.choose_input).pack(fill="x")
        tk.Button(root, text="Выбрать папку с тайлами", command=self.choose_tiles).pack(fill="x")
        tk.Button(root, text="Выбрать место сохранения", command=self.choose_output).pack(fill="x")
        tk.Button(root, text="Создать мозаику", command=self.run_mosaic).pack(fill="x")
        tk.Button(root, text="Превью уменьшенной копии", command=self.show_preview).pack(fill="x")
        tk.Button(root, text="Превью фрагмента (центр 10x10)", command=self.show_fragment_preview).pack(fill="x")

        # контейнер для прогресса (скрыт до старта)
        progress_frame = tk.Frame(root)
        progress_frame.pack(pady=5)
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(side="left")
        self.progress_label = tk.Label(progress_frame, text="0%")
        self.progress_label.pack(side="left", padx=5)
        progress_frame.pack_forget()
        self.progress_frame = progress_frame

        # контейнер для превью
        preview_frame = tk.Frame(root)
        preview_frame.pack(fill="both", expand=True, pady=10)

        # исходное изображение слева
        left_frame = tk.Frame(preview_frame)
        left_frame.pack(side="left", expand=True, padx=10)

        tk.Label(left_frame, text="Исходное изображение:").pack()
        self.input_thumb_label = tk.Label(left_frame, bd=1, relief="sunken", width=300, height=200)
        self.input_thumb_label.pack()

        # превью справа
        right_frame = tk.Frame(preview_frame)
        right_frame.pack(side="left", expand=True, padx=10)

        tk.Label(right_frame, text="Превью мозаики:").pack()
        self.mosaic_thumb_label = tk.Label(right_frame, bd=1, relief="sunken", width=300, height=200)
        self.mosaic_thumb_label.pack()

    def choose_input(self):
        self.input_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp")])
        if self.input_path:
            self._show_input_thumbnail(self.input_path)

    def choose_tiles(self):
        self.tiles_path = filedialog.askdirectory()

    def choose_output(self):
        self.output_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg"),
                ("BMP", "*.bmp"),
                ("WebP", "*.webp"),
                ("All files", "*.*")
            ]
        )

    def _show_input_thumbnail(self, path, max_size=300):
        img = Image.open(path).convert("RGB")
        img.thumbnail((max_size, max_size))
        self._input_thumb = ImageTk.PhotoImage(img)
        self.input_thumb_label.configure(image=self._input_thumb)

    def _show_mosaic_thumbnail(self, path, max_size=300):
        img = Image.open(path).convert("RGB")
        img.thumbnail((max_size, max_size))
        self._mosaic_thumb = ImageTk.PhotoImage(img)
        self.mosaic_thumb_label.configure(image=self._mosaic_thumb)

    def _get_params(self):
        try:
            grid_size = int(self.grid_entry.get())
        except Exception:
            raise ValueError("Grid size должен быть целым числом")

        stride_input = self.stride_entry.get().strip()
        stride = None
        if stride_input != "":
            try:
                stride = int(stride_input)
                if stride <= 0:
                    raise ValueError("Stride должен быть положительным")
            except Exception:
                raise ValueError("Stride должен быть целым положительным числом или пустым")

        try:
            blend = float(self.blend_entry.get())
            if not (0.0 <= blend <= 1.0):
                raise ValueError
        except Exception:
            raise ValueError("Blend должен быть числом от 0.0 до 1.0")

        try:
            color_corr = float(self.color_corr_entry.get())
            if not (0.0 <= color_corr <= 1.0):
                raise ValueError
        except Exception:
            raise ValueError("Color correction должен быть числом от 0.0 до 1.0")

        try:
            seam = float(self.seam_entry.get())
            if not (0.0 <= seam <= 1.0):
                raise ValueError
        except Exception:
            raise ValueError("Seam smoothing должен быть числом от 0.0 до 1.0")

        try:
            max_usage = int(self.max_usage_entry.get())
            if max_usage < 0:
                raise ValueError
        except Exception:
            raise ValueError("Max usage должен быть целым неотрицательным числом")

        allow_rotate = bool(self.rotate_var.get())

        metric = self.metric_combo.get() or "color"

        return {
            "grid_size": grid_size,
            "stride": stride,
            "blend": blend,
            "allow_rotate": allow_rotate,
            "max_usage": max_usage,
            "color_correction_strength": color_corr,
            "seam_smoothing": seam,
            "metric": metric
        }

    def run_mosaic(self):
        if not (self.input_path and self.tiles_path and self.output_path):
            messagebox.showwarning("Предупреждение", "Выберите все файлы и папки.")
            return

        try:
            params = self._get_params()
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))
            return

        # показываем прогресс-бар при старте
        self.progress["value"] = 0
        self.progress_label.config(text="0%")
        self.progress_frame.pack(pady=5)

        def progress_callback(done, total):
            percent = int(done / total * 100)
            self.root.after(0, lambda: (
                self.progress.config(value=percent),
                self.progress_label.config(text=f"{percent}%")
            ))

        def worker():
            try:
                create_mosaic(
                    self.input_path,
                    self.tiles_path,
                    self.output_path,
                    params["grid_size"],
                    stride=params["stride"],
                    allow_rotate=params["allow_rotate"],
                    max_usage=params["max_usage"],
                    color_correction_strength=params["color_correction_strength"],
                    blend=params["blend"],
                    metric=params["metric"],
                    seam_smoothing=params["seam_smoothing"],
                    progress_callback=progress_callback
                )
                self.root.after(0, lambda: messagebox.showinfo("Готово", f"Мозаика сохранена в {self.output_path}"))
            except Exception as e:
                self.root.after(0, lambda e=e: messagebox.showerror("Ошибка", str(e)))
            finally:
                # скрываем прогресс-бар по завершении
                self.root.after(0, self.progress_frame.pack_forget)

        threading.Thread(target=worker, daemon=True).start()

    def show_preview(self):
        if not (self.input_path and self.tiles_path):
            messagebox.showwarning("Предупреждение", "Выберите исходное изображение и папку с тайлами.")
            return

        try:
            params = self._get_params()
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))
            return

        def worker():
            try:
                inp = Image.open(self.input_path).convert("RGB")
                w, h = inp.size
                max_dim = 400
                scale = min(1.0, max_dim / max(w, h))
                preview_w, preview_h = max(1, int(w * scale)), max(1, int(h * scale))

                tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(self.input_path)[1])
                tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                tmp_in.close()
                tmp_out.close()

                try:
                    inp.resize((preview_w, preview_h)).save(tmp_in.name)

                    # масштабируем stride пропорционально (если задан)
                    if params["stride"] is not None:
                        g_stride = max(1, int(params["stride"] * scale))
                    else:
                        g_stride = None

                    g = max(4, int(params["grid_size"] * scale))

                    create_mosaic(tmp_in.name, self.tiles_path, tmp_out.name, g,
                                  stride=g_stride,
                                  allow_rotate=params["allow_rotate"],
                                  max_usage=params["max_usage"],
                                  color_correction_strength=params["color_correction_strength"],
                                  blend=params["blend"],
                                  metric=params["metric"],
                                  seam_smoothing=params["seam_smoothing"])

                    def update_preview():
                        self._show_mosaic_thumbnail(tmp_out.name)
                        self.root.after(2000, lambda: os.remove(tmp_out.name) if os.path.exists(tmp_out.name) else None)
                        if os.path.exists(tmp_in.name):
                            os.remove(tmp_in.name)

                    self.root.after(0, update_preview)

                except Exception as e:
                    self.root.after(0, lambda e=e: messagebox.showerror("Ошибка превью", str(e)))

            except Exception as e:
                self.root.after(0, lambda e=e: messagebox.showerror("Ошибка превью", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def show_fragment_preview(self):
        # делает превью центрального фрагмента размера 10x10 тайлов
        if not (self.input_path and self.tiles_path):
            messagebox.showwarning("Предупреждение", "Выберите исходное изображение и папку с тайлами.")
            return

        try:
            params = self._get_params()
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))
            return

        def worker():
            try:
                inp = Image.open(self.input_path).convert("RGB")
                w, h = inp.size
                tiles_x = tiles_y = 10
                frag_w = params["grid_size"] * tiles_x
                frag_h = params["grid_size"] * tiles_y

                # ограничиваем размер фрагмента размерами изображения
                frag_w = min(frag_w, w)
                frag_h = min(frag_h, h)

                left = max(0, (w - frag_w) // 2)
                top = max(0, (h - frag_h) // 2)
                right = left + frag_w
                bottom = top + frag_h

                frag = inp.crop((left, top, right, bottom))

                # уменьшение до приемлемого размера для превью
                max_dim = 400
                scale = min(1.0, max_dim / max(frag.width, frag.height))
                preview_w, preview_h = max(1, int(frag.width * scale)), max(1, int(frag.height * scale))

                tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(self.input_path)[1])
                tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                tmp_in.close()
                tmp_out.close()

                try:
                    frag.resize((preview_w, preview_h)).save(tmp_in.name)

                    # масштабируем stride пропорционально (если задан)
                    if params["stride"] is not None:
                        g_stride = max(1, int(params["stride"] * scale))
                    else:
                        g_stride = None

                    g = max(4, int(params["grid_size"] * scale))

                    create_mosaic(tmp_in.name, self.tiles_path, tmp_out.name, g,
                                  stride=g_stride,
                                  allow_rotate=params["allow_rotate"],
                                  max_usage=params["max_usage"],
                                  color_correction_strength=params["color_correction_strength"],
                                  blend=params["blend"],
                                  metric=params["metric"],
                                  seam_smoothing=params["seam_smoothing"])

                    def update_preview():
                        self._show_mosaic_thumbnail(tmp_out.name)
                        self.root.after(2000, lambda: os.remove(tmp_out.name) if os.path.exists(tmp_out.name) else None)
                        if os.path.exists(tmp_in.name):
                            os.remove(tmp_in.name)

                    self.root.after(0, update_preview)

                except Exception as e:
                    self.root.after(0, lambda e=e: messagebox.showerror("Ошибка превью", str(e)))

            except Exception as e:
                self.root.after(0, lambda e=e: messagebox.showerror("Ошибка превью", str(e)))

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = MosaicApp(root)
    root.geometry("900x700")
    root.mainloop()


