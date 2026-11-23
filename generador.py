# -*- coding: utf-8 -*-
"""WinStyler - generador de .bat (registro de Windows 10/11)."""
import re

ADV = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
EXPL = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer"
DEVSET = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced\TaskbarDeveloperSettings"
SEARCH = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search"
SEARCHSET = r"HKCU\Software\Microsoft\Windows\CurrentVersion\SearchSettings"
PERS = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
DWM = r"HKCU\Software\Microsoft\Windows\DWM"
ACCENT = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"
FEEDS = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Feeds"
CDM = r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
POL = r"HKCU\Software\Policies\Microsoft\Windows\Explorer"
DESK = r"HKCU\Control Panel\Desktop"
WINMET = r"HKCU\Control Panel\Desktop\WindowMetrics"
STUCK = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3"
CLASSIC = r"HKCU\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}"
WSKEY = r"HKCU\Software\WinStyler"
HK_ADV = r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
HK_START = r"HKLM\SOFTWARE\Microsoft\PolicyManager\current\device\Start"
HK_EDU = r"HKLM\SOFTWARE\Microsoft\PolicyManager\current\device\Education"

CHOICE_KEYS = [
    "tb_align", "tb_size", "tb_small_icons", "tb_search", "tb_taskview",
    "tb_widgets", "tb_chat", "tb_copilot", "tb_news", "tb_combine",
    "tb_seconds", "tb_autohide", "tb_theme", "tb_color_on", "border_color_on",
    "transparency", "st_hide_rec", "st_layout", "st_suggestions",
    "st_most_used", "st_account_notif", "st_web_search", "st_search_highlights",
    # nuevas
    "tb_sd", "tb_badges", "tb_flash", "tb_endtask", "tb_multimon", "tb_mmmode",
    "tb_peek", "tb_lastactive", "tb_tray_all", "tb_animations",
    "apps_theme", "min_anim",
    "ex_ext", "ex_hidden", "ex_launch", "ex_compact", "ex_checkbox", "ex_recent", "ex_classic",
    "tb_effect", "tb_stroke",
    "sm_effect", "sm_shadow", "sm_border", "sm_search", "sm_rec",
]

DEFAULTS = {k: "keep" for k in CHOICE_KEYS}
DEFAULTS.update({"accent_color": "#0078D4", "st_force_rec": False, "folders": [],
                 "tb_opacity": 100, "tb_tint_on": False, "tb_tint": "#14161F", "tb_tint2": "#7B6CF6",
                 "sm_opacity": 100, "sm_tint_on": False, "sm_tint": "#14161F", "sm_tint2": "#7B6CF6",
                 "sm_corner": None, "sm_scale": None, "sm_height": None,
                 "tb_hover_ms": None, "menu_delay": None})

