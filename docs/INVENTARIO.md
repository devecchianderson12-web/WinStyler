# Inventario: Windhawk frente a WinStyler

Relevamiento de las capacidades de [Windhawk](https://windhawk.net/) y su catálogo
([windhawk-mods](https://github.com/ramensoftware/windhawk-mods), guías de estilos de
[barra](https://github.com/ramensoftware/windows-11-taskbar-styling-guide) y
[menú Inicio](https://github.com/ramensoftware/windows-11-start-menu-styling-guide)), y cómo lo cubre WinStyler.

## Cómo funciona cada uno

| | Windhawk | WinStyler |
| --- | --- | --- |
| Motor | Inyecta su motor en los procesos y cada mod (C++) engancha funciones o modifica XAML | `wstb.dll` entra al Explorador y al menú Inicio con la API de diagnóstico XAML y aplica reglas de estilo; el resto es registro de Windows |
| Procesos residentes | `windhawk.exe` queda en segundo plano | Ninguno: `rundll32 wstb.dll,Apply` corre una vez al aplicar e iniciar sesión y termina |
| Mods visuales | Taskbar Styler / Start Menu Styler (objetivo + estilos) | Mismo modelo de objetivos y estilos; se pueden importar sus temas en modo textual |
| Mods que enganchan funciones | Sí (comportamiento de la barra, clics, rueda, etc.) | No (requeriría compilar código por mod; ver «No cubierto») |

## Motor de estilos (equivalente a los Stylers)

| Función del Styler de Windhawk | WinStyler |
| --- | --- |
| `target: A > B > C` (padre directo), varios objetivos separados por coma | Sí |
| `Tipo#Nombre`, tipos cortos (`Grid`) o completos (`Taskbar.TaskbarFrame`) | Sí |
| Filtros `[Propiedad=Valor]` | `Name`, `AutomationProperties.AutomationId`, `AutomationProperties.Name`, `Text` |
| Estilos `Prop=valor` y `Prop:=<XAML>` | Sí (cualquier propiedad, incluso adjuntas como `Grid.Column`) |
| Estados visuales `Prop@Estado=…` con `@Grupo` en el objetivo | Sí (se aplican al cambiar el estado; si una animación del sistema anima la misma propiedad, la animación manda) |
| `styleConstants` (`$Nombre`) | Sí |
| `WindhawkBlur` | Se convierte en `AcrylicBrush` de XAML (desenfoque real del fondo) |
| Expresiones `{{…}}`, enlaces `=>`, `:root` | No; esos estilos se omiten al importar y se informa cuántos |
| Barra, bandeja, miniaturas (proceso Explorador) | Sí (`@explorer`) |
| Menú Inicio (StartMenuExperienceHost) | Sí (`@start`) |
| Centro de notificaciones (ShellExperienceHost) | No por ahora |

## Catálogo de Windhawk y equivalentes

| Mod de Windhawk (o función) | WinStyler | Cómo |
| --- | --- | --- |
| Windows 11 Taskbar Styler (temas) | Sí | Motor de estilos + importación + mods incluidos |
| Windows 11 Start Menu Styler (temas) | Sí | Motor de estilos + importación + mods incluidos |
| Barra translúcida / transparente / acrílica | Sí | Efectos de barra + mod «Fondo acrílico / desenfoque» |
| Barra flotante redondeada | Sí | Mod «Barra flotante redondeada» |
| Barra tipo dock | Parcial | Mod «Barra tipo dock» (fondo detrás de los íconos, sin esquinas en el bloque) |
| Tamaño de íconos / altura de la barra | Sí | Mod «Tamaño de íconos» + altura nativa [11] |
| Indicador de apps abiertas, estilo de botones, hover | Sí | Mods «Indicador…», «Botones de aplicaciones» |
| Reloj (color, tamaño, ocultar fecha) | Sí | Mod «Reloj y fecha» |
| Reloj con formato propio (segundos, texto libre) | Parcial | Segundos nativos; el texto libre requiere enganchar funciones |
| Ocultar campana, «Mostrar escritorio», botón Inicio | Sí | Mods de bandeja y barra |
| Menú Inicio: transparencia, color, degradado, esquinas, borde, sombra | Sí | Efectos del menú + mods «Bordes y esquinas», «Fondo acrílico» |
| Menú Inicio: ocultar buscador, perfil, apagado, «Todos», recomendados | Sí | Mod «Elementos del menú» y opciones nativas |
| Menú Inicio: columnas y alto de anclados, tipografía | Sí | Mods «Anclados: filas y columnas», «Tipografía del menú» |
| Menú Inicio: tamaño (comprimir) y alto | Sí | Efectos del menú |
| Menú Inicio «lado a lado» (todas las apps + ancladas) | No en 23H2 | Mostrar el panel «Todas» a la fuerza hace caer StartMenuExperienceHost en 22621; los temas así de Windhawk apuntan al menú nuevo de 24H2 |
| Menú contextual clásico | Sí | Registro |
| Explorador: quitar Galería / Inicio, fila completa, extensiones, ocultos | Sí | Registro (mods y pestaña Explorador) |
| Explorador de archivos con estilos XAML (barra de comandos, pestañas) | Posible | El motor aplica `@explorer` también al XAML del Explorador de archivos; se pueden importar estilos |
| Volumen con la rueda sobre la barra, cerrar con clic central, etiquetas en la barra de 11, barra vertical o arriba en 11, varias filas | No | Requieren enganchar funciones de `Taskbar.dll`/`explorer.exe` (mods C++ de Windhawk) |

## Requisitos y consumo

- Cambios de registro: persistentes, cero consumo. Algunos piden reiniciar el Explorador (lo hace el `.bat`) o cerrar sesión (se indica en cada mod).
- Efectos y mods de estilo: `wstb.dll` queda cargada dentro del Explorador y del menú Inicio (no es un proceso aparte). La DLL pesa unos 300 KB y su memoria crece con la cantidad de elementos de la interfaz que vigila; usa CPU solo cuando se crean elementos o cambia un estado visual (no hay sondeos periódicos, salvo una comprobación del menú Inicio cada 2 s dentro del Explorador).
- Al iniciar sesión, `rundll32 wstb.dll,Apply` corre unos segundos y termina.
- Si el Explorador se cierra de forma inesperada, los estilos vuelven al aplicar de nuevo o al iniciar sesión.
