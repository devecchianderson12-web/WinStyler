# WinStyler

Plataforma de personalización de **Windows 10 / 11**: temas completos, un catálogo de mods ampliable y
un motor de estilos XAML para transformar la barra de tareas, el menú Inicio y el Explorador.
Programa portable (`WinStyler.exe`, un solo archivo): no instala servicios y no deja procesos en segundo plano.

## Uso

1. **Temas**: elegí un tema de la biblioteca (Windows 11 Glass, Midnight Float, Dock y cápsula, Minimalista,
   Neón Nexus, Custom) y miralo en la vista previa. Podés aplicarlo, editarlo, duplicarlo, crear uno desde la
   configuración actual, guardarlo, exportarlo, importarlo y eliminar los propios.
2. **Mods**: catálogo con buscador y filtro por categoría. Cada mod muestra nombre, descripción, categoría,
   autor, versión, compatibilidad, requisitos, si reinicia el Explorador y su estado; se configura, se
   activa/desactiva, se exporta y (los propios) se elimina. «Instalar mod…» agrega un `.json` y
   «Importar de Windhawk…» convierte un tema del Taskbar/Start Menu Styler de Windhawk.
3. **Barra, Efectos, Inicio, Explorador, Carpetas**: ajustes individuales. «—» deja ese valor como está.
4. **Generar y aplicar** crea un `.bat` temporal, lo ejecuta y lo **borra** al terminar.
   **Guardar .bat** guarda `aplicar_estilo.bat` y `restaurar_original.bat` donde elijas.
5. **Restaurar original** devuelve los valores previos, quita estilos y efectos y borra lo que WinStyler
   guardó en el sistema (`%LOCALAPPDATA%\WinStyler`, `HKCU\Software\WinStyler`).
6. Los perfiles (`.json`) incluyen ajustes y mods; los perfiles de versiones anteriores siguen sirviendo.

La vista previa es una **simulación** (lo indica su título, y cuenta los mods que no puede simular);
debajo se muestra qué está **aplicado en el sistema** y cuándo.
Opciones y mods indican su compatibilidad (**[10]**, **[11]**, compilación mínima).
Antes de cambiar el registro, el `.bat` guarda una copia de los valores originales.

## Qué cambia y cómo

| Tipo | Ejemplos | Mecanismo | Persistencia / consumo |
| --- | --- | --- | --- |
| Nativo | Alineación, botones, agrupación, reloj con segundos, tema, acento, recomendados, Bing, Explorador, menú contextual clásico, mods de registro | Registro de Windows desde el `.bat` (con copia de seguridad) | Permanente, sin consumo |
| Efectos | Fondo de barra y menú: transparente, translúcido, sólido, degradado, opacidad, esquinas, tamaño | `wstb.dll` (módulo nativo C++/WinRT) | Ver abajo |
| Mods de estilo | Barra flotante, acrílico, dock, bandeja en cápsula, botones, indicador, íconos, reloj, menú acrílico, bordes, elementos, columnas, tipografía | Motor de estilos de `wstb.dll` (`styles.wss`) | Ver abajo |

### Módulo `wstb.dll`

- Solo se copia a `%LOCALAPPDATA%\WinStyler` si usás efectos o mods de estilo.
- Al aplicar y al iniciar sesión corre **una vez** `rundll32 wstb.dll,Apply` (clave Run `WinStylerTB`):
  carga la DLL dentro del Explorador y **termina**. No queda ningún proceso propio residente.
- Windows 11: entra al Explorador y al menú Inicio con la API de diagnóstico XAML (como TranslucentTB) y
  aplica las reglas de `styles.wss` a cada elemento que aparece (también al cambiar un estado visual).
- Windows 10: la barra usa `SetWindowCompositionAttribute` desde dentro del Explorador (los mods de estilo
  son solo para Windows 11).
- Inspector de elementos para escribir mods: con `HKCU\Software\WinStyler\DumpTree = 1` (DWORD) cada
  elemento y sus padres se anotan en `%TEMP%\winstyler_tree.txt` (Explorador) o en la carpeta temporal del
  paquete del menú Inicio.

Consumo, compatibilidad y comparación con Windhawk: [docs/INVENTARIO.md](docs/INVENTARIO.md).

### Limitaciones