# (clave, ruta, [valores], {opcion: dato})
TABLE = [
    ("tb_align", ADV, ["TaskbarAl"], {"center": 1, "left": 0}),
    ("tb_size", ADV, ["TaskbarSi"], {"small": 0, "medium": 1, "large": 2}),
    ("tb_small_icons", ADV, ["TaskbarSmallIcons"], {"on": 1, "off": 0}),
    ("tb_search", SEARCH, ["SearchboxTaskbarMode"], {"hidden": 0, "icon": 1, "box": 2, "iconlabel": 3}),
    ("tb_taskview", ADV, ["ShowTaskViewButton"], {"show": 1, "hide": 0}),
    ("tb_widgets", ADV, ["TaskbarDa"], {"show": 1, "hide": 0}),
    ("tb_chat", ADV, ["TaskbarMn"], {"show": 1, "hide": 0}),
    ("tb_copilot", ADV, ["ShowCopilotButton"], {"show": 1, "hide": 0}),
    ("tb_news", FEEDS, ["ShellFeedsTaskbarViewMode"], {"show": 0, "hide": 2}),
    ("tb_combine", ADV, ["TaskbarGlomLevel", "MMTaskbarGlomLevel"], {"always": 0, "full": 1, "never": 2}),
    ("tb_seconds", ADV, ["ShowSecondsInSystemClock"], {"show": 1, "hide": 0}),
    ("tb_sd", ADV, ["TaskbarSd"], {"show": 1, "hide": 0}),
    ("tb_badges", ADV, ["TaskbarBadges"], {"on": 1, "off": 0}),
    ("tb_flash", ADV, ["TaskbarFlashing"], {"on": 1, "off": 0}),
    ("tb_endtask", DEVSET, ["TaskbarEndTask"], {"on": 1, "off": 0}),
    ("tb_multimon", ADV, ["MMTaskbarEnabled"], {"on": 1, "off": 0}),
    ("tb_mmmode", ADV, ["MMTaskbarMode"], {"all": 0, "main": 1, "own": 2}),
    ("tb_peek", ADV, ["DisablePreviewDesktop"], {"on": 0, "off": 1}),
    ("tb_lastactive", ADV, ["LastActiveClick"], {"on": 1, "off": 0}),
    ("tb_tray_all", EXPL, ["EnableAutoTray"], {"on": 0, "off": 1}),
    ("tb_animations", ADV, ["TaskbarAnimations"], {"on": 1, "off": 0}),
    ("apps_theme", PERS, ["AppsUseLightTheme"], {"dark": 0, "light": 1}),
    ("st_layout", ADV, ["Start_Layout"], {"default": 0, "pins": 1, "recs": 2}),
    ("st_most_used", ADV, ["Start_TrackProgs"], {"show": 1, "hide": 0}),
    ("st_account_notif", ADV, ["Start_AccountNotifications"], {"show": 1, "hide": 0}),
    ("st_web_search", SEARCH, ["BingSearchEnabled"], {"on": 1, "off": 0}),
    ("st_search_highlights", SEARCHSET, ["IsDynamicSearchBoxEnabled"], {"on": 1, "off": 0}),
    ("ex_ext", ADV, ["HideFileExt"], {"show": 0, "hide": 1}),
    ("ex_hidden", ADV, ["Hidden"], {"show": 1, "hide": 2}),
    ("ex_launch", ADV, ["LaunchTo"], {"pc": 1, "home": 2, "downloads": 3}),
    ("ex_compact", ADV, ["UseCompactMode"], {"on": 1, "off": 0}),
    ("ex_checkbox", ADV, ["AutoCheckSelect"], {"on": 1, "off": 0}),
    ("ex_recent", EXPL, ["ShowRecent", "ShowFrequent"], {"show": 1, "hide": 0}),
]

EFFECT_ON = ("transparent", "translucent", "solid", "gradient")
NO_TINT = 0xFFFFFFFF


def _rgb(h):
    h = (h or "").lstrip("#")
    if len(h) != 6:
        h = "0078D4"
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return 0, 120, 212


def _mix(c, o, t):
    return tuple(int(round(c[i] + (o[i] - c[i]) * t)) for i in range(3))


def accent_values(hexcolor):
    r, g, b = _rgb(hexcolor)
    abgr = (0xFF << 24) | (b << 16) | (g << 8) | r
    argb = (0xC4 << 24) | (r << 16) | (g << 8) | b
    base = (r, g, b)
    pal = [
        _mix(base, (255, 255, 255), 0.6), _mix(base, (255, 255, 255), 0.4),
        _mix(base, (255, 255, 255), 0.2), base,
        _mix(base, (0, 0, 0), 0.2), _mix(base, (0, 0, 0), 0.4),
        _mix(base, (0, 0, 0), 0.6),
    ]
    palhex = "".join("%02x%02x%02x%02x" % (p[0], p[1], p[2], 255) for p in pal) + "88179800"
    return {"abgr": abgr, "argb": argb, "palette": palhex}


def _col(h):
    r, g, b = _rgb(h)
    return (r << 16) | (g << 8) | b


def _bg_values(eff, cfg, pre):
    """Opacidad y colores de fondo para la barra (pre='tb') o el menú (pre='sm')."""
    tint = _col(cfg.get(pre + "_tint"))
    if eff == "transparent":
        return 0, NO_TINT, NO_TINT
    # la perilla de opacidad vale para translúcido, color sólido y degradado
    opacity = max(0, min(100, int(cfg.get(pre + "_opacity", 100))))
    if eff == "translucent":
        return opacity, (tint if cfg.get(pre + "_tint_on") else NO_TINT), NO_TINT
    if eff == "gradient":
        return opacity, tint, _col(cfg.get(pre + "_tint2"))
    return opacity, tint, NO_TINT


