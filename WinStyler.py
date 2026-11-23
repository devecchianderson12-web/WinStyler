# -*- coding: utf-8 -*-
"""WinStyler - editor visual de barra de tareas, menú Inicio y Explorador (Windows 10/11).
Aplica los cambios con un .bat temporal que se borra al terminar; no instala nada
salvo el módulo opcional del efecto de barra (se elimina con «Restaurar original»)."""
import os
import sys
import json
import time
import math
import colorsys
import base64
import ctypes
import tempfile
import threading
import subprocess
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog

import generador as gen

APP_NAME = "WinStyler"
PW, PH = 720, 430          # tamaño de la vista previa
PALETTE = ["#ff5f6d", "#7b6cf6", "#4ef0c8", "#f7a14c", "#a99cff", "#3ec7f2", "#ffd166", "#ef6fd0"]

# ----------------------------------------------------------------- tema (oscuro neumórfico)
BG = "#12141c"
PANEL = "#1a1d28"
PANEL_HI = "#242838"
PANEL_LO = "#0b0d13"
RAISED = "#232737"
TRACK = "#0c0e15"
LINE = "#2c3144"
TEXT = "#d6daea"
MUTED = "#7d839b"
ACCENT = "#7b6cf6"
ACCENT_HI = "#988cff"
MINT = "#4ef0c8"
CORAL = "#ff5f6d"
SCREEN = "#07080d"

FONTS = {}


def font(name):
    if not FONTS:
        FONTS.update({
            "sm": tkfont.Font(family="Segoe UI", size=9),
            "md": tkfont.Font(family="Segoe UI", size=10),
            "title": tkfont.Font(family="Segoe UI Semibold", size=11),
            "brand": tkfont.Font(family="Segoe UI Semibold", size=19),
            "btn": tkfont.Font(family="Segoe UI Semibold", size=10),
        })
    return FONTS[name]


