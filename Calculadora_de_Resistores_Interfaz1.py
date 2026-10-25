# calculadora_gui.py
import ctypes, os, platform
from pathlib import Path
import threading
import itertools
import math
from tkinter import messagebox, Canvas

import customtkinter as ctk

# ============================================================
# FUENTES
# ============================================================
def cargar_fuente(ruta_ttf: str) -> bool:
    if os.name != "nt":
        return False
    p = Path(ruta_ttf)
    if not p.is_file():
        return False
    FR_PRIVATE = 0x10
    ctypes.windll.gdi32.AddFontResourceExW(str(p.resolve()), FR_PRIVATE, 0)
    return True

def familias_por_plataforma():
    s = platform.system()
    if s == "Windows": return "Segoe UI", "Cascadia Code"
    if s == "Darwin":  return "SF Pro Text", "SF Mono"
    return "Ubuntu", "Ubuntu Mono"

# ============================================================
# PALETA · YOUTUBE LIGHT
# ============================================================
COL_BG           = "#f9f9f9"
COL_CARD         = "#ffffff"
COL_INPUT        = "#f2f2f2"
COL_BORDER       = "#e0e0e0"
COL_BORDER_FOCUS = "#ff0000"
COL_ACCENT       = "#ff0000"
COL_ACCENT_HOVER = "#cc0000"
COL_TEXT         = "#0f0f0f"
COL_DIM          = "#606060"
COL_SUCCESS      = "#1e8e3e"
COL_LIME         = "#5e9c1a"
COL_WARN         = "#e67e00"
COL_DANGER       = "#d32f2f"
COL_INK          = "#ffffff"

# Colores estilo Tinkercad para el título
TINKER_COLORS = [
    "#e74c3c", # Rojo
    "#e67e22", # Naranja
    "#f1c40f", # Amarillo
    "#27ae60", # Verde
    "#2ecc71", # Verde claro
    "#a2d149", # Lima
    "#2980b9", # Azul oscuro
    "#3498db", # Azul
    "#5dade2"  # Azul claro
]

# ============================================================
# JERARQUÍA DEL TOP 3 (medallas: oro → plata → bronce)
# ============================================================
CARD_STYLES = {
    1: {
        'bg':           "#fdf0ba",
        'border':       '#f59e0b',
        'border_width': 3,
        'badge_bg':     '#ca8a04',
        'badge_size':   44,
        'label':        'MEJOR OPCIÓN',
    },
    2: {
        'bg':           "#d4dfec",#f9fafb
        'border':       '#9ca3af', 
        'border_width': 2,
        'badge_bg':     '#6b7280',
        'badge_size':   40,
        'label':        None,
    },
    3: {
        'bg':           "#f0e8e0",
        'border':       '#b45309',
        'border_width': 2,
        'badge_bg':     '#92400e',
        'badge_size':   36,
        'label':        None,
    },
}

# ============================================================
# CÓDIGO DE COLORES DE RESISTORES
# ============================================================
COLOR_CODE = {
    0: "#000000", 1: "#8B4513", 2: "#FF0000", 3: "#FF8C00",
    4: "#FFD700", 5: "#00FF00", 6: "#0000FF", 7: "#8A2BE2",
    8: "#808080", 9: "#FFFFFF",
}
MULT_COLORS = {-1: "#FFD700", -2: "#C0C0C0"}

def bandas_resistor(valor, tolerancia_pct=5.0):
    if valor <= 0:
        return None
    try:
        exp = int(math.floor(math.log10(valor)))
        scaled = round(valor / (10 ** exp) * 10)
        if scaled >= 100:
            scaled //= 10
            exp += 1
        if scaled < 10:
            return None
        d1, d2 = divmod(scaled, 10)
        idx = exp - 1
        band3 = COLOR_CODE.get(idx) if idx >= 0 else MULT_COLORS.get(idx, "#888888")

        if tolerancia_pct <= 1.0:
            band4 = "#8B4513"
        elif tolerancia_pct <= 2.0:
            band4 = "#FF0000"
        elif tolerancia_pct <= 5.0:
            band4 = "#FFD700"
        else:
            band4 = "#C0C0C0"

        return [COLOR_CODE.get(d1, "#888888"),
                COLOR_CODE.get(d2, "#888888"),
                band3 or "#888888",
                band4]
    except (ValueError, OverflowError):
        return None