- Si el Explorador se cierra inesperadamente, estilos y efectos vuelven al aplicar o al iniciar sesión.
- El menú Inicio no puede agrandarse más que su tamaño normal; el panel de búsqueda (SearchHost, contenido
  web) no se puede teñir; el diseño «lado a lado» hace caer el menú de 23H2 y no se incluye.
- Mods de Windhawk que enganchan funciones (volumen con la rueda, etiquetas en la barra de 11, barra vertical…)
  no tienen equivalente.

## Crear un mod

Un mod es un `.json` (ver los de `mods/`):

```json
{
  "schema": 1, "id": "mi-mod", "name": "Mi mod", "category": "Barra de tareas",
  "description": "Qué hace", "author": "Yo", "version": "1.0",
  "compat": {"min_build": 22000}, "restart": "none",
  "settings": [
    {"key": "radius", "label": "Radio", "type": "number", "min": 0, "max": 24, "default": 12, "unit": "px"},
    {"key": "color", "label": "Color", "type": "color", "default": "#557B6CF6"},
    {"key": "hide", "label": "Ocultar", "type": "bool", "default": false}
  ],
  "constants": {"Fondo": "<SolidColorBrush Color=\"{color}\"/>"},
  "rules": [
    {"process": "explorer", "target": "Taskbar.TaskbarFrame > Grid#RootGrid > Taskbar.TaskbarBackground > Grid > Rectangle#BackgroundFill",
     "styles": ["RadiusX={radius}", "RadiusY={radius}", "Fill:=$Fondo"]},
    {"process": "start", "target": "Border#AcrylicBorder", "styles": ["CornerRadius={radius}"], "when": "hide"}
  ],
  "registry": [
    {"path": "HKCU\\Software\\...", "name": "Valor", "type": "REG_DWORD", "data": "1"}
  ]
}
```

- `process`: `explorer` (barra, bandeja, Explorador de archivos) o `start` (menú Inicio).
- `target` y `styles` usan la sintaxis del Taskbar/Start Menu Styler de Windhawk (`Prop=valor`,
  `Prop:=<XAML>`, `Prop@Estado=…` con `@Grupo` en el objetivo, `$Constante`).
- `{clave}` se reemplaza por el ajuste; `{clave/100}` lo divide por 100. `when` activa la regla solo si el
  ajuste booleano está en verdadero.
- `restart`: `none`, `explorer`, `logoff` o `reboot`.
- Mods y temas propios se guardan en `%APPDATA%\WinStyler\mods` y `%APPDATA%\WinStyler\temas`.

## Compilar

### GitHub Actions

Cada push a `main`/`master` ejecuta `.github/workflows/build.yml` en `windows-latest`: instala
`requirements-build.txt`, compila `native/wstb.dll` (`wstb.cpp` + `styler.cpp`), genera `WinStyler.exe`
(con `mods/` y `themes/` incluidos) y renueva la release `latest`, así
`releases/latest/download/WinStyler.exe` siempre descarga la última versión.

### Local

Requisitos: Python 3.12 y Visual Studio Build Tools con «Desarrollo para el escritorio con C++» (incluye el Windows SDK).

```bat
pip install -r requirements-build.txt
compilar.bat
```

`compilar.bat` compila `native\wstb.dll` si falta y deja solo `WinStyler.exe` en la carpeta del proyecto.
`assets\crear_icono.py` regenera el ícono y el logo (requiere Pillow).

## Estructura

| Ruta | Contenido |
| --- | --- |
| `WinStyler.py` | Interfaz: temas, catálogo, ajustes, vista previa simulada, perfiles, ejecución del `.bat` |
| `catalogo.py` | Biblioteca de mods y temas, compilación de `styles.wss`, importación de Windhawk |
| `generador.py` | Genera los `.bat` de aplicar/restaurar (registro, efectos, estilos) |
| `mods/`, `themes/` | Mods y temas incluidos (JSON) |
| `native/` | `wstb.dll`: carga sin proceso residente, efectos y motor de estilos (`styler.cpp`) |
| `assets/` | Ícono, logo y el script que los genera |
| `docs/INVENTARIO.md` | Inventario de Windhawk, equivalencias, requisitos y consumo |
| `compilar.bat` | Compilación local de un único `WinStyler.exe` |