def effect_values(cfg):
    """Valores que lee wstb.dll (clave HKCU Software/WinStyler). {} = nada que escribir."""
    out = {}
    eff = cfg.get("tb_effect", "keep")
    if eff in EFFECT_ON:
        opacity, tint, tint2 = _bg_values(eff, cfg, "tb")
        stroke = cfg.get("tb_stroke", "keep")
        stroke = (1 if stroke == "show" else 0) if eff == "transparent" else (0 if stroke == "hide" else 1)
        out.update({"TbEnabled": 1, "TbOpacity": opacity, "TbTint": tint, "TbTint2": tint2, "TbStroke": stroke})
    elif eff == "default":
        out["TbEnabled"] = 0

    seff = cfg.get("sm_effect", "keep")
    extras = any(cfg.get(k, "keep") != "keep" for k in ("sm_shadow", "sm_border", "sm_search", "sm_rec")) or \
        any(cfg.get(k) is not None for k in ("sm_corner", "sm_scale", "sm_height"))
    if seff in EFFECT_ON or (extras and seff != "default"):
        opacity, tint, tint2 = _bg_values(seff, cfg, "sm") if seff in EFFECT_ON else (100, NO_TINT, NO_TINT)
        shadow = cfg.get("sm_shadow", "keep")
        shadow = (1 if shadow == "show" else 0) if seff == "transparent" else (0 if shadow == "hide" else 1)

        def flag(k):
            return 0 if cfg.get(k, "keep") == "hide" else 1

        out.update({"SmEnabled": 1, "SmOpacity": opacity, "SmTint": tint, "SmTint2": tint2,
                    "SmCorner": NO_TINT if cfg.get("sm_corner") is None else int(cfg["sm_corner"]),
                    "SmScale": int(cfg.get("sm_scale") or 0), "SmHeight": int(cfg.get("sm_height") or 0),
                    "SmShadow": shadow, "SmBorder": flag("sm_border"), "SmSearch": flag("sm_search"),
                    "SmRec": flag("sm_rec")})
    elif seff == "default":
        out["SmEnabled"] = 0
    return out


def build_items(cfg):
    """Devuelve la lista de valores de registro a escribir (con copia de seguridad)."""
    items = []

    def add(path, name, val, typ="REG_DWORD"):
        items.append({"path": path, "name": name, "type": typ, "data": str(val)})

    g = lambda k: cfg.get(k, "keep")

    for key, path, names, mapping in TABLE:
        v = mapping.get(g(key))
        if v is None:
            continue
        for n in names:
            add(path, n, v)

    # Búsqueda web en Inicio (Win 11 usa la política, Win 10 BingSearchEnabled)
    if g("st_web_search") == "off":
        add(POL, "DisableSearchBoxSuggestions", 1)
    elif g("st_web_search") == "on":
        add(POL, "DisableSearchBoxSuggestions", 0)

    # Recomendaciones del menú Inicio
    if g("st_hide_rec") == "on":
        add(ADV, "Start_IrisRecommendations", 0)
        add(ADV, "Start_TrackDocs", 0)
    elif g("st_hide_rec") == "off":
        add(ADV, "Start_IrisRecommendations", 1)
        add(ADV, "Start_TrackDocs", 1)

    # Sugerencias / anuncios
    if g("st_suggestions") in ("on", "off"):
        v = 1 if g("st_suggestions") == "on" else 0
        for n in ("SystemPaneSuggestionsEnabled", "SubscribedContent-338388Enabled",
                  "SubscribedContent-338389Enabled", "SubscribedContent-310093Enabled",
                  "SoftLandingEnabled"):
            add(CDM, n, v)

    # Transparencia
    tr = g("transparency")
    if tr == "off":
        add(PERS, "EnableTransparency", 0)
    elif tr in ("normal", "extra"):
        add(PERS, "EnableTransparency", 1)
    if tr == "extra":
        add(HK_ADV, "UseOLEDTaskbarTransparency", 1)

    # Tema / color de acento
    color_tb = g("tb_color_on")
    theme = g("tb_theme")
    if color_tb == "on":
        theme = "dark"  # Windows solo aplica el acento a la barra en modo oscuro
    if theme == "dark":
        add(PERS, "SystemUsesLightTheme", 0)
    elif theme == "light":
        add(PERS, "SystemUsesLightTheme", 1)
    if color_tb == "on":
        add(PERS, "ColorPrevalence", 1)
    elif color_tb == "off":
        add(PERS, "ColorPrevalence", 0)
    if g("border_color_on") == "on":
        add(DWM, "ColorPrevalence", 1)
    elif g("border_color_on") == "off":
        add(DWM, "ColorPrevalence", 0)
    if color_tb == "on" or g("border_color_on") == "on":
        a = accent_values(cfg.get("accent_color", "#0078D4"))
        add(DESK, "AutoColorization", 0)
        add(DWM, "AccentColor", a["abgr"])
        add(DWM, "ColorizationColor", a["argb"])
        add(DWM, "ColorizationAfterglow", a["argb"])
        add(ACCENT, "AccentColorMenu", a["abgr"])
        add(ACCENT, "StartColorMenu", a["abgr"])
        add(ACCENT, "AccentPalette", a["palette"], "REG_BINARY")

    # Animaciones y tiempos
    if g("min_anim") in ("on", "off"):
        add(WINMET, "MinAnimate", 1 if g("min_anim") == "on" else 0, "REG_SZ")
    if cfg.get("tb_hover_ms") is not None:
        add(ADV, "ExtendedUIHoverTime", int(cfg["tb_hover_ms"]))
    if cfg.get("menu_delay") is not None:
        add(DESK, "MenuShowDelay", int(cfg["menu_delay"]), "REG_SZ")

    # Menú contextual clásico (Windows 11): se crea o borra una clave entera
    if g("ex_classic") in ("on", "off"):
        items.append({"path": CLASSIC, "name": "*KEY*", "type": "KEY", "data": g("ex_classic")})

    # Política (administrador): ocultar «Recomendado»
    if cfg.get("st_force_rec"):
        add(HK_START, "HideRecommendedSection", 1)
        add(HK_EDU, "IsEducationEnvironment", 1)
    return items