# ============================================================
# LÓGICA
# ============================================================
E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]

def generar_valores_comerciales(serie, max_decadas=6):
    valores = []
    for decada in range(max_decadas):
        for v in serie:
            valores.append(round(v * (10 ** decada), 2))
    return sorted(valores)

def obtener_lista_resistencias(tolerancia):
    return generar_valores_comerciales(E12 if tolerancia >= 10 else E24)

def _topologias_3r(a, b, c):
    opciones = {}
    for sola, p1, p2 in [(a, b, c), (b, a, c), (c, a, b)]:
        den = p1 + p2 + sola
        if den > 0:
            v = (p1 + p2) * sola / den
            opciones[f"({p1:g}+{p2:g})||{sola:g}"] = ('Serie-Paralelo', v)
        if p1 + p2 > 0:
            v = p1 * p2 / (p1 + p2) + sola
            opciones[f"({p1:g}||{p2:g})+{sola:g}"] = ('Paralelo-Serie', v)
    return [(t, v, e) for e, (t, v) in opciones.items()]

def encontrar_mejores_combinaciones(target, resistencias, tolerancia_pct):
    resultados = []
    for r in range(1, 4):
        for combo in itertools.combinations_with_replacement(resistencias, r):
            v = sum(combo)
            err = abs(v - target) / target * 100
            if err <= tolerancia_pct:
                resultados.append({'tipo': 'Serie',
                    'expresion': ' + '.join(f"{x:g}" for x in combo),
                    'combinacion': combo, 'valor_eq': round(v, 2),
                    'error': round(err, 3), 'n': r})
            if r > 1:
                v = 1 / sum(1/x for x in combo)
                err = abs(v - target) / target * 100
                if err <= tolerancia_pct:
                    resultados.append({'tipo': 'Paralelo',
                        'expresion': ' || '.join(f"{x:g}" for x in combo),
                        'combinacion': combo, 'valor_eq': round(v, 2),
                        'error': round(err, 3), 'n': r})
            if r == 3:
                for tipo, v, expr in _topologias_3r(*combo):
                    err = abs(v - target) / target * 100
                    if err <= tolerancia_pct:
                        resultados.append({'tipo': tipo, 'expresion': expr,
                            'combinacion': combo, 'valor_eq': round(v, 2),
                            'error': round(err, 3), 'n': r})
    vistos, unicos = set(), []
    for r in resultados:
        k = (r['expresion'], r['valor_eq'])
        if k not in vistos:
            vistos.add(k); unicos.append(r)
    return sorted(unicos, key=lambda x: (x['error'], x['n']))

