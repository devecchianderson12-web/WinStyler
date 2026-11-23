# WinStyler

Editor visual de la barra de tareas, el menú Inicio y el Explorador para **Windows 10 / 11**.
Programa portable (`WinStyler.exe`, un solo archivo): no instala nada y no deja procesos en segundo plano.

## Uso

1. Ajustá las opciones (pestañas **Barra**, **Efectos**, **Inicio**, **Explorador** y **Carpetas**) y mirá la vista previa. «—» deja ese valor como está.
2. **Generar y aplicar** crea un `.bat` temporal, lo ejecuta y lo **borra** al terminar: no queda ningún archivo en el escritorio ni junto al programa.
3. **Guardar .bat** guarda `aplicar_estilo.bat` y `restaurar_original.bat` en la carpeta que elijas.
4. **Restaurar original** devuelve los valores que había antes, quita los efectos de barra y menú y borra todo lo que WinStyler guardó (`%LOCALAPPDATA%\WinStyler` y `HKCU\Software\WinStyler`).
5. Preajustes: Limpio, Flotante, Rendimiento y Restablecer. En la pestaña Inicio: «Modo compacto».
6. Los perfiles (`.json`) se guardan y cargan desde la botonera; los perfiles de versiones anteriores siguen sirviendo.

Opciones marcadas **[10]** u **[11]** aplican solo a esa versión de Windows. Las marcadas «admin» piden permisos (UAC).
Antes de cambiar algo, el `.bat` guarda una copia de los valores originales en `%LOCALAPPDATA%\WinStyler`.

## Qué cambia

- **Nativo (registro de Windows):** alineación, altura, botones de la barra, agrupación, multipantalla, bandeja, reloj, tema, acento, transparencia, animaciones y tiempos, menú Inicio (recomendados, distribución, sugerencias, Bing), Explorador (extensiones, ocultos, vista compacta, casillas, menú contextual clásico) y carpetas con accesos en «Todas las aplicaciones».
- **Fondo de la barra:** transparente (íconos flotando), translúcida, color sólido o degradado, con perilla de opacidad y línea superior on/off.
- **Menú Inicio [11]:** fondo transparente, translúcido, sólido o degradado (también en carpetas abiertas y «Todas»), opacidad, esquinas, tamaño (comprime sin recortar), alto, sombra, borde, cuadro de búsqueda y «Recomendado».

### Cómo funcionan los efectos de fondo

Los hace `native/wstb.dll`, que solo se copia a `%LOCALAPPDATA%\WinStyler` si elegís un efecto:

- Al aplicar y al iniciar sesión se ejecuta **una vez** `rundll32 wstb.dll,Apply` (clave Run `WinStylerTB`), que carga la DLL dentro del Explorador y **termina**. No queda ningún proceso propio residente.
- Windows 11: la DLL entra al Explorador y al menú Inicio con la API de diagnóstico XAML (como TranslucentTB). Desde el Explorador un hilo vuelve a preparar el menú si Windows lo reinicia.
- Windows 10: la barra usa `SetWindowCompositionAttribute` desde dentro del Explorador.
- «Predeterminado» en barra y menú, o «Restaurar original», quitan la DLL y la clave Run.

### Limitaciones

- Si el Explorador se cierra inesperadamente, el efecto de fondo vuelve al aplicar de nuevo o al iniciar sesión (no hay proceso vigilando, a propósito).
- El menú Inicio no puede agrandarse más que su tamaño normal; el panel de resultados de búsqueda (SearchHost, contenido web) no se puede teñir.
- No se puede cambiar el ícono del botón Inicio ni anclar carpetas directamente en «Anclado».
- La altura de la barra [11] depende de la compilación de Windows.

## Compilar

### GitHub Actions

Cada push a `main`/`master` ejecuta `.github/workflows/build.yml` en `windows-latest`:
instala las dependencias de `requirements-build.txt`, compila `native/wstb.dll` desde `native/wstb.cpp`,
genera `WinStyler.exe` y renueva la release `latest` con el exe nuevo, así el enlace
`releases/latest/download/WinStyler.exe` siempre descarga la última versión.

### Local

Requisitos: Python 3.12 y Visual Studio Build Tools con la carga «Desarrollo para el escritorio con C++» (incluye el Windows SDK).

```bat
pip install -r requirements-build.txt
compilar.bat
```

`compilar.bat` compila `native\wstb.dll` si falta y deja solo `WinStyler.exe` (con ícono) en la carpeta del proyecto; los temporales se borran.
`assets\crear_icono.py` regenera el ícono y el logo (requiere Pillow).

## Estructura

| Ruta | Contenido |
| --- | --- |
| `WinStyler.py` | Interfaz (tema oscuro, vista previa, perfiles, ejecución del `.bat`) |
| `generador.py` | Genera los `.bat` de aplicar/restaurar y la configuración de efectos |
| `native/` | Módulo de efectos `wstb.dll` (C++/WinRT) y su script de compilación |
| `assets/` | Ícono, logo y el script que los genera |
| `compilar.bat` | Compilación local de un único `WinStyler.exe` |