def has_changes(cfg):
    if any(cfg.get(k, "keep") != "keep" for k in CHOICE_KEYS):
        return True
    if any(cfg.get(k) is not None for k in ("tb_hover_ms", "menu_delay", "sm_corner", "sm_scale", "sm_height")):
        return True
    return bool(cfg.get("st_force_rec")) or bool(cfg.get("folders"))


def _scope(path):
    return "HKLM" if path.upper().startswith("HKLM") else "HKCU"


def _ps_path(p):
    if p.upper().startswith("HKCU\\"):
        return "HKCU:\\" + p[5:]
    if p.upper().startswith("HKLM\\"):
        return "HKLM:\\" + p[5:]
    return p


def _q(s):
    return str(s).replace("'", "''")


def _safe(name, default="Carpeta"):
    s = re.sub(r'[\\/:*?"<>|]', "_", str(name)).strip().rstrip(".")
    return s or default


def _ps_items(items, autohide):
    rows = []
    for it in items:
        rows.append("  @{s='%s';p='%s';n='%s'}" % (_scope(it["path"]), _q(_ps_path(it["path"])), _q(it["name"])))
    if autohide in ("on", "off"):
        rows.append("  @{s='HKCU';p='%s';n='Settings'}" % _q(_ps_path(STUCK)))
    if not rows:
        return "$items = @()"
    return "$items = @(\n" + ",\n".join(rows) + "\n)"


def _ps_extras(cfg):
    out = []
    ah = cfg.get("tb_autohide", "keep")
    if ah in ("on", "off"):
        out.append("$p = '%s'" % _q(_ps_path(STUCK)))
        out.append("$v = (Get-ItemProperty -Path $p -Name Settings).Settings")
        out.append("if ($v) { $v[8] = %d; Set-ItemProperty -Path $p -Name Settings -Value $v }" % (3 if ah == "on" else 2))
    folders = cfg.get("folders") or []
    if folders:
        out.append("$sh = New-Object -ComObject WScript.Shell")
        out.append("$base = Join-Path $env:APPDATA 'Microsoft\\Windows\\Start Menu\\Programs'")
        out.append("""function New-WsFolder($name, $apps) {
  $d = Join-Path $base $name
  $mk = Join-Path $d '.winstyler.marker'
  if ((Test-Path -LiteralPath $d) -and -not (Test-Path -LiteralPath $mk)) {
    Write-Host ("Se omite '" + $name + "': ya existe y no fue creada por WinStyler")
    return
  }
  New-Item -ItemType Directory -Path $d -Force | Out-Null
  Set-Content -LiteralPath $mk -Value 'WinStyler'
  (Get-Item -LiteralPath $mk -Force).Attributes = 'Hidden'
  Get-ChildItem -LiteralPath $d -Filter *.lnk | Remove-Item -Force
  foreach ($a in $apps) {
    $l = $sh.CreateShortcut((Join-Path $d ($a.n + '.lnk')))
    $l.TargetPath = $a.t
    $l.WorkingDirectory = Split-Path $a.t
    if ($a.i) { $l.IconLocation = $a.i }
    $l.Save()
  }
}""")
        for f in folders:
            apps = []
            for a in f.get("apps", []):
                icon = a.get("icon") or ""
                if icon and "," not in icon:
                    icon += ",0"
                apps.append("@{n='%s';t='%s';i='%s'}" % (_q(_safe(a.get("name"), "App")), _q(a.get("path", "")), _q(icon)))
            arr = "@(" + ", ".join(apps) + ")" if apps else "@()"
            out.append("New-WsFolder '%s' %s" % (_q(_safe(f.get("name"))), arr))
    return "\n".join(out)