# ============================================================
# INTERFAZ
# ============================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self._current_tol = 5.0

        cargar_fuente("fonts/Inter-Regular.ttf")
        cargar_fuente("fonts/JetBrainsMono-Regular.ttf")

        familia_ui, familia_mono = familias_por_plataforma()
        familia_ui   = "Inter"          if Path("fonts/Inter-Regular.ttf").is_file() else familia_ui
        familia_mono = "JetBrains Mono" if Path("fonts/JetBrainsMono-Regular.ttf").is_file() else familia_mono

        self.F_TIT    = ctk.CTkFont(family=familia_ui,   size=22, weight="bold")
        self.F_SUB    = ctk.CTkFont(family=familia_ui,   size=12)
        self.F_LABEL  = ctk.CTkFont(family=familia_ui,   size=11, weight="bold")
        self.F_UI     = ctk.CTkFont(family=familia_ui,   size=14)
        self.F_UI_B   = ctk.CTkFont(family=familia_ui,   size=14, weight="bold")
        self.F_MONO   = ctk.CTkFont(family=familia_mono, size=12)
        self.F_MONO_B = ctk.CTkFont(family=familia_mono, size=13, weight="bold")

        ctk.set_appearance_mode("light")
        self.configure(fg_color=COL_BG)
        self.title("⚡ Calculadora de Resistencias")
        self.geometry("1200x820")
        self.minsize(1000, 720)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._build_header()
        self._build_inputs()
        self._build_status()
        self._build_results()

    # --------------------------------------------------------
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(16, 4))

        center_frame = ctk.CTkFrame(header, fg_color="transparent")
        center_frame.pack(anchor="center")

        title_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        title_frame.pack(anchor="center")

        words = ["CALCULADORA", "DE", "RESISTENCIAS"]
        color_idx = 0

        for i, word in enumerate(words):
            word_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
            word_frame.pack(side="left", padx=(0, 12) if i < len(words) - 1 else 0)
            
            for char in word:
                bg = TINKER_COLORS[color_idx % len(TINKER_COLORS)]
                lbl = ctk.CTkLabel(word_frame, text=char, font=self.F_TIT,
                                   text_color="#ffffff", fg_color=bg,
                                   width=32, height=32, corner_radius=0)
                lbl.pack(side="left", padx=1)
                color_idx += 1

        sub_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        sub_frame.pack(anchor="center", pady=(8, 0))

        ctk.CTkFrame(sub_frame, width=4, height=14, fg_color=TINKER_COLORS[0],
                     corner_radius=2).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(sub_frame,
                     text="Encuentra la combinación perfecta con resistencias comerciales :D",
                     font=self.F_SUB, text_color="#64748b",
                     anchor="w").pack(side="left")

    def _build_inputs(self):
        card = ctk.CTkFrame(self, fg_color=COL_CARD, corner_radius=16,
                            border_width=1, border_color=COL_BORDER)
        card.grid(row=1, column=0, sticky="ew", padx=24, pady=6)
        card.grid_columnconfigure(0, weight=3)
        card.grid_columnconfigure(1, weight=3)
        card.grid_columnconfigure(2, weight=3)
        card.grid_columnconfigure(3, weight=0)

        ctk.CTkLabel(card, text="VALOR DESEADO  (Ω)", font=self.F_LABEL,
                     text_color=COL_DIM, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=(20, 10), pady=(10, 2))
        self.e_obj = ctk.CTkEntry(card, placeholder_text="ej: 500",
                                  font=self.F_UI, height=40, corner_radius=10,
                                  fg_color=COL_INPUT, border_color=COL_BORDER,
                                  border_width=1, text_color=COL_TEXT)
        self.e_obj.grid(row=1, column=0, sticky="ew", padx=(20, 10), pady=(0, 10))

        ctk.CTkLabel(card, text="TOLERANCIA  (%)", font=self.F_LABEL,
                     text_color=COL_DIM, anchor="w"
                     ).grid(row=0, column=1, sticky="w", padx=10, pady=(10, 2))
        self.e_tol = ctk.CTkEntry(card, placeholder_text="ej: 5",
                                  font=self.F_UI, height=40, corner_radius=10,
                                  fg_color=COL_INPUT, border_color=COL_BORDER,
                                  border_width=1, text_color=COL_TEXT)
        self.e_tol.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 10))

        self.btn = ctk.CTkButton(card, text="🔍   Buscar combinaciones",
                                 font=self.F_UI_B, height=40, corner_radius=10,
                                 fg_color=COL_ACCENT, hover_color=COL_ACCENT_HOVER,
                                 text_color="white", command=self.calcular)
        self.btn.grid(row=1, column=2, sticky="ew", padx=(10, 10), pady=(0, 10))

        self.btn_clear = ctk.CTkButton(card, text="🗑️ Limpiar", font=self.F_UI_B,
                                       width=100, height=40, corner_radius=10,
                                       fg_color="transparent", border_width=1,
                                       border_color=COL_BORDER, text_color=COL_DIM,
                                       hover_color="#f1f5f9",
                                       command=self._limpiar_campos)
        self.btn_clear.grid(row=1, column=3, sticky="ew", padx=(0, 20), pady=(0, 10))

        for entry in (self.e_obj, self.e_tol):
            entry.bind("<FocusIn>",  lambda e: e.widget.configure(border_color=COL_BORDER_FOCUS))
            entry.bind("<FocusOut>", lambda e: e.widget.configure(border_color=COL_BORDER))
            entry.bind("<Return>",   lambda e: self.calcular())

    def _build_status(self):
        self.status = ctk.CTkLabel(self, text="Introduce los valores y pulsa Buscar",
                                   font=self.F_UI, text_color=COL_DIM)
        self.status.grid(row=2, column=0, pady=(0, 4))

    def _build_results(self):
        ctk.CTkLabel(self, text="TOP 3 COMBINACIONES", font=self.F_LABEL,
                     text_color=COL_DIM, anchor="w"
                     ).grid(row=3, column=0, sticky="ew", padx=32, pady=(2, 2))

        self.results_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.results_frame.grid(row=4, column=0, sticky="nsew", padx=24, pady=(0, 12))

        ctk.CTkLabel(self.results_frame,
                     text="Introduce un valor y una tolerancia, y pulsa Buscar.",
                     font=self.F_UI, text_color=COL_DIM).pack(pady=40)

    # --------------------------------------------------------
    # Lógica del botón Limpiar
    # --------------------------------------------------------
    def _limpiar_campos(self):
        self.e_obj.delete(0, "end")
        self.e_tol.delete(0, "end")
        self._clear(self.results_frame)
        self.status.configure(text="Introduce los valores y pulsa Buscar", text_color=COL_DIM)
        ctk.CTkLabel(self.results_frame,
                     text="Introduce un valor y una tolerancia, y pulsa Buscar.",
                     font=self.F_UI, text_color=COL_DIM).pack(pady=40)

    # --------------------------------------------------------
    # Dibujo de resistores
    # --------------------------------------------------------
    def _draw_resistor(self, canvas, valor, tolerancia, w=62, h=22):
        mid = h // 2
        lead = int(w * 0.15)
        body_l, body_r = lead, w - lead

        canvas.create_line(0, mid, body_l, mid, fill="#9aa0a8", width=2)
        canvas.create_line(body_r, mid, w, mid, fill="#9aa0a8", width=2)
        canvas.create_rectangle(body_l, 3, body_r, h - 3,
                                fill="#e8d4a8", outline="#8b7355", width=1)

        bands = bandas_resistor(valor, tolerancia)
        if not bands:
            return

        body_w = body_r - body_l
        band_w = max(3, int(body_w * 0.10))

        for frac, color in [(0.10, bands[0]), (0.28, bands[1]), (0.46, bands[2])]:
            x = body_l + int(body_w * frac)
            canvas.create_rectangle(x, 3, x + band_w, h - 3, fill=color, outline="")
        x = body_l + int(body_w * 0.78)
        canvas.create_rectangle(x, 3, x + band_w, h - 3, fill=bands[3], outline="")

    def _resistor_chip(self, parent, valor, bg, accent=COL_BORDER):
        frame = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=8,
                             border_width=1, border_color=accent)
        canvas = Canvas(frame, width=62, height=22, bg="#ffffff", highlightthickness=0)
        self._draw_resistor(canvas, valor, self._current_tol)
        canvas.pack(padx=6, pady=(3, 1))
        ctk.CTkLabel(frame, text=f"{valor:g} Ω", font=self.F_MONO,
                     text_color=COL_TEXT).pack(padx=6, pady=(0, 3))
        return frame

    # --------------------------------------------------------
    # Lógica de UI
    # --------------------------------------------------------
    def calcular(self):
        try:
            objetivo   = float(self.e_obj.get().replace(",", "."))
            tolerancia = float(self.e_tol.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Error", "Introduce números válidos")
            return
        if objetivo <= 0 or tolerancia <= 0:
            messagebox.showerror("Error", "Los valores deben ser positivos")
            return

        self.status.configure(text="⏳  Calculando combinaciones…", text_color=COL_WARN)
        self.btn.configure(state="disabled")
        threading.Thread(target=self._run, args=(objetivo, tolerancia),
                         daemon=True).start()

    def _run(self, objetivo, tolerancia):
        resistencias = obtener_lista_resistencias(tolerancia)
        etiqueta = "E12" if tolerancia >= 10 else "E24"
        resultados = encontrar_mejores_combinaciones(objetivo, resistencias, tolerancia)
        self._current_tol = tolerancia
        self.after(0, self._mostrar, resultados, etiqueta)

    def _mostrar(self, resultados, etiqueta):
        self.btn.configure(state="normal")
        self._clear(self.results_frame)

        if not resultados:
            self.status.configure(
                text="❌  Nada dentro de la tolerancia. Prueba a subir el %.",
                text_color=COL_DANGER)
            ctk.CTkLabel(self.results_frame,
                         text="Sin combinaciones disponibles.\nAumenta la tolerancia o cambia el valor.",
                         font=self.F_UI, text_color=COL_DIM,
                         justify="center").pack(pady=60)
            return

        top = resultados[:3]
        self.status.configure(
            text=f"✅  Top {len(top)} de {len(resultados)} combinaciones  ·  Serie {etiqueta}",
            text_color=COL_SUCCESS)

        for i, r in enumerate(top, 1):
            self._add_result_card(self.results_frame, i, r)

    def _add_result_card(self, parent, idx, r):
        style = CARD_STYLES[idx]
        card = ctk.CTkFrame(
            parent,
            fg_color=style['bg'],
            corner_radius=12,
            border_width=style['border_width'],
            border_color=style['border'],
        )
        card.pack(fill="x", padx=4, pady=4)
        card.grid_columnconfigure(1, weight=1)

        rank = ctk.CTkLabel(card, text=f"#{idx}",
                            font=self.F_UI_B,
                            width=style['badge_size'], height=style['badge_size'],
                            corner_radius=style['badge_size'] // 2,
                            fg_color=style['badge_bg'],
                            text_color="#ffffff")
        rank.grid(row=0, column=0, rowspan=2, padx=(16, 14), pady=10)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=1, sticky="w", pady=(10, 2))

        if style['label']:
            ctk.CTkLabel(info, text=f"  {style['label']}  ",
                         font=self.F_LABEL, text_color="#ffffff",
                         fg_color=style['badge_bg'], corner_radius=6, height=20
                         ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(info, text=r['tipo'].upper(),
                     font=self.F_LABEL, text_color=COL_DIM
                     ).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(info, text=r['expresion'],
                     font=self.F_MONO_B, text_color=COL_TEXT
                     ).pack(side="left")

        chips_row = ctk.CTkFrame(card, fg_color="transparent")
        chips_row.grid(row=1, column=1, sticky="w", pady=(2, 10))
        for valor in r['combinacion']:
            self._resistor_chip(chips_row, valor, bg=style['bg'],
                                accent=style['border']).pack(side="left", padx=(0, 6))

        right = ctk.CTkFrame(card, fg_color="transparent")
        right.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 16), pady=10)

        ctk.CTkLabel(right, text=f"{r['valor_eq']:.2f} Ω",
                     font=self.F_MONO_B, text_color=COL_TEXT).pack(anchor="e")
        
        # --- AQUÍ ESTÁ EL CAMBIO: Añadida la palabra "Error: " ---
        err_chip = ctk.CTkLabel(right, text=f"  Error: {r['error']:.3f}%  ",
                                font=self.F_MONO_B, text_color=COL_INK,
                                fg_color=self._err_color(r['error']),
                                corner_radius=6, height=22)
        err_chip.pack(anchor="e", pady=(4, 0))

    @staticmethod
    def _err_color(err):
        if err < 1.0: return COL_SUCCESS
        if err < 3.0: return COL_LIME
        if err < 7.0: return COL_WARN
        return COL_DANGER

    @staticmethod
    def _clear(frame):
        for w in frame.winfo_children():
            w.destroy()


if __name__ == "__main__":
    App().mainloop()