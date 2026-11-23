# -*- coding: utf-8 -*-
"""WinStyler - catálogo de mods y biblioteca de temas.

Un *mod* es un archivo JSON con metadatos, ajustes y cambios reales:
  - "rules": estilos XAML que aplica native/wstb.dll dentro del Explorador (barra, bandeja,
    Explorador de archivos) o del menú Inicio (Windows 11). Mismo formato de objetivos y
    estilos que el Windows 11 Taskbar/Start Menu Styler de Windhawk.
  - "registry": valores del registro (con copia de seguridad y restauración automáticas).
Un *tema* agrupa ajustes de WinStyler (barra, Inicio, Explorador, efectos) y una lista de mods
con su configuración. Los incluidos están en mods/ y themes/; los del usuario se guardan en
%APPDATA%\\WinStyler (mods\\ y temas\\).
"""
import os
import re
import sys
import json
import copy

SCHEMA = 1


def _resource(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def user_dir(kind=""):
    base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "WinStyler")
    return os.path.join(base, kind) if kind else base


def windows_build():
    try:
        return sys.getwindowsversion().build
    except Exception:
        return 22631


# ------------------------------------------------------------------ carga / guardado
def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_dir(folder, builtin):
    out = []
    if not os.path.isdir(folder):
        return out
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(".json"):
            continue
        p = os.path.join(folder, name)
        try:
            obj = _read_json(p)
        except (OSError, ValueError):
            continue
        if not isinstance(obj, dict) or not obj.get("id"):
            continue
        obj["_builtin"] = builtin
        obj["_path"] = p
        out.append(obj)
    return out


def _merge(builtin, user):
    by_id = {o["id"]: o for o in builtin}
    for o in user:
        by_id[o["id"]] = o
    return sorted(by_id.values(), key=lambda o: (not o.get("_builtin"), o.get("category", ""), o.get("name", "").lower()))


def load_mods():
    return _merge(_load_dir(_resource("mods"), True), _load_dir(user_dir("mods"), False))


def load_themes():
    return _merge(_load_dir(_resource("themes"), True), _load_dir(user_dir("temas"), False))


def _clean(obj):
    return {k: v for k, v in obj.items() if not k.startswith("_")}