PS_COMMON = r"""#PS_BEGIN
$ErrorActionPreference = 'SilentlyContinue'
$mode  = $env:WS_MODE
$scope = $env:WS_SCOPE
$wsDir = Join-Path $env:LOCALAPPDATA 'WinStyler'
New-Item -ItemType Directory -Path $wsDir -Force | Out-Null
$bkFile = Join-Path $wsDir ('backup_' + $scope + '.json')
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$dll = Join-Path $wsDir 'wstb.dll'
@@ITEMS@@
$bk = @{}
if (Test-Path -LiteralPath $bkFile) {
  $o = Get-Content -LiteralPath $bkFile -Raw | ConvertFrom-Json
  foreach ($pr in $o.PSObject.Properties) { $bk[$pr.Name] = $pr.Value }
}
if ($mode -eq 'backup') {
  foreach ($it in $items) {
    if ($it.s -ne $scope) { continue }
    $key = $it.p + '|' + $it.n
    if ($bk.ContainsKey($key)) { continue }
    if ($it.n -eq '*KEY*') {
      $bk[$key] = @{ exists = (Test-Path -LiteralPath $it.p); kind = 'KEY' }
      continue
    }
    $e = @{ exists = $false }
    if (Test-Path -LiteralPath $it.p) {
      $k = Get-Item -LiteralPath $it.p
      if ($k.GetValueNames() -contains $it.n) {
        $kind = $k.GetValueKind($it.n).ToString()
        $val = $k.GetValue($it.n)
        if ($val -is [byte[]]) { $val = @($val) }
        $e = @{ exists = $true; kind = $kind; value = $val }
      }
    }
    $bk[$key] = $e
  }
  $bk | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $bkFile -Encoding UTF8
}
if ($mode -eq 'restore') {
  if (-not (Test-Path -LiteralPath $bkFile)) { Write-Host ('No hay copia de seguridad para ' + $scope) }
  foreach ($k in @($bk.Keys)) {
    $parts = $k -split '\|', 2
    $p = $parts[0]; $n = $parts[1]; $e = $bk[$k]
    if ($n -eq '*KEY*') {
      if (-not $e.exists) { Remove-Item -LiteralPath $p -Recurse -Force }
      continue
    }
    if ($e.exists) {
      if (-not (Test-Path -LiteralPath $p)) { New-Item -Path $p -Force | Out-Null }
      switch ($e.kind) {
        'DWord'  { $v = [int]$e.value; $t = 'DWord' }
        'QWord'  { $v = [long]$e.value; $t = 'QWord' }
        'Binary' { $v = [byte[]]@($e.value); $t = 'Binary' }
        default  { $v = [string]$e.value; $t = 'String' }
      }
      New-ItemProperty -LiteralPath $p -Name $n -Value $v -PropertyType $t -Force | Out-Null
    } else {
      Remove-ItemProperty -LiteralPath $p -Name $n -ErrorAction SilentlyContinue
    }
  }
  if ($scope -eq 'HKCU') {
    $base = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
    Get-ChildItem -LiteralPath $base -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName '.winstyler.marker') } | Remove-Item -Recurse -Force
  }
}
if ($mode -eq 'extras') {
@@EXTRAS@@
}
if ($mode -eq 'effect' -or $mode -eq 'purge') {
  # versiones anteriores dejaban un proceso residente (rundll32 ...,Keep): se detiene
  try { $ev = [System.Threading.EventWaitHandle]::OpenExisting('Local\WinStylerTBStop'); [void]$ev.Set(); Start-Sleep -Milliseconds 800 } catch {}
  Stop-Process -Name StartMenuExperienceHost -Force -ErrorAction SilentlyContinue
  Start-Sleep -Milliseconds 400
}
$on = $false
if ($mode -eq 'effect') {
  $cfg = Get-ItemProperty -LiteralPath 'HKCU:\Software\WinStyler'
  $on = ($cfg.TbEnabled -eq 1) -or ($cfg.SmEnabled -eq 1)
}
if ($mode -eq 'effect' -and $on) {
  $s = [IO.File]::ReadAllText($env:WS_SELF, [Text.Encoding]::UTF8)
  $mk = '#WSTB' + '64#'
  $i = $s.IndexOf($mk)
  if ($i -ge 0) {
    $j = $s.IndexOf("`n", $i)
    $bytes = [Convert]::FromBase64String($s.Substring($i + $mk.Length, $j - $i - $mk.Length).Trim())
    for ($t = 0; $t -lt 25; $t++) { try { [IO.File]::WriteAllBytes($dll, $bytes); break } catch { Start-Sleep -Milliseconds 300 } }
  }
  if (Test-Path -LiteralPath $dll) {
    # carga única al iniciar sesión: rundll32 prepara barra y menú y termina enseguida
    New-ItemProperty -Path $runKey -Name 'WinStylerTB' -Value ('rundll32.exe "' + $dll + '",Apply') -PropertyType String -Force | Out-Null
    Start-Process -FilePath 'rundll32.exe' -ArgumentList ('"' + $dll + '",Apply')
  }
}
if (($mode -eq 'effect' -and -not $on) -or $mode -eq 'purge') {
  Remove-ItemProperty -Path $runKey -Name 'WinStylerTB' -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath 'HKCU:\Software\WinStyler' -Recurse -Force
  for ($t = 0; $t -lt 25 -and (Test-Path -LiteralPath $dll); $t++) { Remove-Item -LiteralPath $dll -Force; if (Test-Path -LiteralPath $dll) { Start-Sleep -Milliseconds 300 } }
}
if ($mode -eq 'purge') {
  for ($t = 0; $t -lt 10 -and (Test-Path -LiteralPath $wsDir); $t++) { Remove-Item -LiteralPath $wsDir -Recurse -Force; if (Test-Path -LiteralPath $wsDir) { Start-Sleep -Milliseconds 300 } }
}
if ($mode -eq 'tray') {
  # Tras reiniciar el Explorador, los programas en segundo plano vuelven a mostrar su ícono.
  Start-Sleep -Seconds 4
  Add-Type -Namespace WsTray -Name U -MemberDefinition '[DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern uint RegisterWindowMessage(string s); [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);'
  [void][WsTray.U]::PostMessage([IntPtr]0xffff, [WsTray.U]::RegisterWindowMessage('TaskbarCreated'), [IntPtr]::Zero, [IntPtr]::Zero)
}
if ((Test-Path -LiteralPath $wsDir) -and -not (Get-ChildItem -LiteralPath $wsDir -Force)) { Remove-Item -LiteralPath $wsDir -Force }
"""

