// styler.h - motor genérico de estilos XAML de WinStyler (Windows 11).
// Aplica reglas "objetivo -> propiedades" a los elementos de la barra (Explorador) y del
// menú Inicio, con un formato compatible con los temas del Windows 11 Taskbar/Start Menu
// Styler de Windhawk (WinStyler los convierte a styles.wss).
#pragma once
#include <windows.h>
#include <winrt/Windows.UI.Xaml.h>

// Se llama una vez al cargarse en el proceso. inStart = StartMenuExperienceHost.
void Styler_Init(HMODULE module, bool inStart);
// Cada elemento que agrega el árbol XAML (hilo de interfaz).
void Styler_OnAdd(winrt::Windows::UI::Xaml::FrameworkElement const& el);
// Recarga styles.wss y reaplica en los elementos del hilo actual (hilo de interfaz).
void Styler_ReloadThread();
// Hilos de interfaz con elementos registrados (para despachar la recarga).
void Styler_Threads(std::vector<DWORD>& out);
// Marca que hay que releer el archivo (cualquier hilo).
void Styler_Invalidate();