def _safe_id(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "sin-nombre"


def save_user(kind, obj):
    """kind: 'mods' o 'temas'. Devuelve la ruta guardada."""
    folder = user_dir(kind)
    os.makedirs(folder, exist_ok=True)
    obj = _clean(obj)
    obj["id"] = obj.get("id") or _safe_id(obj.get("name"))
    obj["schema"] = SCHEMA
    path = os.path.join(folder, obj["id"] + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path


def delete_user(obj):
    p = obj.get("_path")
    if p and not obj.get("_builtin") and os.path.isfile(p):
        os.remove(p)


def export(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_clean(obj), f, ensure_ascii=False, indent=2)


def unique_id(base, existing):
    ids = {o["id"] for o in existing}
    i, cand = 2, base
    while cand in ids:
        cand = "%s-%d" % (base, i)
        i += 1
    return cand


# ------------------------------------------------------------------ compatibilidad
def compat_text(mod):
    c = mod.get("compat") or {}
    lo, hi = c.get("min_build"), c.get("max_build")
    if lo and lo >= 22000:
        txt = "Windows 11"
        if lo > 22000:
            txt += " (compilación %d o posterior)" % lo
    elif hi and hi < 22000:
        txt = "Windows 10"
    else:
        txt = "Windows 10 y 11"
    return txt


def is_compatible(mod, build=None):
    build = build or windows_build()
    c = mod.get("compat") or {}
    if c.get("min_build") and build < c["min_build"]:
        return False
    if c.get("max_build") and build > c["max_build"]:
        return False
    return True


RESTART_TEXT = {"none": "Inmediato", "explorer": "Reinicia el Explorador (automático)",
                "logoff": "Cerrar sesión", "reboot": "Reiniciar Windows"}


def requirements_text(mod):
    procs = sorted({r.get("process", "explorer") for r in mod.get("rules", [])})
    parts = []
    if procs:
        names = {"explorer": "Explorador (barra/bandeja/Explorador de archivos)", "start": "menú Inicio"}
        parts.append("Módulo wstb.dll en " + " y ".join(names.get(p, p) for p in procs) +
                     " (se carga una vez, sin proceso residente)")
    if mod.get("registry"):
        parts.append("Registro de Windows (con copia de seguridad)")
    return "; ".join(parts) or "Ninguno"


# ------------------------------------------------------------------ ajustes de un mod
def default_settings(mod):
    return {s["key"]: s.get("default") for s in mod.get("settings", []) if "key" in s}


def _fmt_num(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        s = ("%.4f" % v).rstrip("0").rstrip(".")
        return s or "0"
    return str(v)


_TOKEN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)(/100)?\}")


def substitute(text, values):
    def repl(m):
        key, pct = m.group(1), m.group(2)
        if key not in values:
            return m.group(0)
        v = values[key]
        if pct:
            try:
                return _fmt_num(float(v) / 100.0)
            except (TypeError, ValueError):
                return "0"
        return _fmt_num(v)
    return _TOKEN.sub(repl, text)


# ------------------------------------------------------------------ estilos
def _split_targets(target):
    """Divide 'A > B, C > D' en objetivos, respetando corchetes."""
    out, depth, cur = [], 0, ""
    for ch in target:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


_BLUR = re.compile(r"<WindhawkBlur\b([^>]*)/>", re.I)


def _attr(attrs, name):
    m = re.search(r'\b%s\s*=\s*"([^"]*)"' % name, attrs, re.I)
    return m.group(1) if m else None


def _blur_to_acrylic(m):
    """WindhawkBlur (pincel propio de Windhawk) -> AcrylicBrush de XAML (desenfoque real del fondo)."""
    attrs = m.group(1)
    tint = _attr(attrs, "TintColor") or "#00000000"
    t = tint.lstrip("#")
    alpha = int(t[:2], 16) if len(t) == 8 else 255
    rgb = t[2:] if len(t) == 8 else t[-6:]
    op = "%.3f" % (alpha / 255.0)
    return ('<AcrylicBrush BackgroundSource="Backdrop" TintColor="#FF%s" TintOpacity="%s" '
            'TintLuminosityOpacity="0" FallbackColor="%s"/>' % (rgb, op, tint))


def parse_style(style, constants):
    """'Prop@Estado:=<xaml>' / 'Prop=valor' -> (prop, estado, es_xaml, valor) o None si no se admite."""
    s = style.strip()
    if not s or s.startswith("//") or "{{" in s or "=>" in s:
        return None
    eq = s.find("=")
    if eq <= 0:
        return None
    xaml = s[eq - 1] == ":"
    left = s[:eq - 1 if xaml else eq].strip()
    value = s[eq + 1:].strip()
    prop, _, state = left.partition("@")
    for name in sorted(constants, key=len, reverse=True):
        value = value.replace("$" + name, constants[name])
    if value.lstrip().startswith("<"):
        xaml = True
    value = _BLUR.sub(_blur_to_acrylic, value).replace("\r", " ").replace("\n", " ").replace("\t", " ")
    if "$" in value and re.search(r"\$[A-Za-z_]", value):
        return None  # constante desconocida
    return prop.strip(), state.strip(), xaml, value


def compile_styles(cfg, mods=None, build=None):
    """Genera styles.wss para los mods activos. Devuelve (texto, procesos_usados)."""
    mods = mods if mods is not None else load_mods()
    by_id = {m["id"]: m for m in mods}
    sections = {"explorer": [], "start": []}
    for mid, state in (cfg.get("mods") or {}).items():
        mod = by_id.get(mid)
        if not mod or not state.get("enabled") or not is_compatible(mod, build):
            continue
        values = default_settings(mod)
        values.update(state.get("settings") or {})
        constants = {k: substitute(str(v), values) for k, v in (mod.get("constants") or {}).items()}
        for rule in mod.get("rules", []):
            proc = rule.get("process", "explorer")
            if proc not in sections:
                continue
            if rule.get("when") and not values.get(rule["when"]):
                continue
            styles = []
            for st in rule.get("styles", []):
                parsed = parse_style(substitute(st, values), constants)
                if parsed:
                    styles.append(parsed)
            if not styles:
                continue
            for target in _split_targets(substitute(rule.get("target", ""), values)):
                if not target or target.startswith(":root") or "{{" in target:
                    continue
                lines = sections[proc]
                lines.append("T\t" + target)
                for prop, st_state, xaml, value in styles:
                    lines.append("S\t%s\t%s\t%s\t%s" % (prop, st_state, "x" if xaml else "v", value))
    out, used = ["# WinStyler styles.wss (generado)"], set()
    for proc, lines in sections.items():
        if lines:
            used.add(proc)
            out.append("@" + proc)
            out.extend(lines)
    return ("\n".join(out) + "\n") if used else "", used


def registry_items(cfg, mods=None, build=None):
    """Valores de registro de los mods activos (formato de generador.build_items)."""
    mods = mods if mods is not None else load_mods()
    by_id = {m["id"]: m for m in mods}
    items = []
    for mid, state in (cfg.get("mods") or {}).items():
        mod = by_id.get(mid)
        if not mod or not state.get("enabled") or not is_compatible(mod, build):
            continue
        values = default_settings(mod)
        values.update(state.get("settings") or {})
        for r in mod.get("registry", []):
            if r.get("when") and not values.get(r["when"]):
                continue
            items.append({"path": r["path"], "name": r["name"], "type": r.get("type", "REG_DWORD"),
                          "data": substitute(str(r.get("data", "")), values)})
    return items


# ------------------------------------------------------------------ importar de Windhawk
_START_HINTS = ("StartDocked", "StartMenu", "AcrylicBorder", "AllAppsRoot", "PinnedList", "LauncherFrame",
                "StartSizingFrame", "UndockedRoot", "TopLevelSuggestions")


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        s = s[1:-1]
        if s.startswith("'"):
            s = s.replace("''", "'")
    return s


def parse_windhawk_text(text):
    """Lee el 'modo textual' (YAML) o JSON del Taskbar/Start Menu Styler de Windhawk."""
    text = text.strip()
    if text.startswith("{"):
        data = json.loads(text)
        consts = data.get("styleConstants") or []
        styles = data.get("controlStyles") or []
        return ([_unquote(c) for c in consts],
                [{"target": s.get("target", ""), "styles": list(s.get("styles") or [])} for s in styles])
    consts, controls, section, cur = [], [], None, None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        stripped = line.strip()
        if not raw.startswith((" ", "\t", "-")) and stripped.endswith(":"):
            section = stripped[:-1].strip()
            continue
        if section == "styleConstants" and stripped.startswith("- "):
            consts.append(_unquote(stripped[2:]))
        elif section == "controlStyles":
            if stripped.startswith("- target:"):
                cur = {"target": _unquote(stripped[len("- target:"):]), "styles": []}
                controls.append(cur)
            elif stripped.startswith("target:") and cur is not None:
                cur["target"] = _unquote(stripped[len("target:"):])
            elif stripped.startswith("- ") and cur is not None:
                cur["styles"].append(_unquote(stripped[2:]))
    return consts, controls


def windhawk_to_mod(text, name, author="", category=None):
    consts, controls = parse_windhawk_text(text)
    constants = {}
    for c in consts:
        k, _, v = c.partition("=")
        if k.strip():
            constants[k.strip()] = v.strip()
    rules, skipped = [], 0
    for ctl in controls:
        target = ctl.get("target", "")
        proc = "start" if any(h in target for h in _START_HINTS) else "explorer"
        ok = []
        for st in ctl.get("styles", []):
            if parse_style(st, constants) is None:
                skipped += 1
            else:
                ok.append(st)
        if ok and target:
            rules.append({"process": proc, "target": target, "styles": ok})
    procs = {r["process"] for r in rules}
    desc = "Importado de un tema del Windows 11 %s Styler de Windhawk." % (
        "Start Menu" if procs == {"start"} else "Taskbar")
    if skipped:
        desc += " Se omitieron %d estilos con expresiones que WinStyler no admite." % skipped
    return {
        "schema": SCHEMA, "id": _safe_id(name), "name": name, "description": desc,
        "category": category or ("Menú Inicio" if procs == {"start"} else "Barra de tareas"),
        "author": author or "Importado", "version": "1.0",
        "compat": {"min_build": 22000}, "restart": "none",
        "constants": constants, "settings": [], "rules": rules,
    }


def import_file(path):
    """Devuelve ('mod'|'tema', objeto) a partir de un JSON de WinStyler o un tema de Windhawk."""
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    name = os.path.splitext(os.path.basename(path))[0]
    try:
        obj = json.loads(text)
    except ValueError:
        obj = None
    if isinstance(obj, dict):
        if "controlStyles" in obj:
            return "mod", windhawk_to_mod(text, name)
        if obj.get("kind") == "theme" or "settings_cfg" in obj:
            obj.setdefault("id", _safe_id(obj.get("name") or name))
            return "tema", obj
        if "rules" in obj or "registry" in obj:
            obj.setdefault("id", _safe_id(obj.get("name") or name))
            return "mod", obj
        raise ValueError("El JSON no es un mod ni un tema de WinStyler.")
    if "controlStyles" in text:
        return "mod", windhawk_to_mod(text, name)
    raise ValueError("Formato no reconocido.")


def theme_cfg(theme, defaults):
    """Configuración completa de WinStyler a partir de un tema."""
    cfg = copy.deepcopy(defaults)
    cfg.update(copy.deepcopy(theme.get("settings_cfg") or {}))
    cfg["mods"] = copy.deepcopy(theme.get("mods") or {})
    return cfg