PS_LINE = ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$m=\'#PS_\'+\'BEGIN\'; '
           '$s=[IO.File]::ReadAllText($env:WS_SELF,[Text.Encoding]::UTF8); '
           'Invoke-Expression $s.Substring($s.IndexOf($m))"')

ELEV_LINE = ("powershell -NoProfile -Command \"Start-Process -FilePath '%WS_SELF%' "
             "-ArgumentList 'hklm' -Verb RunAs -WindowStyle Hidden -Wait\"")



def _regadd(it):
    if it["type"] == "KEY":
        if it["data"] == "on":
            return 'reg add "%s\\InprocServer32" /ve /f >nul' % it["path"]
        return 'reg delete "%s" /f >nul 2>&1' % it["path"]
    return 'reg add "%s" /v "%s" /t %s /d %s /f >nul' % (it["path"], it["name"], it["type"], it["data"])


def _join(lines):
    return "\r\n".join(lines) + "\r\n"


def needs_dll(cfg):
    v = effect_values(cfg)
    return v.get("TbEnabled") == 1 or v.get("SmEnabled") == 1


def build_apply_bat(cfg, dll_b64=None):
    items = build_items(cfg)
    hkcu = [i for i in items if _scope(i["path"]) == "HKCU"]
    hklm = [i for i in items if _scope(i["path"]) == "HKLM"]
    ah = cfg.get("tb_autohide", "keep")
    extras = _ps_extras(cfg)
    eff = effect_values(cfg)
    blob = needs_dll(cfg)
    if blob and not dll_b64:
        raise ValueError("Falta el módulo wstb.dll para los efectos de barra / menú Inicio.")
    L = []
    L += ["@echo off", "setlocal EnableExtensions", 'set "WS_SELF=%~f0"',
          'if /i "%~1"=="hklm" goto :hklm_only',
          "title WinStyler - Aplicando estilo",
          "echo Aplicando estilo de WinStyler...", ""]
    if hkcu or ah in ("on", "off"):
        L += ['set "WS_MODE=backup"', 'set "WS_SCOPE=HKCU"', "call :ps"]
    L += [_regadd(i) for i in hkcu]
    if extras:
        L += ['set "WS_MODE=extras"', 'set "WS_SCOPE=HKCU"', "call :ps"]
    if hklm:
        L += ["net session >nul 2>&1", "if not %errorlevel%==0 goto :elev", "call :hklm",
              "goto :after_hklm", ":elev",
              "echo Se necesitan permisos de administrador para algunas opciones...", ELEV_LINE,
              ":after_hklm"]
    if eff:
        L += ['reg add "%s" /v "%s" /t REG_DWORD /d 0x%X /f >nul' % (WSKEY, n, v) for n, v in eff.items()]
    L += ["echo Reiniciando el Explorador de Windows...",
          "taskkill /f /im explorer.exe >nul 2>&1"]
    if eff:
        L += ['set "WS_MODE=effect"', 'set "WS_SCOPE=HKCU"', "call :ps"]
    L += ['start "" explorer.exe', 'set "WS_MODE=tray"', 'set "WS_SCOPE=HKCU"', "call :ps"]
    L += ["echo Listo.",
          "exit /b 0", "",
          ":hklm_only", "call :hklm", "exit /b 0", "",
          ":hklm", 'set "WS_MODE=backup"', 'set "WS_SCOPE=HKLM"']
    if hklm:
        L.append("call :ps")
    L += [_regadd(i) for i in hklm]
    L += ["exit /b 0", "",
          ":ps", PS_LINE, "exit /b 0", ""]
    if blob:
        L += ["rem #WSTB64#" + dll_b64, ""]
    ps = PS_COMMON.replace("@@ITEMS@@", _ps_items(items, ah)).replace("@@EXTRAS@@", extras)
    return _join(L) + ps.replace("\r\n", "\n").replace("\n", "\r\n")