def resource(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def is_win11():
    try:
        return sys.getwindowsversion().build >= 22000
    except Exception:
        return True


# ----------------------------------------------------------------- opciones
KEEP = ("keep", "—")
SHOWHIDE = [KEEP, ("show", "Mostrar"), ("hide", "Ocultar")]
ONOFF = [KEEP, ("on", "Sí"), ("off", "No")]

CHOICES = {
    "tb_align": ("Alineación de íconos [11]", [KEEP, ("center", "Centro"), ("left", "Izquierda")]),
    "tb_size": ("Altura de la barra [11]", [KEEP, ("small", "Baja"), ("medium", "Media"), ("large", "Alta")]),
    "tb_small_icons": ("Íconos pequeños [10]", ONOFF),
    "tb_search": ("Búsqueda", [KEEP, ("hidden", "Oculta"), ("icon", "Solo ícono"), ("box", "Cuadro de búsqueda"), ("iconlabel", "Ícono y texto")]),
    "tb_taskview": ("Vista de tareas", SHOWHIDE),
    "tb_widgets": ("Widgets [11]", SHOWHIDE),
    "tb_chat": ("Chat / Teams [11]", SHOWHIDE),
    "tb_copilot": ("Botón Copilot [11]", SHOWHIDE),
    "tb_news": ("Noticias e intereses [10]", SHOWHIDE),
    "tb_sd": ("Esquina «Mostrar escritorio» [11]", SHOWHIDE),
    "tb_combine": ("Agrupar botones", [KEEP, ("always", "Siempre"), ("full", "Si la barra está llena"), ("never", "Nunca")]),
    "tb_autohide": ("Ocultar automáticamente", ONOFF),
    "tb_multimon": ("Barra en todas las pantallas", ONOFF),
    "tb_mmmode": ("Botones en otras pantallas", [KEEP, ("all", "En todas las barras"), ("main", "Principal y donde está abierta"), ("own", "Solo donde está abierta")]),
    "tb_seconds": ("Segundos en el reloj", SHOWHIDE),
    "tb_badges": ("Contadores en íconos", ONOFF),
    "tb_flash": ("Parpadeo de aplicaciones [11]", ONOFF),
    "tb_endtask": ("«Finalizar tarea» con clic derecho [11]", ONOFF),
    "tb_peek": ("Vistazo al escritorio (Peek)", ONOFF),
    "tb_lastactive": ("Clic abre la última ventana", ONOFF),
    "tb_tray_all": ("Todos los íconos de la bandeja [10]", ONOFF),
    "tb_animations": ("Animaciones de la barra", ONOFF),
    "tb_effect": ("Estilo de fondo", [("keep", "Sin cambio"), ("transparent", "Transparente (íconos flotando)"),
                                      ("translucent", "Translúcida"), ("solid", "Color sólido"),
                                      ("gradient", "Degradado"), ("default", "Predeterminado de Windows")]),
    "tb_stroke": ("Línea superior de la barra", SHOWHIDE),
    "sm_effect": ("Fondo del menú", [("keep", "Sin cambio"), ("transparent", "Transparente (íconos flotando)"),
                                    ("translucent", "Translúcido"), ("solid", "Color sólido"),
                                    ("gradient", "Degradado"), ("default", "Predeterminado de Windows")]),
    "sm_shadow": ("Sombra del menú", SHOWHIDE),
    "sm_border": ("Borde del menú", SHOWHIDE),
    "sm_search": ("Cuadro de búsqueda", SHOWHIDE),
    "sm_rec": ("Sección «Recomendado»", SHOWHIDE),
    "tb_theme": ("Tema de Windows (barra e Inicio)", [KEEP, ("dark", "Oscuro"), ("light", "Claro")]),
    "apps_theme": ("Tema de las aplicaciones", [KEEP, ("dark", "Oscuro"), ("light", "Claro")]),
    "tb_color_on": ("Acento en barra e Inicio", ONOFF),
    "border_color_on": ("Acento en bordes y títulos", ONOFF),
    "transparency": ("Efectos de transparencia", [KEEP, ("off", "No"), ("normal", "Sí"), ("extra", "Extra [10]")]),
    "min_anim": ("Animar minimizar / maximizar", ONOFF),
    "st_hide_rec": ("Quitar recomendados [11]", ONOFF),
    "st_layout": ("Distribución de Inicio [11]", [KEEP, ("default", "Predeterminada"), ("pins", "Más anclados"), ("recs", "Más recomendados")]),
    "st_suggestions": ("Sugerencias y anuncios", [KEEP, ("on", "Permitir"), ("off", "Quitar")]),
    "st_most_used": ("Aplicaciones más usadas", SHOWHIDE),
    "st_account_notif": ("Avisos de la cuenta [11]", SHOWHIDE),
    "st_web_search": ("Resultados web (Bing)", [KEEP, ("on", "Permitir"), ("off", "Quitar")]),
    "st_search_highlights": ("Destacados de búsqueda", [KEEP, ("on", "Mostrar"), ("off", "Quitar")]),
    "ex_ext": ("Extensiones de archivo", SHOWHIDE),
    "ex_hidden": ("Archivos ocultos", SHOWHIDE),
    "ex_launch": ("Abrir el Explorador en", [KEEP, ("pc", "Este equipo"), ("home", "Inicio"), ("downloads", "Descargas")]),
    "ex_compact": ("Vista compacta", ONOFF),
    "ex_checkbox": ("Casillas de selección", ONOFF),
    "ex_recent": ("Recientes y frecuentes", SHOWHIDE),
    "ex_classic": ("Menú contextual clásico [11]", ONOFF),
}

CLEAN = {"tb_search": "hidden", "tb_taskview": "hide", "tb_widgets": "hide", "tb_chat": "hide",
         "tb_copilot": "hide", "tb_news": "hide", "st_hide_rec": "on", "st_suggestions": "off",
         "st_web_search": "off", "st_search_highlights": "off", "st_account_notif": "hide"}
FLOAT = {"tb_effect": "transparent", "tb_stroke": "hide", "tb_align": "center", "tb_search": "hidden",
         "sm_effect": "translucent", "sm_opacity": 45, "sm_tint_on": True, "sm_tint": "#14161F",
         "sm_shadow": "hide", "sm_corner": 16,
         "tb_taskview": "hide", "tb_widgets": "hide", "tb_chat": "hide", "tb_copilot": "hide",
         "tb_news": "hide", "tb_theme": "dark"}
COMPACT = {"sm_search": "hide", "sm_rec": "hide", "sm_height": 560, "sm_corner": 12}
PERF = {"tb_animations": "off", "min_anim": "off", "transparency": "off", "tb_badges": "off",
        "tb_flash": "off", "menu_delay": 0, "tb_hover_ms": 100}


# ----------------------------------------------------------------- colores
def rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def hexs(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in c)


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def wall(x, W, yf):
    base = mix((16, 22, 48), (46, 26, 86), x / float(W))
    return mix(base, (7, 8, 18), yf * 0.55)


def rrect(c, x1, y1, x2, y2, r=6, **kw):
    r = max(0, min(r, (x2 - x1) / 2.0, (y2 - y1) / 2.0))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


def effective(cfg, style):
    def g(k, d):
        v = cfg.get(k, "keep")
        return d if v == "keep" else v

    win11 = style == "11"
    e = {"win11": win11}
    e["align"] = g("tb_align", "center") if win11 else "left"
    if win11:
        e["h"] = {"small": 34, "medium": 44, "large": 54}[g("tb_size", "medium")]
    else:
        e["h"] = 34 if g("tb_small_icons", "off") == "on" else 42
    e["search"] = g("tb_search", "box")
    e["taskview"] = g("tb_taskview", "show") == "show"
    e["widgets"] = win11 and g("tb_widgets", "show") == "show"
    e["chat"] = win11 and g("tb_chat", "show") == "show"
    e["copilot"] = win11 and g("tb_copilot", "show") == "show"
    e["news"] = (not win11) and g("tb_news", "show") == "show"
    e["combine"] = g("tb_combine", "always")
    e["seconds"] = g("tb_seconds", "hide") == "show"
    e["autohide"] = g("tb_autohide", "off") == "on"
    e["badges"] = g("tb_badges", "on") == "on"
    e["sd"] = win11 and g("tb_sd", "show") == "show"
    accent = rgb(cfg.get("accent_color", "#0078D4"))
    if cfg.get("tb_color_on") == "on":
        base = accent
    elif g("tb_theme", "dark") == "light":
        base = (240, 240, 240)
    else:
        base = (32, 32, 32)
    e["base"] = base
    e["fg"] = (255, 255, 255) if lum(base) < 140 else (20, 20, 20)
    e["alpha"] = {"off": 1.0, "normal": 0.86, "extra": 0.55}[g("transparency", "normal")]
    e["border"] = accent if cfg.get("border_color_on") == "on" else None

    # fondo de la barra (efecto de wstb.dll)
    eff = cfg.get("tb_effect", "keep")
    tint = rgb(cfg.get("tb_tint") or "#14161F")
    tb_base, tb_alpha = base, e["alpha"]
    e["tb_base2"] = rgb(cfg.get("tb_tint2") or "#7B6CF6") if eff == "gradient" else None
    if eff == "transparent":
        tb_alpha = 0.0
    elif eff == "translucent":
        tb_alpha = max(0, min(100, int(cfg.get("tb_opacity", 50)))) / 100.0
        if cfg.get("tb_tint_on"):
            tb_base = tint
    elif eff in ("solid", "gradient"):
        tb_base, tb_alpha = tint, max(0, min(100, int(cfg.get("tb_opacity", 100)))) / 100.0
    under = mix(wall(PW / 2.0, PW, 0.97), tb_base, tb_alpha)
    e["tb_base"], e["tb_alpha"], e["tb_under"] = tb_base, tb_alpha, under
    e["tb_fg"] = (255, 255, 255) if lum(under) < 140 else (20, 20, 20)
    stroke = cfg.get("tb_stroke", "keep")
    e["stroke"] = stroke == "show" or (stroke == "keep" and eff != "transparent")

    # menú Inicio (wstb.dll)
    seff = cfg.get("sm_effect", "keep")
    stint = rgb(cfg.get("sm_tint") or "#14161F")
    e["sm_base2"] = None
    if seff == "transparent":
        e["alpha"] = 0.0
    elif seff == "translucent":
        e["alpha"] = max(0, min(100, int(cfg.get("sm_opacity", 60)))) / 100.0
        if cfg.get("sm_tint_on"):
            e["base"] = stint
    elif seff in ("solid", "gradient"):
        e["base"], e["alpha"] = stint, max(0, min(100, int(cfg.get("sm_opacity", 100)))) / 100.0
        if seff == "gradient":
            e["sm_base2"] = rgb(cfg.get("sm_tint2") or "#7B6CF6")
    if seff in ("transparent", "translucent", "solid", "gradient"):
        e["fg"] = (255, 255, 255) if lum(mix(wall(PW / 2, PW, 0.5), e["base"], e["alpha"])) < 140 else (20, 20, 20)
    e["sm_corner"] = cfg.get("sm_corner")
    e["sm_k"], e["sm_h"] = (cfg.get("sm_scale") or 100) / 100.0, cfg.get("sm_height")
    e["sm_search"] = cfg.get("sm_search", "keep") != "hide"
    e["sm_shadow"] = cfg.get("sm_shadow", "keep") == "show" or (cfg.get("sm_shadow", "keep") == "keep" and seff != "transparent")
    e["sm_border"] = cfg.get("sm_border", "keep") != "hide" and seff != "transparent"
    e["hide_rec"] = cfg.get("st_hide_rec") == "on" or cfg.get("sm_rec") == "hide"
    e["layout"] = g("st_layout", "default")
    e["suggest"] = g("st_suggestions", "on") == "on"
    e["most_used"] = g("st_most_used", "show") == "show"
    e["folders"] = cfg.get("folders") or []
    return e


# ----------------------------------------------------------------- vista previa
_WALL = {}


def wallpaper(c, W, H):
    """Fondo de escritorio (imagen en caché): degradado con rejilla, estilo pantalla XY."""
    key = (W, H)
    if key not in _WALL:
        img = tk.PhotoImage(master=c, width=W, height=H)
        cx, cy = W * 0.5, H * 0.46
        rows = []
        for y in range(H):
            yf = y / float(H)
            row = []
            for x in range(0, W, 2):
                col = wall(x, W, yf)
                d = ((x - cx) ** 2 + ((y - cy) * 1.6) ** 2) ** 0.5
                glow = max(0.0, 1.0 - d / (W * 0.45)) ** 2 * 0.35
                col = mix(col, (60, 50, 140), glow)
                hx = hexs(col)
                row.append(hx)
                row.append(hx)
            rows.append("{" + " ".join(row[:W]) + "}")
        img.put(" ".join(rows))
        _WALL[key] = img
    return _WALL[key]


def paint(c, cfg, style, show_start, W=PW, H=PH):
    c.delete("all")
    e = effective(cfg, style)
    win11 = e["win11"]

    c.create_image(0, 0, image=wallpaper(c, W, H), anchor="nw")
    cx, cy = W * 0.5, H * 0.46
    grid = hexs(mix(wall(W / 2, W, 0.5), (120, 110, 220), 0.18))
    for i in range(1, 6):
        rx, ry = i * W * 0.085, i * H * 0.075
        c.create_rectangle(cx - rx, cy - ry, cx + rx, cy + ry, outline=grid)
    c.create_line(cx, cy - H * 0.42, cx, cy + H * 0.42, fill=grid)
    c.create_line(cx - W * 0.45, cy, cx + W * 0.45, cy, fill=grid)
    for (dx, dy, col, r) in ((0, 0, MINT, 7), (-0.24, 0.12, ACCENT, 6), (-0.16, 0.25, CORAL, 6)):
        px, py = cx + dx * W, cy + dy * H
        under = wall(px, W, py / H)
        for k in range(5, 0, -1):
            rr = r + k * 4
            c.create_oval(px - rr, py - rr, px + rr, py + rr, outline="",
                          fill=hexs(mix(under, rgb(col), 0.08 * (6 - k))))
        c.create_oval(px - r, py - r, px + r, py + r, fill=col, outline="")
    rrect(c, 34, 28, 214, 132, 10, fill="#1c2033", outline="#2c3148")
    for i, col in enumerate((CORAL, "#f7a14c", MINT)):
        c.create_oval(46 + i * 12, 38, 54 + i * 12, 46, fill=col, outline="")
    c.create_text(124, 86, text="Ventana de fondo", fill="#9aa1bd", font=("Segoe UI", 9))

    tbh = e["h"]
    y0 = H - (4 if e["autohide"] else tbh)
    if e["tb_alpha"] > 0:
        for x in range(0, W, 6):
            b = mix(e["tb_base"], e["tb_base2"], x / float(W)) if e["tb_base2"] else e["tb_base"]
            col = mix(wall(x, W, 0.97), b, e["tb_alpha"])
            c.create_rectangle(x, y0, x + 6, H, fill=hexs(col), outline="")
    if e["border"]:
        c.create_line(0, y0, W, y0, fill=hexs(e["border"]), width=2)
    elif e["stroke"]:
        c.create_line(0, y0, W, y0, fill=hexs(mix(e["tb_under"], e["tb_fg"], 0.16)))

    if e["autohide"]:
        c.create_text(W - 8, y0 - 10, text="Barra oculta automáticamente", anchor="e",
                      fill="#ffffff", font=("Segoe UI", 8))
    else:
        _taskbar(c, e, W, H, y0, tbh, hexs(e["tb_fg"]))

    if show_start:
        bottom = y0 - 10
        if win11:
            last = (c.find_all() or (0,))[-1]
            _start11(c, e, W, bottom)
            if e["sm_k"] < 1.0:
                cx = (W / 2.0) if e["align"] != "left" else 8
                for item in c.find_all():
                    if item > last:
                        c.scale(item, cx, bottom, e["sm_k"], e["sm_k"])
        else:
            _start10(c, e, W, bottom - 2)


def _taskbar(c, e, W, H, y0, tbh, fgh):
    win11 = e["win11"]
    cy = y0 + tbh / 2.0
    under, fg = e["tb_under"], e["tb_fg"]
    els = [("start", 34 if win11 else 46)]
    if e["search"] != "hidden":
        w = {"icon": 34, "box": 150 if win11 else 190, "iconlabel": 90}[e["search"]]
        els.append(("search", w))
    if e["taskview"]:
        els.append(("taskview", 34))
    if e["widgets"] and e["align"] == "left":
        els.append(("widgets", 34))
    if e["chat"]:
        els.append(("chat", 34))
    if e["copilot"]:
        els.append(("copilot", 34))
    wide = e["combine"] == "never"
    for i in range(4):
        els.append(("app%d" % i, 104 if wide else 34))
    gap = 2
    total = sum(w for _, w in els) + gap * (len(els) - 1)
    x = (W - total) / 2.0 if e["align"] == "center" else 8
    accent = "#4cc2ff"
    s = min(22, tbh - 14)
    for kind, w in els:
        mx = x + (34 if kind.startswith("app") and wide else w) / 2.0
        if kind == "start":
            q = max(4, s // 2 - 1)
            for dx in (-1, 0):
                for dy in (-1, 0):
                    c.create_rectangle(mx + dx * (q + 1) + (0 if dx else 1), cy + dy * (q + 1) + (0 if dy else 1),
                                       mx + dx * (q + 1) + (0 if dx else 1) + q, cy + dy * (q + 1) + (0 if dy else 1) + q,
                                       fill=accent, outline="")
        elif kind == "search":
            if e["search"] == "icon":
                c.create_oval(mx - 6, cy - 7, mx + 4, cy + 3, outline=fgh, width=2)
                c.create_line(mx + 3, cy + 3, mx + 8, cy + 8, fill=fgh, width=2)
            else:
                rrect(c, x, cy - 13, x + w, cy + 13, 12, fill=hexs(mix(under, fg, 0.12)),
                      outline=hexs(mix(under, fg, 0.25)))
                c.create_oval(x + 8, cy - 5, x + 16, cy + 3, outline=fgh, width=1)
                c.create_text(x + 22, cy, text="Buscar" if e["search"] == "iconlabel" else "Escribe aquí para buscar",
                              anchor="w", fill=fgh, font=("Segoe UI", 8))
        elif kind == "taskview":
            c.create_rectangle(mx - 8, cy - 6, mx + 3, cy + 5, outline=fgh)
            c.create_rectangle(mx - 3, cy - 3, mx + 8, cy + 8, outline=fgh)
        elif kind == "widgets":
            for dx in (0, 1):
                for dy in (0, 1):
                    c.create_rectangle(mx - 8 + dx * 9, cy - 8 + dy * 9, mx + dx * 9 - 1, cy + dy * 9 - 1,
                                       fill=PALETTE[(dx * 2 + dy + 1) % 8], outline="")
        elif kind == "chat":
            rrect(c, mx - 9, cy - 8, mx + 9, cy + 7, 5, fill="#6264a7", outline="")
            c.create_oval(mx - 2, cy - 2, mx + 2, cy + 2, fill="#ffffff", outline="")
        elif kind == "copilot":
            c.create_oval(mx - 9, cy - 9, mx + 9, cy + 9, fill="#00b7c3", outline="")
            c.create_oval(mx - 3, cy - 3, mx + 9, cy + 9, fill="#8e8cd8", outline="")
        else:
            i = int(kind[3:])
            rrect(c, mx - s / 2.0, cy - s / 2.0, mx + s / 2.0, cy + s / 2.0, 5, fill=PALETTE[i % 8], outline="")
            if wide:
                c.create_text(x + 36, cy, text="App %d" % (i + 1), anchor="w", fill=fgh, font=("Segoe UI", 8))
            if i == 0:
                c.create_line(mx - 6, y0 + tbh - 3, mx + 6, y0 + tbh - 3, fill=accent, width=2)
            if i == 2 and e["badges"]:
                c.create_oval(mx + s / 2.0 - 7, cy - s / 2.0 - 3, mx + s / 2.0 + 3, cy - s / 2.0 + 7,
                              fill=CORAL, outline="")
        x += w + gap

    # bandeja del sistema
    clock = "12:34:56" if e["seconds"] else "12:34"
    right = W - (14 if e["sd"] else 10)
    c.create_text(right, cy - 7, text=clock, anchor="e", fill=fgh, font=("Segoe UI", 8))
    c.create_text(right, cy + 7, text="15/11/2026", anchor="e", fill=fgh, font=("Segoe UI", 7))
    if e["sd"]:
        c.create_line(W - 5, y0 + 8, W - 5, y0 + tbh - 8, fill=hexs(mix(under, fg, 0.35)))
    tx = right - 80
    for i in range(3):
        c.create_rectangle(tx - i * 16 - 10, cy - 5, tx - i * 16, cy + 5, outline=fgh)
    if e["news"]:
        c.create_text(tx - 62, cy, text="21°C", anchor="e", fill=fgh, font=("Segoe UI", 8))
    if e["widgets"] and e["align"] == "center":
        c.create_text(12, cy - 6, text="21°C", anchor="w", fill=fgh, font=("Segoe UI", 9, "bold"))
        c.create_text(12, cy + 7, text="Soleado", anchor="w", fill=fgh, font=("Segoe UI", 7))


def _tile(c, x, y, size, color, fgh, folder=None):
    if folder is None:
        rrect(c, x, y, x + size, y + size, 7, fill=color, outline="")
        return
    rrect(c, x, y, x + size, y + size, 7, fill=hexs(mix(rgb(color) if isinstance(color, str) else color, (255, 255, 255), 0.55)), outline="")
    h = size / 2.0 - 4
    for i in range(4):
        dx, dy = i % 2, i // 2
        c.create_rectangle(x + 3 + dx * (h + 2), y + 3 + dy * (h + 2),
                           x + 3 + dx * (h + 2) + h, y + 3 + dy * (h + 2) + h,
                           fill=PALETTE[(i + 2) % 8], outline="")


def _start11(c, e, W, bottom):
    base, fg = e["base"], e["fg"]
    fgh = hexs(fg)
    layout = e["layout"]
    rows = {"default": 3, "pins": 4, "recs": 2}[layout] + (2 if e["hide_rec"] else 0)
    nrec = {"default": 4, "pins": 2, "recs": 6}[layout]
    rec_h = 0 if e["hide_rec"] else 24 + ((nrec + 1) // 2) * 34
    top = 0 if e["sm_search"] else -34
    pw = 380
    ph = 80 + top + rows * 58 + rec_h + 56
    if e["sm_h"]:
        ph = min(ph, int(ph * min(1.0, e["sm_h"] / 726.0)) + 40)
    px = 8 if e["align"] == "left" else (W - pw) // 2
    py = bottom - ph
    rad = 12 if e["sm_corner"] is None else max(0, int(e["sm_corner"] * 0.6))
    pcol = mix(wall(W / 2, W, 0.5), base, min(1.0, e["alpha"] + (0.08 if e["alpha"] > 0 else 0)))
    if e["sm_shadow"]:
        rrect(c, px + 4, py + 6, px + pw + 4, py + ph + 6, rad, fill=hexs(mix(wall(W / 2, W, 0.6), (0, 0, 0), 0.45)), outline="")
    if e["sm_base2"]:
        steps = 24
        for i in range(steps):
            t0, t1 = i / float(steps), (i + 1) / float(steps)
            col = mix(wall(W / 2, W, 0.5), mix(base, e["sm_base2"], (t0 + t1) / 2), e["alpha"])
            r = rad if i in (0, steps - 1) else 0
            rrect(c, px, py + ph * t0, px + pw, py + ph * t1 + 1, r, fill=hexs(col), outline="")
        pcol = mix(wall(W / 2, W, 0.5), mix(base, e["sm_base2"], 0.5), e["alpha"])
    elif e["alpha"] > 0:
        rrect(c, px, py, px + pw, py + ph, rad, fill=hexs(pcol), outline="")
    if e["border"] or e["sm_border"]:
        out = hexs(e["border"]) if e["border"] else hexs(mix(pcol, fg, 0.15))
        rrect(c, px, py, px + pw, py + ph, rad, fill="", outline=out, width=2 if e["border"] else 1)
    if e["sm_search"]:
        rrect(c, px + 16, py + 14, px + pw - 16, py + 42, 14, fill=hexs(mix(pcol, fg, 0.1)), outline=hexs(mix(pcol, fg, 0.2)))
        c.create_text(px + 30, py + 28, text="Buscar aplicaciones, configuración y documentos",
                      anchor="w", fill=fgh, font=("Segoe UI", 8))
    bottom_y = py + ph
    py += top
    c.create_text(px + 20, py + 62, text="Anclado", anchor="w", fill=fgh, font=("Segoe UI", 9, "bold"))
    c.create_text(px + pw - 20, py + 62, text="Todas  >", anchor="e", fill=fgh, font=("Segoe UI", 8))
    cols = 6 if pw >= 300 else 4
    cell = (pw - 40) / float(cols)
    tiles = [("f", f) for f in e["folders"]]
    total = rows * cols
    tiles = tiles[:total]
    while len(tiles) < total:
        tiles.append(("a", None))
    for i, (kind, f) in enumerate(tiles):
        cx = px + 20 + (i % cols) * cell
        cy = py + 76 + (i // cols) * 58
        ix = cx + (cell - 30) / 2.0
        if kind == "f":
            _tile(c, ix, cy, 30, PALETTE[1], fgh, folder=f)
            label = (f.get("name") or "")[:8]
            c.create_text(cx + cell / 2.0, cy + 40, text=label, fill=fgh, font=("Segoe UI", 7))
        else:
            _tile(c, ix, cy, 30, hexs(rgb(PALETTE[i % 8])), fgh)
            c.create_rectangle(cx + cell / 2.0 - 12, cy + 38, cx + cell / 2.0 + 12, cy + 40,
                               fill=hexs(mix(pcol, fg, 0.5)), outline="")
    ry = py + 76 + rows * 58
    if not e["hide_rec"]:
        c.create_text(px + 20, ry + 8, text="Recomendado", anchor="w", fill=fgh, font=("Segoe UI", 9, "bold"))
        for i in range(nrec):
            rx = px + 20 + (i % 2) * ((pw - 40) / 2.0)
            rowy = ry + 26 + (i // 2) * 34
            rrect(c, rx, rowy, rx + 22, rowy + 22, 4, fill=PALETTE[(i + 3) % 8], outline="")
            c.create_rectangle(rx + 30, rowy + 4, rx + 100, rowy + 7, fill=hexs(mix(pcol, fg, 0.6)), outline="")
            c.create_rectangle(rx + 30, rowy + 12, rx + 70, rowy + 14, fill=hexs(mix(pcol, fg, 0.35)), outline="")
    fy = bottom_y - 40
    if e["alpha"] > 0 or e["sm_base2"]:   # menú achicado: lo que no entra queda tapado
        c.create_rectangle(px + 2, fy - 3, px + pw - 2, bottom_y - 2, fill=hexs(pcol), outline="")
    c.create_line(px, fy, px + pw, fy, fill=hexs(mix(pcol, fg, 0.15)))
    c.create_oval(px + 20, fy + 8, px + 44, fy + 32, fill=hexs(mix(pcol, fg, 0.4)), outline="")
    c.create_text(px + 52, fy + 20, text="Usuario", anchor="w", fill=fgh, font=("Segoe UI", 8))
    c.create_oval(px + pw - 38, fy + 11, px + pw - 20, fy + 29, outline=fgh, width=2)
    c.create_line(px + pw - 29, fy + 8, px + pw - 29, fy + 20, fill=fgh, width=2)


def _start10(c, e, W, bottom):
    base, fg = e["base"], e["fg"]
    fgh = hexs(fg)
    pw, ph = 440, 410
    px, py = 0, bottom - ph
    pcol = mix(wall(120, W, 0.5), base, min(1.0, e["alpha"] + 0.1))
    out = hexs(e["border"]) if e["border"] else hexs(mix(pcol, fg, 0.12))
    c.create_rectangle(px, py, px + pw, py + ph, fill=hexs(pcol), outline=out)
    c.create_rectangle(px, py, px + 40, py + ph, fill=hexs(mix(pcol, (0, 0, 0), 0.25)), outline="")
    for i in range(4):
        c.create_rectangle(px + 13, py + ph - 30 - i * 32, px + 27, py + ph - 16 - i * 32, outline=fgh)
    y = py + 14
    if e["most_used"]:
        c.create_text(px + 52, y, text="Más usadas", anchor="w", fill=fgh, font=("Segoe UI", 8, "bold"))
        y += 18
        for i in range(3):
            c.create_rectangle(px + 52, y, px + 70, y + 18, fill=PALETTE[i], outline="")
            c.create_rectangle(px + 78, y + 6, px + 150, y + 9, fill=hexs(mix(pcol, fg, 0.5)), outline="")
            y += 26
    if e["suggest"]:
        c.create_text(px + 52, y + 2, text="Sugerido", anchor="w", fill=fgh, font=("Segoe UI", 8, "bold"))
        y += 18
        c.create_rectangle(px + 52, y, px + 70, y + 18, fill="#ffb900", outline="")
        c.create_text(px + 78, y + 9, text="Instalar app", anchor="w", fill=fgh, font=("Segoe UI", 8))
        y += 28
    c.create_text(px + 52, y + 2, text="A", anchor="w", fill=fgh, font=("Segoe UI", 8, "bold"))
    y += 18
    for i in range(4):
        if y + 22 > py + ph - 10:
            break
        c.create_rectangle(px + 52, y, px + 70, y + 18, fill=PALETTE[(i + 3) % 8], outline="")
        c.create_rectangle(px + 78, y + 6, px + 140, y + 9, fill=hexs(mix(pcol, fg, 0.5)), outline="")
        y += 26
    tx = px + 190
    c.create_text(tx, py + 14, text="Productividad", anchor="w", fill=fgh, font=("Segoe UI", 8, "bold"))
    tiles = [("f", f) for f in e["folders"]][:6]
    while len(tiles) < 6:
        tiles.append(("a", None))
    for i, (kind, f) in enumerate(tiles):
        x = tx + (i % 3) * 78
        yy = py + 34 + (i // 3) * 78
        if kind == "f":
            _tile(c, x, yy, 72, PALETTE[1], fgh, folder=f)
            c.create_text(x + 36, yy + 62, text=(f.get("name") or "")[:10], fill=fgh, font=("Segoe UI", 7))
        else:
            _tile(c, x, yy, 72, hexs(rgb(PALETTE[(i + 1) % 8])), fgh)
    c.create_text(tx, py + 200, text="Explorar", anchor="w", fill=fgh, font=("Segoe UI", 8, "bold"))
    for i in range(3):
        _tile(c, tx + i * 78, py + 220, 72, hexs(rgb(PALETTE[(i + 4) % 8])), fgh)


# ----------------------------------------------------------------- controles personalizados
class Segmented(tk.Canvas):
    """Selector en forma de píldora (como los interruptores del panel)."""

    def __init__(self, master, options, command=None, bg=PANEL):
        self.opts = list(options)
        self.command = command
        self.value = self.opts[0][0]
        f = font("sm")
        self.widths = [max(30, f.measure(lbl) + 22) for _, lbl in self.opts]
        self.W, self.H = sum(self.widths) + 6, 28
        super().__init__(master, width=self.W, height=self.H, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Button-1>", self._click)
        self.draw()

    @staticmethod
    def fits(options, limit=250):
        f = font("sm")
        return sum(max(30, f.measure(lbl) + 22) for _, lbl in options) + 6 <= limit

    def draw(self):
        self.delete("all")
        rrect(self, 0, 0, self.W, self.H, 14, fill=TRACK, outline=PANEL_LO)
        x = 3
        for (code, lbl), w in zip(self.opts, self.widths):
            on = code == self.value
            if on:
                rrect(self, x, 3, x + w, self.H - 3, 11, fill=ACCENT if code != "keep" else LINE, outline="")
            self.create_text(x + w / 2.0, self.H / 2.0, text=lbl, font=font("sm"),
                             fill="#ffffff" if on else MUTED)
            x += w

    def _click(self, ev):
        x = 3
        for (code, _), w in zip(self.opts, self.widths):
            if x <= ev.x < x + w:
                if code != self.value:
                    self.value = code
                    self.draw()
                    if self.command:
                        self.command()
                return
            x += w

    def get(self):
        return self.value

    def set(self, code):
        if any(c == code for c, _ in self.opts):
            self.value = code
            self.draw()


class Dropdown(tk.Canvas):
    """Lista desplegable oscura."""

    def __init__(self, master, options, command=None, bg=PANEL, width=230):
        self.opts = [(c, "Sin cambio" if l == "—" else l) for c, l in options]
        self.command = command
        self.value = self.opts[0][0]
        self.W, self.H = width, 30
        self.pop = None
        super().__init__(master, width=self.W, height=self.H, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Button-1>", self._open)
        self.draw()

    def label(self):
        return next((l for c, l in self.opts if c == self.value), "")

    def draw(self):
        self.delete("all")
        rrect(self, 0, 0, self.W, self.H, 14, fill=TRACK, outline=PANEL_LO)
        active = self.value != "keep"
        if active:
            self.create_oval(12, self.H / 2 - 3, 18, self.H / 2 + 3, fill=MINT, outline="")
        self.create_text(26 if active else 14, self.H / 2.0, text=self.label(), anchor="w",
                         font=font("sm"), fill=TEXT if active else MUTED)
        x, y = self.W - 18, self.H / 2.0
        self.create_line(x - 4, y - 2, x, y + 2, x + 4, y - 2, fill=MUTED, width=2)

    def _open(self, _ev=None):
        if self.pop:
            return self._close()
        top = tk.Toplevel(self)
        top.overrideredirect(True)
        top.configure(bg=LINE)
        top.attributes("-topmost", True)
        inner = tk.Frame(top, bg=PANEL_HI)
        inner.pack(padx=1, pady=1)
        for code, lbl in self.opts:
            on = code == self.value
            lab = tk.Label(inner, text=lbl, anchor="w", padx=14, pady=6, font=font("sm"),
                           bg=ACCENT if on else PANEL_HI, fg="#ffffff" if on else TEXT, width=0)
            lab.pack(fill="x")
            lab.bind("<Enter>", lambda e, w=lab, o=on: w.configure(bg=ACCENT_HI if o else RAISED))
            lab.bind("<Leave>", lambda e, w=lab, o=on: w.configure(bg=ACCENT if o else PANEL_HI))
            lab.bind("<ButtonRelease-1>", lambda e, c=code: self._pick(c))
        top.update_idletasks()
        w = max(self.W, top.winfo_reqwidth())
        top.geometry("%dx%d+%d+%d" % (w, top.winfo_reqheight(), self.winfo_rootx(), self.winfo_rooty() + self.H + 4))
        top.bind("<Button-1>", self._outside)
        top.bind("<Escape>", lambda e: self._close())
        top.grab_set()
        top.focus_set()
        self.pop = top

    def _outside(self, ev):
        p = self.pop
        if p and not (p.winfo_rootx() <= ev.x_root < p.winfo_rootx() + p.winfo_width()
                      and p.winfo_rooty() <= ev.y_root < p.winfo_rooty() + p.winfo_height()):
            self._close()

    def _close(self):
        if self.pop:
            try:
                self.pop.grab_release()
                self.pop.destroy()
            except tk.TclError:
                pass
        self.pop = None

    def _pick(self, code):
        self._close()
        if code != self.value:
            self.value = code
            self.draw()
            if self.command:
                self.command()

    def get(self):
        return self.value

    def set(self, code):
        if any(c == code for c, _ in self.opts):
            self.value = code
            self.draw()


class Toggle(tk.Canvas):
    """Interruptor deslizante."""

    def __init__(self, master, value=False, command=None, bg=PANEL):
        super().__init__(master, width=48, height=26, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.value = bool(value)
        self.command = command
        self.bind("<Button-1>", self._click)
        self.draw()

    def draw(self):
        self.delete("all")
        rrect(self, 1, 1, 47, 25, 12, fill=ACCENT if self.value else TRACK, outline=PANEL_LO)
        x = 34 if self.value else 14
        self.create_oval(x - 9, 4, x + 9, 22, fill="#eef0fa" if self.value else "#4b5166", outline="")

    def _click(self, _ev):
        self.value = not self.value
        self.draw()
        if self.command:
            self.command()

    def get(self):
        return self.value

    def set(self, v):
        self.value = bool(v)
        self.draw()


class Knob(tk.Canvas):
    """Perilla giratoria (arrastrar arriba/abajo o rueda del ratón).
    Si es opcional, el LED indica si se aplica; doble clic lo activa/desactiva."""

    def __init__(self, master, label, lo, hi, value, fmt="{}", step=1, command=None,
                 optional=False, active=True, size=74, bg=PANEL):
        self.label, self.lo, self.hi, self.step = label, lo, hi, step
        self.fmt, self.command, self.optional = fmt, command, optional
        self.value, self.active, self.size = value, active or not optional, size
        super().__init__(master, width=size + 34, height=size + 44, bg=bg, highlightthickness=0, bd=0, cursor="sb_v_double_arrow")
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<MouseWheel>", self._wheel)
        self.bind("<Double-Button-1>", self._toggle)
        self._y0 = self._v0 = 0
        self.draw()

    def draw(self):
        self.delete("all")
        s = self.size
        cx, cy = (s + 34) / 2.0, s / 2.0 + 6
        R = s / 2.0 - 2
        frac = (self.value - self.lo) / float(self.hi - self.lo)
        on = self.active
        self.create_oval(cx - R + 3, cy - R + 5, cx + R + 3, cy + R + 5, fill=PANEL_LO, outline="")
        self.create_oval(cx - R - 2, cy - R - 2, cx + R - 2, cy + R - 2, fill=PANEL_HI, outline="")
        self.create_oval(cx - R, cy - R, cx + R, cy + R, fill=PANEL, outline="")
        box = (cx - R + 5, cy - R + 5, cx + R - 5, cy + R - 5)
        self.create_arc(*box, start=225, extent=-270, style="arc", outline=TRACK, width=6)
        if frac > 0.003:
            self.create_arc(*box, start=225, extent=-270 * frac, style="arc",
                            outline=ACCENT if on else "#454b62", width=6)
        rin = R - 13
        for i in range(9):
            t = i / 8.0
            r = rin * (1 - t * 0.85)
            off = -t * rin * 0.18
            col = hexs(mix(rgb("#1e2231"), rgb("#363c54"), t))
            self.create_oval(cx - r + off, cy - r + off, cx + r + off, cy + r + off, fill=col, outline="")
        a = math.radians(225 - 270 * frac)
        x1, y1 = cx + math.cos(a) * rin * 0.35, cy - math.sin(a) * rin * 0.35
        x2, y2 = cx + math.cos(a) * rin * 0.82, cy - math.sin(a) * rin * 0.82
        self.create_line(x1, y1, x2, y2, fill=ACCENT_HI if on else MUTED, width=3, capstyle="round")
        if self.optional:
            self.create_oval(s + 34 - 14, 4, s + 34 - 6, 12, fill=MINT if on else TRACK, outline=PANEL_LO)
        self.create_text(cx, s + 18, text=self.label, font=font("sm"), fill=TEXT if on else MUTED)
        self.create_text(cx, s + 34, text=self.fmt.format(self.value) if on else "sin cambio",
                         font=font("sm"), fill=MINT if on else MUTED)

    def _set(self, v):
        v = max(self.lo, min(self.hi, int(round(v / float(self.step)) * self.step)))
        if v != self.value or not self.active:
            self.value = v
            self.active = True
            self.draw()
            if self.command:
                self.command()

    def _press(self, ev):
        self._y0, self._v0 = ev.y, self.value

    def _drag(self, ev):
        self._set(self._v0 + (self._y0 - ev.y) * (self.hi - self.lo) / 160.0)

    def _wheel(self, ev):
        self._set(self.value + (self.step if ev.delta > 0 else -self.step) * max(1, (self.hi - self.lo) // (self.step * 50)))
        return "break"

    def _toggle(self, _ev):
        if self.optional:
            self.active = not self.active
            self.draw()
            if self.command:
                self.command()

    def get(self):
        return self.value if self.active else None

    def set(self, v):
        if v is None:
            self.active = not self.optional
        else:
            self.value = max(self.lo, min(self.hi, int(v)))
            self.active = True
        self.draw()


class PillButton(tk.Canvas):
    def __init__(self, master, text, command, primary=False, height=36, width=None, bg=BG):
        w = width or font("btn").measure(text) + 40
        super().__init__(master, width=w, height=height + 6, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.text, self.command, self.primary, self.h = text, command, primary, height
        self.hover = self.down = False
        self.enabled = True
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Enter>", lambda e: self._st(hover=True))
        self.bind("<Leave>", lambda e: self._st(hover=False, down=False))
        self.bind("<ButtonPress-1>", lambda e: self._st(down=True))
        self.bind("<ButtonRelease-1>", self._release)
        self.draw()

    def _st(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        self.draw()

    def _release(self, ev):
        was = self.down
        self._st(down=False)
        if was and self.enabled and 0 <= ev.x < self.winfo_width() and 0 <= ev.y < self.winfo_height():
            self.command()

    def set_enabled(self, on):
        self.enabled = on
        self.configure(cursor="hand2" if on else "arrow")
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        if w <= 1:
            w = int(self.cget("width"))
        h = self.h
        d = 1 if self.down else 0
        if not self.down:
            rrect(self, 3, 4, w - 1, h + 3, h / 2.0, fill=PANEL_LO, outline="")
            rrect(self, 1, 0, w - 4, h - 2, h / 2.0, fill=PANEL_HI, outline="")
        if self.primary:
            body = ACCENT_HI if self.hover else ACCENT
        else:
            body = "#2b3044" if self.hover else RAISED
        if not self.enabled:
            body = "#2a2d3a"
        rrect(self, 2 + d, 1 + d, w - 3 + d, h - 1 + d, h / 2.0 - 1, fill=body, outline="")
        fg = "#ffffff" if self.primary else TEXT
        if not self.enabled:
            fg = MUTED
        self.create_text(w / 2.0 + d, h / 2.0 + d, text=self.text, font=font("btn"), fill=fg)


class ColorChip(tk.Canvas):
    def __init__(self, master, color, command, bg=PANEL):
        super().__init__(master, width=64, height=28, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.color, self.command = color, command
        self.bind("<Button-1>", lambda e: self.command())
        self.draw()

    def draw(self):
        self.delete("all")
        rrect(self, 0, 0, 64, 28, 14, fill=TRACK, outline=PANEL_LO)
        self.create_oval(5, 5, 23, 23, fill=self.color, outline=LINE)
        self.create_text(42, 14, text="Elegir", font=font("sm"), fill=TEXT)

    def set(self, color):
        self.color = color
        self.draw()


class Panel(tk.Canvas):
    """Módulo con relieve suave, título y tornillos (como el panel de la imagen)."""
    PADX, TOP = 30, 40

    def __init__(self, master, title, note=None):
        super().__init__(master, bg=BG, highlightthickness=0, bd=0, height=80)
        self.title = title
        self.body = tk.Frame(self, bg=PANEL)
        self.body.columnconfigure(0, weight=1)
        self.win = self.create_window(self.PADX, self.TOP, window=self.body, anchor="nw")
        self.nrow = 0
        self.body.bind("<Configure>", self._layout)
        self.bind("<Configure>", self._layout)
        if note:
            self.note(note)

    def _layout(self, _ev=None):
        w = self.winfo_width()
        if w < 50:
            return
        self.itemconfigure(self.win, width=w - self.PADX - 22)
        H = self.TOP + self.body.winfo_reqheight() + 22
        if int(float(self.cget("height"))) != H:
            self.configure(height=H)
        self.delete("bg")
        rrect(self, 7, 7, w - 3, H - 4, 18, fill=PANEL_LO, outline="", tags="bg")
        rrect(self, 2, 2, w - 9, H - 10, 18, fill=PANEL_HI, outline="", tags="bg")
        rrect(self, 4, 4, w - 7, H - 8, 18, fill=PANEL, outline="", tags="bg")
        self.create_text(self.PADX, 23, text=self.title, anchor="w", font=font("title"), fill=TEXT, tags="bg")
        for y in (23, H - 26):
            self.create_oval(10, y - 5, 20, y + 5, fill="#262a3a", outline=PANEL_LO, tags="bg")
            self.create_oval(13, y - 2, 17, y + 2, fill=PANEL_LO, outline="", tags="bg")
        self.tag_lower("bg")

    def row(self, label, widget):
        tk.Label(self.body, text=label, bg=PANEL, fg=TEXT, font=font("md"), anchor="w").grid(
            row=self.nrow, column=0, sticky="w", pady=5)
        widget.grid(row=self.nrow, column=1, sticky="e", pady=5)
        self.nrow += 1
        return widget

    def full(self, widget, pady=5):
        widget.grid(row=self.nrow, column=0, columnspan=2, sticky="ew", pady=pady)
        self.nrow += 1
        return widget

    def note(self, text):
        lab = tk.Label(self.body, text=text, bg=PANEL, fg=MUTED, font=font("sm"), justify="left", anchor="w", wraplength=400)
        lab.bind("<Configure>", lambda e: lab.configure(wraplength=max(200, e.width - 4)))
        return self.full(lab, pady=(2, 4))


class ScrollArea(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG)
        self.cv = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0, yscrollincrement=24)
        self.bar = tk.Canvas(self, width=6, bg=BG, highlightthickness=0, bd=0)
        self.inner = tk.Frame(self.cv, bg=BG)
        self.win = self.cv.create_window(0, 0, window=self.inner, anchor="nw")
        self.bar.pack(side="right", fill="y", padx=(2, 0))
        self.cv.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", self._inner)
        self.cv.bind("<Configure>", self._outer)
        self.cv.configure(yscrollcommand=lambda *a: self._bar())

    def _inner(self, ev):
        self.cv.configure(scrollregion=(0, 0, ev.width, ev.height))
        self._bar()

    def _outer(self, ev):
        self.cv.itemconfigure(self.win, width=ev.width)
        self._bar()

    def wheel(self, delta):
        if self.inner.winfo_reqheight() > self.cv.winfo_height():
            self.cv.yview_scroll(-1 if delta > 0 else 1, "units")

    def _bar(self):
        self.bar.delete("all")
        a, b = self.cv.yview()
        if b - a >= 0.999:
            return
        h = self.bar.winfo_height()
        rrect(self.bar, 0, a * h, 6, b * h, 3, fill=LINE, outline="")


class AskDialog(tk.Toplevel):
    def __init__(self, master, title, prompt, initial=""):
        super().__init__(master)
        self.result = None
        self.title(title)
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(master)
        tk.Label(self, text=prompt, bg=PANEL, fg=TEXT, font=font("md")).pack(anchor="w", padx=18, pady=(16, 6))
        self.var = tk.StringVar(value=initial)
        ent = tk.Entry(self, textvariable=self.var, width=36, bg=TRACK, fg=TEXT, insertbackground=TEXT,
                       relief="flat", font=font("md"), highlightthickness=1, highlightbackground=LINE,
                       highlightcolor=ACCENT)
        ent.pack(padx=18, ipady=5, fill="x")
        bar = tk.Frame(self, bg=PANEL)
        bar.pack(fill="x", padx=14, pady=14)
        PillButton(bar, "Aceptar", self._ok, primary=True, height=32, bg=PANEL).pack(side="right", padx=4)
        PillButton(bar, "Cancelar", self.destroy, height=32, bg=PANEL).pack(side="right", padx=4)
        ent.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        dark_titlebar(self)
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 3
        self.geometry("+%d+%d" % (x, y))
        ent.focus_set()
        ent.select_range(0, "end")
        self.grab_set()
        self.wait_window()

    def _ok(self):
        self.result = self.var.get()
        self.destroy()


def ask(master, title, prompt, initial=""):
    return AskDialog(master, title, prompt, initial).result


def dark_titlebar(win):
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        val = ctypes.c_int(1)
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), 4) == 0:
                break
    except Exception:
        pass


class DarkDialog(tk.Toplevel):
    """Base de los diálogos oscuros: centra, oscurece la barra de título y es modal."""

    def __init__(self, title):
        master = tk._default_root
        super().__init__(master)
        self.master_win = master
        self.result = None
        self.withdraw()
        self.title(title)
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(master)
        self.bind("<Escape>", lambda e: self.destroy())

    def show(self):
        dark_titlebar(self)
        self.update_idletasks()
        m = self.master_win
        x = m.winfo_rootx() + (m.winfo_width() - self.winfo_reqwidth()) // 2
        y = m.winfo_rooty() + (m.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry("+%d+%d" % (max(0, x), max(0, y)))
        self.deiconify()
        self.grab_set()
        self.focus_set()
        self.wait_window()
        return self.result


class MessageDialog(DarkDialog):
    def __init__(self, title, text, kind="info", buttons=(("Aceptar", True),)):
        super().__init__(title)
        body = tk.Frame(self, bg=PANEL)
        body.pack(fill="both", padx=20, pady=(18, 6))
        led = tk.Canvas(body, width=14, height=14, bg=PANEL, highlightthickness=0)
        led.pack(side="left", anchor="n", pady=4)
        led.create_oval(1, 1, 13, 13, fill={"info": MINT, "error": CORAL, "ask": ACCENT}[kind], outline="")
        tk.Label(body, text=text, bg=PANEL, fg=TEXT, font=font("md"), justify="left", wraplength=380).pack(
            side="left", padx=(12, 0))
        bar = tk.Frame(self, bg=PANEL)
        bar.pack(fill="x", padx=14, pady=14)
        for i, (label, value) in enumerate(reversed(buttons)):
            PillButton(bar, label, lambda v=value: self._close(v), primary=bool(value), height=32,
                       bg=PANEL).pack(side="right", padx=4)
        self.bind("<Return>", lambda e: self._close(buttons[-1][1] if len(buttons) == 1 else buttons[0][1]))

    def _close(self, value):
        self.result = value
        self.destroy()


class messagebox:  # reemplazo oscuro de tkinter.messagebox (misma interfaz)
    @staticmethod
    def showinfo(title, text):
        MessageDialog(title, text, "info").show()

    @staticmethod
    def showerror(title, text):
        MessageDialog(title, text, "error").show()

    @staticmethod
    def askyesno(title, text):
        return bool(MessageDialog(title, text, "ask", (("Sí", True), ("No", False))).show())


def _hsv_to_hex(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#%02x%02x%02x" % (int(r * 255 + 0.5), int(g * 255 + 0.5), int(b * 255 + 0.5))


class ColorDialog(DarkDialog):
    """Selector de color oscuro: cuadro de saturación/brillo, barra de tono, paleta y HEX."""
    SW, SH, HB = 240, 160, 16
    SWATCHES = ["#12141c", "#1a1d28", "#232737", "#3a3f55", "#7d839b", "#d6daea", "#ffffff", "#000000",
                "#7b6cf6", "#988cff", "#4ef0c8", "#3ec7f2", "#0078d4", "#ff5f6d", "#ef6fd0", "#f7a14c",
                "#ffd166", "#16c60c", "#1b1240", "#2b1055", "#0d2b45", "#3a0f2e", "#5c2d91", "#6c5ce7"]

    def __init__(self, color, title):
        super().__init__(title)
        try:
            r, g, b = rgb(color or "#7b6cf6")
        except ValueError:
            r, g, b = 123, 108, 246
        self.h, self.s, self.v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        wrap = tk.Frame(self, bg=PANEL)
        wrap.pack(padx=18, pady=(16, 4))
        left = tk.Frame(wrap, bg=PANEL)
        left.pack(side="left")
        self.sv = tk.Canvas(left, width=self.SW, height=self.SH, highlightthickness=1,
                            highlightbackground=PANEL_LO, bd=0, cursor="crosshair")
        self.sv.pack()
        self.hue = tk.Canvas(left, width=self.SW, height=self.HB, highlightthickness=1,
                             highlightbackground=PANEL_LO, bd=0, cursor="hand2")
        self.hue.pack(pady=(10, 0))
        self._hue_img = tk.PhotoImage(master=self, width=self.SW, height=1)
        self._hue_img.put("{" + " ".join(_hsv_to_hex(x / float(self.SW), 1, 1) for x in range(self.SW)) + "}")
        self._hue_img = self._hue_img.zoom(1, self.HB)
        self.hue.create_image(0, 0, image=self._hue_img, anchor="nw")
        right = tk.Frame(wrap, bg=PANEL)
        right.pack(side="left", fill="y", padx=(16, 0))
        self.prev = tk.Canvas(right, width=120, height=64, bg=PANEL, highlightthickness=0)
        self.prev.pack(anchor="w")
        tk.Label(right, text="HEX", bg=PANEL, fg=MUTED, font=font("sm")).pack(anchor="w", pady=(10, 2))
        self.hexvar = tk.StringVar()
        ent = tk.Entry(right, textvariable=self.hexvar, width=10, bg=TRACK, fg=TEXT, insertbackground=TEXT,
                       relief="flat", font=font("md"), highlightthickness=1, highlightbackground=LINE,
                       highlightcolor=ACCENT)
        ent.pack(anchor="w", ipady=4)
        ent.bind("<Return>", self._from_hex)
        ent.bind("<FocusOut>", self._from_hex)
        pal = tk.Frame(self, bg=PANEL)
        pal.pack(padx=18, pady=(12, 0), anchor="w")
        for i, col in enumerate(self.SWATCHES):
            c = tk.Canvas(pal, width=22, height=22, bg=PANEL, highlightthickness=0, cursor="hand2")
            c.grid(row=i // 12, column=i % 12, padx=2, pady=2)
            c.create_oval(2, 2, 20, 20, fill=col, outline=LINE)
            c.bind("<Button-1>", lambda e, h=col: self._set_hex(h))
        bar = tk.Frame(self, bg=PANEL)
        bar.pack(fill="x", padx=14, pady=14)
        PillButton(bar, "Aceptar", self._ok, primary=True, height=32, bg=PANEL).pack(side="right", padx=4)
        PillButton(bar, "Cancelar", self.destroy, height=32, bg=PANEL).pack(side="right", padx=4)
        for ev in ("<Button-1>", "<B1-Motion>"):
            self.sv.bind(ev, self._sv_click)
            self.hue.bind(ev, self._hue_click)
        self._sv_img = None
        self._render_sv()
        self._update()

    def _render_sv(self):
        w, h = self.SW // 4, self.SH // 4  # se dibuja reducido y se amplía (rápido)
        img = tk.PhotoImage(master=self, width=w, height=h)
        rows = []
        for y in range(h):
            v = 1 - y / float(h - 1)
            rows.append("{" + " ".join(_hsv_to_hex(self.h, x / float(w - 1), v) for x in range(w)) + "}")
        img.put(" ".join(rows))
        self._sv_img = img.zoom(4, 4)
        self.sv.delete("img")
        self.sv.create_image(0, 0, image=self._sv_img, anchor="nw", tags="img")
        self.sv.tag_lower("img")

    def _update(self):
        hx = _hsv_to_hex(self.h, self.s, self.v)
        self.color = hx
        self.hexvar.set(hx.upper())
        self.sv.delete("mark")
        x, y = self.s * (self.SW - 1), (1 - self.v) * (self.SH - 1)
        self.sv.create_oval(x - 6, y - 6, x + 6, y + 6, outline="#ffffff", width=2, tags="mark")
        self.hue.delete("mark")
        hxp = self.h * (self.SW - 1)
        self.hue.create_rectangle(hxp - 3, 0, hxp + 3, self.HB + 1, outline="#ffffff", width=2, tags="mark")
        self.prev.delete("all")
        rrect(self.prev, 0, 0, 120, 64, 14, fill=hx, outline=LINE)

    def _sv_click(self, ev):
        self.s = min(1.0, max(0.0, ev.x / float(self.SW - 1)))
        self.v = min(1.0, max(0.0, 1 - ev.y / float(self.SH - 1)))
        self._update()

    def _hue_click(self, ev):
        self.h = min(0.999, max(0.0, ev.x / float(self.SW - 1)))
        self._render_sv()
        self._update()

    def _set_hex(self, hx):
        try:
            r, g, b = rgb(hx)
        except ValueError:
            return
        self.h, self.s, self.v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        self._render_sv()
        self._update()

    def _from_hex(self, _ev=None):
        t = self.hexvar.get().strip().lstrip("#")
        if len(t) == 6 and all(ch in "0123456789abcdefABCDEF" for ch in t):
            if ("#" + t).lower() != self.color.lower():
                self._set_hex("#" + t)
        else:
            self.hexvar.set(self.color.upper())

    def _ok(self):
        self._from_hex()
        self.result = self.color
        self.destroy()


class colorchooser:  # reemplazo oscuro de tkinter.colorchooser (misma interfaz)
    @staticmethod
    def askcolor(color=None, title="Color"):
        hx = ColorDialog(color, title).show()
        return (rgb(hx), hx) if hx else (None, None)


# ----------------------------------------------------------------- aplicación
class App:
    def __init__(self, root):
        self.root = root
        root.title("WinStyler · Barra de tareas, Inicio y Explorador")
        root.configure(bg=BG)
        root.geometry("1350x860")
        root.minsize(1280, 760)
        try:
            root.iconbitmap(default=resource("assets", "winstyler.ico"))
        except tk.TclError:
            pass
        self.ctrl = {}
        self.folders = []
        self.accent = "#0078D4"
        self.tint = "#14161F"
        self.tint2 = "#7B6CF6"
        self.sm_tint = "#14161F"
        self.sm_tint2 = "#7B6CF6"
        self.style = "11" if is_win11() else "10"
        self.show_start = False
        self.busy = False
        self.areas = []
        self._build()
        dark_titlebar(root)
        root.bind_all("<MouseWheel>", self._wheel)
        self.refresh()

    # ---------------- interfaz
    def _build(self):
        root = self.root
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)
        left = tk.Frame(root, bg=BG, width=530)
        left.grid(row=0, column=0, sticky="nsew", padx=(18, 8), pady=14)
        left.grid_propagate(False)
        left.pack_propagate(False)
        right = tk.Frame(root, bg=BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 18), pady=14)

        head = tk.Frame(left, bg=BG)
        head.pack(fill="x", pady=(0, 10))
        try:  # el mismo dibujo que el icono del .exe
            self.logo_img = tk.PhotoImage(file=resource("assets", "logo.png"))
            tk.Label(head, image=self.logo_img, bg=BG, bd=0).pack(side="left")
        except tk.TclError:
            pass
        tt = tk.Frame(head, bg=BG)
        tt.pack(side="left", padx=12)
        tk.Label(tt, text="WinStyler", bg=BG, fg=TEXT, font=font("brand")).pack(anchor="w")
        tk.Label(tt, text="Control de barra de tareas, menú Inicio y Explorador", bg=BG, fg=MUTED,
                 font=font("sm")).pack(anchor="w")

        tabs = [("tb", "Barra"), ("fx", "Efectos"), ("st", "Inicio"), ("ex", "Explorador"), ("fd", "Carpetas")]
        self.tabbar = Segmented(left, tabs, command=self._show_tab, bg=BG)
        self.tabbar.pack(anchor="w", pady=(0, 10))
        self.stack = tk.Frame(left, bg=BG)
        self.stack.pack(fill="both", expand=True)
        self.pages = {}
        for code, _ in tabs:
            area = ScrollArea(self.stack)
            self.pages[code] = area
            self.areas.append(area)
        self._page_tb(self.pages["tb"].inner)
        self._page_fx(self.pages["fx"].inner)
        self._page_st(self.pages["st"].inner)
        self._page_ex(self.pages["ex"].inner)
        self._page_fd(self.pages["fd"].inner)
        self._show_tab()

        pre = tk.Frame(left, bg=BG)
        pre.pack(fill="x", pady=(10, 0))
        tk.Label(pre, text="Preajustes", bg=BG, fg=MUTED, font=font("sm")).pack(side="left", padx=(2, 8))
        for txt, cmd in (("Limpio", lambda: self.preset(CLEAN)), ("Flotante", lambda: self.preset(FLOAT)),
                         ("Rendimiento", lambda: self.preset(PERF)), ("Restablecer", self.reset)):
            PillButton(pre, txt, cmd, height=30).pack(side="left", padx=3)

        act = tk.Frame(left, bg=BG)
        act.pack(fill="x", pady=(8, 0))
        act.columnconfigure(0, weight=1, uniform="a")
        act.columnconfigure(1, weight=1, uniform="a")
        PillButton(act, "Guardar perfil", self.save_profile_dialog).grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        PillButton(act, "Cargar perfil", self.load_profile_dialog).grid(row=0, column=1, sticky="ew", padx=3, pady=3)
        self.btn_bat = PillButton(act, "Guardar .bat", lambda: self.generate(False))
        self.btn_bat.grid(row=1, column=0, sticky="ew", padx=3, pady=3)
        self.btn_restore = PillButton(act, "Restaurar original", self.restore)
        self.btn_restore.grid(row=1, column=1, sticky="ew", padx=3, pady=3)
        self.btn_apply = PillButton(act, "Generar y aplicar", lambda: self.generate(True), primary=True, height=42)
        self.btn_apply.grid(row=2, column=0, columnspan=2, sticky="ew", padx=3, pady=(6, 0))

        # ----- vista previa
        top = tk.Frame(right, bg=BG)
        top.pack(fill="x", pady=(6, 10))
        tk.Label(top, text="Vista previa", bg=BG, fg=TEXT, font=font("title")).pack(side="left")
        self.seg_style = Segmented(top, [("11", "Windows 11"), ("10", "Windows 10")], command=self._style, bg=BG)
        self.seg_style.set(self.style)
        self.seg_style.pack(side="left", padx=16)
        tk.Label(top, text="Menú Inicio", bg=BG, fg=MUTED, font=font("sm")).pack(side="left", padx=(8, 6))
        self.tg_start = Toggle(top, False, command=self._start_toggle, bg=BG)
        self.tg_start.pack(side="left")

        bz = tk.Canvas(right, width=PW + 36, height=PH + 62, bg=BG, highlightthickness=0)
        bz.pack(anchor="w")
        rrect(bz, 6, 8, PW + 36, PH + 62, 20, fill=PANEL_LO, outline="")
        rrect(bz, 0, 0, PW + 30, PH + 54, 20, fill=PANEL_HI, outline="")
        rrect(bz, 2, 2, PW + 30, PH + 54, 20, fill=PANEL, outline="")
        rrect(bz, 10, 10, PW + 22, PH + 46, 14, fill=SCREEN, outline="#000000")
        self.bz_title = bz.create_text(26, 26, text="", anchor="w", fill="#aab0cc", font=font("sm"))
        bz.create_oval(PW + 2, 22, PW + 10, 30, fill=MINT, outline="")
        self.bezel = bz
        self.canvas = tk.Canvas(bz, width=PW, height=PH, highlightthickness=0, bd=0, bg=SCREEN)
        bz.create_window(16, 38, window=self.canvas, anchor="nw")

        info = tk.Label(right, bg=BG, fg=MUTED, font=font("sm"), justify="left", wraplength=PW + 20, anchor="w",
                        text="Vista previa aproximada. «Generar y aplicar» crea un .bat temporal, lo ejecuta y lo borra "
                             "al terminar: no queda nada en el escritorio ni junto al programa. Antes de cambiar algo se "
                             "guarda una copia de los valores originales; «Restaurar original» los devuelve y elimina "
                             "también esa copia y el módulo del efecto de barra.")
        info.pack(anchor="w", pady=(12, 6))
        st = tk.Frame(right, bg=BG)
        st.pack(anchor="w", pady=(4, 0))
        self.led = tk.Canvas(st, width=12, height=12, bg=BG, highlightthickness=0)
        self.led.pack(side="left", padx=(2, 8))
        self.status = tk.Label(st, text="", bg=BG, fg=TEXT, font=font("sm"))
        self.status.pack(side="left")
        self.set_status("Listo", MINT)

    def _choice(self, panel, key):
        label, opts = CHOICES[key]
        cmd = (lambda k=key: self._effect_changed(k)) if key in ("tb_effect", "sm_effect") else self.refresh
        if Segmented.fits(opts):
            w = Segmented(panel.body, opts, command=cmd)
        else:
            w = Dropdown(panel.body, opts, command=cmd)
        self.ctrl[key] = w
        return panel.row(label, w)

    def _panels(self, parent, spec):
        for title, keys in spec:
            p = Panel(parent, title)
            p.pack(fill="x", pady=(0, 12))
            for k in keys:
                self._choice(p, k)

    def _page_tb(self, f):
        self._panels(f, [
            ("Disposición", ["tb_align", "tb_size", "tb_small_icons", "tb_combine", "tb_autohide",
                             "tb_multimon", "tb_mmmode"]),
            ("Botones", ["tb_search", "tb_taskview", "tb_widgets", "tb_chat", "tb_copilot", "tb_news", "tb_sd"]),
            ("Comportamiento", ["tb_seconds", "tb_badges", "tb_flash", "tb_endtask", "tb_peek",
                                "tb_lastactive", "tb_tray_all", "tb_animations"]),
        ])
        p = Panel(f, "Tiempos")
        p.pack(fill="x", pady=(0, 12))
        row = tk.Frame(p.body, bg=PANEL)
        self.kn_hover = Knob(row, "Miniaturas", 0, 2000, 400, "{} ms", step=50, optional=True, active=False,
                             command=self.refresh)
        self.kn_hover.pack(side="left", padx=(0, 18))
        self.kn_menu = Knob(row, "Menús", 0, 1000, 400, "{} ms", step=25, optional=True, active=False,
                            command=self.refresh)
        self.kn_menu.pack(side="left")
        p.full(row)
        p.note("Retraso al pasar el ratón por un botón de la barra (miniaturas) y al abrir submenús. "
               "Doble clic en una perilla para activarla o dejarla sin cambio.")
        self._legend(f)

    def _page_fx(self, f):
        p = Panel(f, "Fondo de la barra")
        p.pack(fill="x", pady=(0, 12))
        self._choice(p, "tb_effect")
        row = tk.Frame(p.body, bg=PANEL)
        self.kn_opacity = Knob(row, "Opacidad", 0, 100, 40, "{} %", step=1, command=self.refresh)
        self.kn_opacity.pack(side="left", padx=(0, 22))
        side = tk.Frame(row, bg=PANEL)
        side.pack(side="left", fill="y", pady=8)
        l1 = tk.Frame(side, bg=PANEL)
        l1.pack(anchor="w", pady=4)
        self.tg_tint = Toggle(l1, False, command=self.refresh)
        self.tg_tint.pack(side="left")
        tk.Label(l1, text="Teñir con color propio", bg=PANEL, fg=TEXT, font=font("md")).pack(side="left", padx=10)
        l2 = tk.Frame(side, bg=PANEL)
        l2.pack(anchor="w", pady=4)
        self.chip_tint = ColorChip(l2, self.tint, self.pick_tint)
        self.chip_tint.pack(side="left")
        self.chip_tint2 = ColorChip(l2, self.tint2, self.pick_tint2)
        self.chip_tint2.pack(side="left", padx=(8, 0))
        tk.Label(l2, text="Color 1 / 2 (degradado)", bg=PANEL, fg=MUTED, font=font("sm")).pack(side="left", padx=10)
        p.full(row)
        self._choice(p, "tb_stroke")
        p.note("«Transparente» deja solo los íconos flotando sobre el fondo. La opacidad vale para «Translúcida», "
               "«Color sólido» y «Degradado». "
               "Esto lo hace un módulo pequeño (wstb.dll) que se guarda en %LOCALAPPDATA%\\WinStyler y se carga una vez al iniciar sesión dentro del Explorador, sin procesos en segundo plano. "
               "«Predeterminado de Windows» o «Restaurar original» lo quitan.")

        p = Panel(f, "Tema y color")
        p.pack(fill="x", pady=(0, 12))
        for k in ("tb_theme", "apps_theme", "tb_color_on", "border_color_on", "transparency"):
            self._choice(p, k)
        self.chip_accent = p.row("Color de acento", ColorChip(p.body, self.accent, self.pick_color))
        p.note("El acento solo se aplica si activas «Acento en barra e Inicio» o «Acento en bordes». "
               "Windows lo muestra en la barra únicamente con tema oscuro (se fuerza).")

        p = Panel(f, "Animaciones")
        p.pack(fill="x", pady=(0, 12))
        self._choice(p, "min_anim")
        self._legend(f)

    def _page_st(self, f):
        p = Panel(f, "Apariencia del menú [11]")
        p.pack(fill="x", pady=(0, 12))
        self._choice(p, "sm_effect")
        row = tk.Frame(p.body, bg=PANEL)
        self.kn_sm_opacity = Knob(row, "Opacidad", 0, 100, 60, "{} %", command=self.refresh, size=62)
        self.kn_sm_corner = Knob(row, "Esquinas", 0, 32, 8, "{} px", optional=True, active=False,
                                 command=self.refresh, size=62)
        self.kn_sm_scale = Knob(row, "Tamaño", 50, 100, 85, "{} %", step=1, optional=True, active=False,
                                command=self.refresh, size=62)
        self.kn_sm_height = Knob(row, "Alto", 360, 900, 726, "{} px", step=10, optional=True, active=False,
                                 command=self.refresh, size=62)
        for k in (self.kn_sm_opacity, self.kn_sm_corner, self.kn_sm_scale, self.kn_sm_height):
            k.pack(side="left", padx=(0, 2))
        p.full(row)
        l1 = tk.Frame(p.body, bg=PANEL)
        self.tg_sm_tint = Toggle(l1, False, command=self.refresh)
        self.tg_sm_tint.pack(side="left")
        tk.Label(l1, text="Teñir", bg=PANEL, fg=TEXT, font=font("md")).pack(side="left", padx=(8, 14))
        self.chip_sm_tint = ColorChip(l1, self.sm_tint, self.pick_sm_tint)
        self.chip_sm_tint.pack(side="left")
        self.chip_sm_tint2 = ColorChip(l1, self.sm_tint2, self.pick_sm_tint2)
        self.chip_sm_tint2.pack(side="left", padx=(8, 0))
        tk.Label(l1, text="Color 1 / 2", bg=PANEL, fg=MUTED, font=font("sm")).pack(side="left", padx=8)
        p.full(l1)
        for k in ("sm_shadow", "sm_border", "sm_search", "sm_rec"):
            self._choice(p, k)
        p.full(self._btnrow(p.body, [("Modo compacto", lambda: self.preset(COMPACT))]))
        p.note("Lo aplica el mismo módulo del efecto de barra (Windows 11); se ve la próxima vez que abras el menú. "
               "La opacidad vale para «Translúcido», «Color sólido» y «Degradado». «Tamaño» comprime todo el menú (sin recortar) y «Alto» lo "
               "acorta; ninguno puede agrandarlo porque Windows no deja que su ventana crezca. El panel de búsqueda "
               "es otra aplicación de Windows (SearchHost) y no se puede teñir. Doble clic en una perilla con LED para activarla o dejarla sin cambio.")

        p = Panel(f, "Menú Inicio")
        p.pack(fill="x", pady=(0, 12))
        for k in ("st_hide_rec", "st_layout", "st_suggestions", "st_most_used", "st_account_notif",
                  "st_web_search", "st_search_highlights"):
            self._choice(p, k)
        self.tg_force = p.row("Forzar ocultar «Recomendado» (admin) [11]", Toggle(p.body, False, command=self.refresh))
        self._legend(f)

    def _page_ex(self, f):
        self._panels(f, [
            ("Explorador de archivos", ["ex_ext", "ex_hidden", "ex_launch", "ex_compact", "ex_checkbox",
                                        "ex_recent", "ex_classic"]),
        ])
        self._legend(f)

    def _listbox(self, parent, h):
        return tk.Listbox(parent, height=h, exportselection=False, bg=TRACK, fg=TEXT, font=font("md"),
                          selectbackground=ACCENT, selectforeground="#ffffff", relief="flat", bd=0,
                          highlightthickness=1, highlightbackground=PANEL_LO, highlightcolor=ACCENT,
                          activestyle="none")

    def _btnrow(self, parent, items):
        fr = tk.Frame(parent, bg=PANEL)
        for txt, cmd in items:
            PillButton(fr, txt, cmd, height=28, bg=PANEL).pack(side="left", padx=(0, 6))
        return fr

    def _page_fd(self, f):
        p = Panel(f, "Carpetas del menú Inicio")
        p.pack(fill="x", pady=(0, 12))
        p.note("Se crean en la lista «Todas las aplicaciones», cada acceso con su propio ícono.")
        self.lb_f = p.full(self._listbox(p.body, 5))
        self.lb_f.bind("<<ListboxSelect>>", lambda e: self._fill_apps())
        p.full(self._btnrow(p.body, [("Nueva", self.f_add), ("Renombrar", self.f_rename), ("Eliminar", self.f_del)]))
        tk.Label(p.body, text="Aplicaciones de la carpeta", bg=PANEL, fg=TEXT, font=font("md")).grid(
            row=p.nrow, column=0, sticky="w", pady=(10, 0))
        p.nrow += 1
        self.lb_a = p.full(self._listbox(p.body, 8))
        p.full(self._btnrow(p.body, [("Añadir…", self.a_add), ("Nombre", self.a_rename),
                                     ("Ícono…", self.a_icon), ("Quitar", self.a_del)]))

    def _legend(self, f):
        tk.Label(f, bg=BG, fg=MUTED, font=font("sm"), justify="left", anchor="w", wraplength=480,
                 text="[10] y [11] indican la versión de Windows donde aplica cada opción; en la otra se ignora. "
                      "«—» deja el valor actual sin tocar.").pack(fill="x", padx=6, pady=(0, 10))

    def _effect_changed(self, key):
        knob = self.kn_opacity if key == "tb_effect" else self.kn_sm_opacity
        eff = self.ctrl[key].get()
        if eff == "translucent":
            knob.set(50)
        elif eff in ("solid", "gradient"):
            knob.set(100)
        self.refresh()

    def _show_tab(self):
        code = self.tabbar.get()
        for c, area in self.pages.items():
            if c == code:
                area.pack(fill="both", expand=True)
            else:
                area.pack_forget()
        if code == "st" and not self.show_start:  # en la pestaña Inicio se muestra el menú
            self.tg_start.set(True)
            self._start_toggle()

    def _wheel(self, ev):
        w = self.root.winfo_containing(ev.x_root, ev.y_root)
        while w is not None:
            for area in self.areas:
                if w is area:
                    area.wheel(ev.delta)
                    return
            w = w.master

    def _style(self):
        self.style = self.seg_style.get()
        self.refresh()

    def _start_toggle(self):
        self.show_start = self.tg_start.get()
        self.refresh()

    def set_status(self, text, color=MINT):
        self.status.configure(text=text)
        self.led.delete("all")
        self.led.create_oval(1, 1, 11, 11, fill=color, outline="")

    # ---------------- estado
    def get_cfg(self):
        cfg = dict(gen.DEFAULTS)
        for k, w in self.ctrl.items():
            cfg[k] = w.get()
        cfg["accent_color"] = self.accent
        cfg["st_force_rec"] = bool(self.tg_force.get())
        cfg["folders"] = json.loads(json.dumps(self.folders))
        cfg["tb_opacity"] = self.kn_opacity.get()
        cfg["tb_tint_on"] = bool(self.tg_tint.get())
        cfg["tb_tint"] = self.tint
        cfg["tb_tint2"] = self.tint2
        cfg["sm_opacity"] = self.kn_sm_opacity.get()
        cfg["sm_tint_on"] = bool(self.tg_sm_tint.get())
        cfg["sm_tint"] = self.sm_tint
        cfg["sm_tint2"] = self.sm_tint2
        cfg["sm_corner"] = self.kn_sm_corner.get()
        cfg["sm_scale"] = self.kn_sm_scale.get()
        cfg["sm_height"] = self.kn_sm_height.get()
        cfg["tb_hover_ms"] = self.kn_hover.get()
        cfg["menu_delay"] = self.kn_menu.get()
        return cfg

    def set_cfg(self, cfg):
        for k, w in self.ctrl.items():
            w.set(cfg.get(k, "keep"))
        self.accent = cfg.get("accent_color", "#0078D4")
        self.chip_accent.set(self.accent)
        self.tint = cfg.get("tb_tint") or "#14161F"
        self.chip_tint.set(self.tint)
        self.tg_tint.set(cfg.get("tb_tint_on", False))
        self.kn_opacity.set(cfg.get("tb_opacity", 40))
        self.tint2 = cfg.get("tb_tint2") or "#7B6CF6"
        self.chip_tint2.set(self.tint2)
        self.sm_tint = cfg.get("sm_tint") or "#14161F"
        self.chip_sm_tint.set(self.sm_tint)
        self.sm_tint2 = cfg.get("sm_tint2") or "#7B6CF6"
        self.chip_sm_tint2.set(self.sm_tint2)
        self.tg_sm_tint.set(cfg.get("sm_tint_on", False))
        self.kn_sm_opacity.set(cfg.get("sm_opacity", 60))
        self.kn_sm_corner.set(cfg.get("sm_corner"))
        self.kn_sm_scale.set(cfg.get("sm_scale"))
        self.kn_sm_height.set(cfg.get("sm_height"))
        self.kn_hover.set(cfg.get("tb_hover_ms"))
        self.kn_menu.set(cfg.get("menu_delay"))
        self.tg_force.set(bool(cfg.get("st_force_rec", False)))
        self.folders = list(cfg.get("folders") or [])
        self._fill_folders()

    def refresh(self):
        self.bezel.itemconfigure(self.bz_title, text="Vista previa · Windows %s" % self.style)
        try:
            paint(self.canvas, self.get_cfg(), self.style, self.show_start)
        except Exception as ex:  # la vista previa nunca debe romper la app
            print("preview:", ex)

    def pick_color(self):
        res = colorchooser.askcolor(color=self.accent, title="Color de acento")
        if res and res[1]:
            self.accent = res[1]
            self.chip_accent.set(res[1])
            self.refresh()

    def pick_tint(self):
        res = colorchooser.askcolor(color=self.tint, title="Color de la barra")
        if res and res[1]:
            self.tint = res[1]
            self.chip_tint.set(res[1])
            if self.ctrl["tb_effect"].get() == "translucent":
                self.tg_tint.set(True)
            self.refresh()

    def _pick(self, attr, chip, title):
        res = colorchooser.askcolor(color=getattr(self, attr), title=title)
        if res and res[1]:
            setattr(self, attr, res[1])
            chip.set(res[1])
            self.refresh()
            return True
        return False

    def pick_tint2(self):
        self._pick("tint2", self.chip_tint2, "Segundo color de la barra (degradado)")

    def pick_sm_tint(self):
        if self._pick("sm_tint", self.chip_sm_tint, "Color del menú Inicio") and \
                self.ctrl["sm_effect"].get() == "translucent":
            self.tg_sm_tint.set(True)
            self.refresh()

    def pick_sm_tint2(self):
        self._pick("sm_tint2", self.chip_sm_tint2, "Segundo color del menú (degradado)")

    # ---------------- presets / perfil
    def preset(self, values):
        cfg = self.get_cfg()
        cfg.update(values)
        self.set_cfg(cfg)
        self.refresh()

    def reset(self):
        if self.folders and not messagebox.askyesno("Restablecer", "¿Borrar también las carpetas definidas?"):
            keep = self.folders
        else:
            keep = []
        cfg = dict(gen.DEFAULTS)
        cfg["folders"] = keep
        self.set_cfg(cfg)
        self.refresh()

    def save_profile(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_cfg(), f, ensure_ascii=False, indent=2)

    def load_profile(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.set_cfg(json.load(f))
        except Exception as ex:
            messagebox.showerror("Perfil", "No se pudo cargar el perfil:\n%s" % ex)

    def save_profile_dialog(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", initialfile="winstyler_perfil.json",
                                         filetypes=[("Perfil", "*.json")])
        if p:
            self.save_profile(p)

    def load_profile_dialog(self):
        p = filedialog.askopenfilename(filetypes=[("Perfil", "*.json")])
        if p:
            self.load_profile(p)
            self.refresh()

    # ---------------- carpetas
    def _sel_f(self):
        s = self.lb_f.curselection()
        return s[0] if s else None

    def _sel_a(self):
        s = self.lb_a.curselection()
        return s[0] if s else None

    def _fill_folders(self, select=None):
        self.lb_f.delete(0, "end")
        for f in self.folders:
            self.lb_f.insert("end", f["name"])
        if select is not None and self.folders:
            self.lb_f.selection_set(min(select, len(self.folders) - 1))
        self._fill_apps()

    def _fill_apps(self):
        self.lb_a.delete(0, "end")
        i = self._sel_f()
        if i is None or i >= len(self.folders):
            return
        for a in self.folders[i]["apps"]:
            self.lb_a.insert("end", a["name"] + ("  [ícono]" if a.get("icon") else ""))

    def f_add(self):
        n = ask(self.root, "Nueva carpeta", "Nombre de la carpeta:")
        if n and n.strip():
            self.folders.append({"name": n.strip(), "apps": []})
            self._fill_folders(len(self.folders) - 1)
            self.refresh()

    def f_rename(self):
        i = self._sel_f()
        if i is None:
            return
        n = ask(self.root, "Renombrar", "Nuevo nombre:", self.folders[i]["name"])
        if n and n.strip():
            self.folders[i]["name"] = n.strip()
            self._fill_folders(i)
            self.refresh()

    def f_del(self):
        i = self._sel_f()
        if i is None:
            return
        del self.folders[i]
        self._fill_folders(i)
        self.refresh()

    def a_add(self):
        i = self._sel_f()
        if i is None:
            messagebox.showinfo("Carpetas", "Primero crea o selecciona una carpeta.")
            return
        files = filedialog.askopenfilenames(title="Elegir aplicaciones",
                                            filetypes=[("Programas y accesos", "*.exe *.lnk *.bat *.cmd"), ("Todos", "*.*")])
        for p in files:
            name = os.path.splitext(os.path.basename(p))[0]
            self.folders[i]["apps"].append({"name": name, "path": p, "icon": ""})
        self._fill_folders(i)
        self.refresh()

    def a_rename(self):
        i, j = self._sel_f(), self._sel_a()
        if i is None or j is None:
            return
        a = self.folders[i]["apps"][j]
        n = ask(self.root, "Nombre", "Nombre del acceso:", a["name"])
        if n and n.strip():
            a["name"] = n.strip()
            self._fill_folders(i)
            self.lb_a.selection_set(j)

    def a_icon(self):
        i, j = self._sel_f(), self._sel_a()
        if i is None or j is None:
            return
        a = self.folders[i]["apps"][j]
        p = filedialog.askopenfilename(title="Elegir ícono (cancelar = ícono por defecto)",
                                       filetypes=[("Íconos", "*.ico *.exe *.dll"), ("Todos", "*.*")])
        a["icon"] = p or ""
        self._fill_folders(i)
        self.lb_a.selection_set(j)

    def a_del(self):
        i, j = self._sel_f(), self._sel_a()
        if i is None or j is None:
            return
        del self.folders[i]["apps"][j]
        self._fill_folders(i)
        self.refresh()

    # ---------------- generación
    @staticmethod
    def _dll_b64():
        with open(resource("native", "wstb.dll"), "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")

    def generate(self, run):
        if self.busy:
            return
        cfg = self.get_cfg()
        if not gen.has_changes(cfg):
            messagebox.showinfo("WinStyler", "No hay cambios seleccionados.")
            return
        try:
            text = gen.build_apply_bat(cfg, self._dll_b64() if gen.needs_dll(cfg) else None)
        except (OSError, ValueError) as ex:
            messagebox.showerror("WinStyler", "No se pudo preparar el estilo:\n%s" % ex)
            return
        if run:
            self._run_temp(text, "Aplicando estilo…", "Estilo aplicado · archivos temporales eliminados")
            return
        d = filedialog.askdirectory(title="Carpeta donde guardar aplicar_estilo.bat y restaurar_original.bat")
        if not d:
            return
        try:
            for name, body in (("aplicar_estilo.bat", text), ("restaurar_original.bat", gen.build_restore_bat())):
                with open(os.path.join(d, name), "w", encoding="utf-8", newline="") as f:
                    f.write(body)
        except OSError as ex:
            messagebox.showerror("WinStyler", "No se pudo guardar:\n%s" % ex)
            return
        self.set_status("Archivos .bat guardados en %s" % d, MINT)

    def restore(self):
        if self.busy:
            return
        if not messagebox.askyesno("Restaurar original",
                                   "Se devolverán los valores que había antes de usar WinStyler, se quitará el "
                                   "efecto de barra y del menú Inicio y se borrará todo lo que WinStyler guardó.\n\n¿Continuar?"):
            return
        self._run_temp(gen.build_restore_bat(), "Restaurando…", "Valores originales restaurados · sin rastros")

    def _set_busy(self, on):
        self.busy = on
        for b in (self.btn_apply, self.btn_restore, self.btn_bat):
            b.set_enabled(not on)

    def _run_temp(self, text, busy_msg, done_msg):
        try:
            fd, path = tempfile.mkstemp(prefix="ws_", suffix=".bat")
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                f.write(text)
        except OSError as ex:
            messagebox.showerror("WinStyler", "No se pudo crear el archivo temporal:\n%s" % ex)
            return
        self._set_busy(True)
        self.set_status(busy_msg, ACCENT)

        def work():
            err = None
            try:
                p = subprocess.Popen(["cmd.exe", "/d", "/c", path], creationflags=0x08000000,
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, close_fds=True)
                p.wait()
            except OSError as ex:
                err = ex
            for _ in range(30):  # el .bat temporal no debe quedar en el disco
                try:
                    os.remove(path)
                    break
                except FileNotFoundError:
                    break
                except OSError:
                    time.sleep(0.3)
            left = os.path.exists(path)
            self.root.after(0, lambda: self._done(err, left, done_msg))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, err, left, done_msg):
        self._set_busy(False)
        if err:
            self.set_status("Error al ejecutar", CORAL)
            messagebox.showerror("WinStyler", "No se pudo ejecutar:\n%s" % err)
        elif left:
            self.set_status("Aplicado, pero no se pudo borrar el archivo temporal", CORAL)
        else:
            self.set_status(done_msg, MINT)


def main():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("WinStyler.App")
    except Exception:
        pass
    root = tk.Tk()
    root.withdraw()
    App(root)
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()