def build_restore_bat():
    L = ["@echo off", "setlocal EnableExtensions", 'set "WS_SELF=%~f0"',
         'if /i "%~1"=="hklm" goto :hklm_only',
         "title WinStyler - Restaurar valores originales",
         "echo Restaurando valores originales...",
         'set "WS_MODE=restore"', 'set "WS_SCOPE=HKCU"', "call :ps",
         'if not exist "%LOCALAPPDATA%\\WinStyler\\backup_HKLM.json" goto :restart',
         "net session >nul 2>&1", "if not %errorlevel%==0 goto :elev", "call :hklm", "goto :restart",
         ":elev", ELEV_LINE,
         ":restart",
         "echo Reiniciando el Explorador de Windows...",
         "taskkill /f /im explorer.exe >nul 2>&1",
         'set "WS_MODE=purge"', 'set "WS_SCOPE=HKCU"', "call :ps",
         'start "" explorer.exe',
         'set "WS_MODE=tray"', 'set "WS_SCOPE=HKCU"', "call :ps",
         "echo Listo.",
         "exit /b 0", "",
         ":hklm_only", "call :hklm", "exit /b 0", "",
         ":hklm", 'set "WS_MODE=restore"', 'set "WS_SCOPE=HKLM"', "call :ps", "exit /b 0", "",
         ":ps", PS_LINE, "exit /b 0", ""]
    ps = PS_COMMON.replace("@@ITEMS@@", "$items = @()").replace("@@EXTRAS@@", "")
    return _join(L) + ps.replace("\n", "\r\n")
