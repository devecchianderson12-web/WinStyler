// wstb.dll - efectos de barra de tareas y menú Inicio de WinStyler.
//  * Windows 11: se carga en el Explorador (barra) y en StartMenuExperienceHost (menú
//    Inicio) mediante la API de diagnóstico XAML (InitializeXamlDiagnosticsEx) y
//    cambia propiedades de los elementos XAML.
//  * Windows 10: la barra usa SetWindowCompositionAttribute.
// Uso: rundll32.exe wstb.dll,Keep   (proceso residente que mantiene los efectos)
// Configuración (DWORD) en HKCU\Software\WinStyler:
//   Barra: TbEnabled, TbOpacity (0-100), TbTint, TbTint2, TbStroke
//   Inicio: SmEnabled, SmOpacity, SmTint, SmTint2, SmCorner, SmScale (%), SmHeight,
//           SmShadow, SmBorder, SmSearch, SmRec
//   Colores 0x00RRGGBB; 0xFFFFFFFF = sin cambio / color de Windows.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#undef GetCurrentTime
#include <aclapi.h>
#include <sddl.h>
#include <tlhelp32.h>
#include <ocidl.h>
#include <xamlom.h>
#include <winrt/base.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.UI.h>
#include <winrt/Windows.UI.Xaml.h>
#include <winrt/Windows.UI.Xaml.Controls.h>
#include <winrt/Windows.UI.Xaml.Media.h>
#include <winrt/Windows.UI.Xaml.Shapes.h>
#include <algorithm>
#include <cmath>
#include <mutex>
#include <string_view>
#include <vector>

#pragma comment(lib, "windowsapp.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "oleaut32.lib")

namespace wux = winrt::Windows::UI::Xaml;
namespace wuxc = winrt::Windows::UI::Xaml::Controls;
namespace wuxm = winrt::Windows::UI::Xaml::Media;
using WInspectable = winrt::Windows::Foundation::IInspectable;

// {5C2B9E3A-8F41-4D7B-9A6E-3B1F2C7D8E90}
static const CLSID CLSID_WsTap = {0x5c2b9e3a, 0x8f41, 0x4d7b, {0x9a, 0x6e, 0x3b, 0x1f, 0x2c, 0x7d, 0x8e, 0x90}};
static const wchar_t REG_KEY[] = L"Software\\WinStyler";
static const DWORD NO_TINT = 0xFFFFFFFF;

static HMODULE g_module = nullptr;

static bool g_inStart = false;  // true dentro de StartMenuExperienceHost

// ------------------------------------------------------------------ configuración
struct Cfg {
    DWORD enabled = 0, opacity = 100, tint = NO_TINT, tint2 = NO_TINT, stroke = 1;
};

struct SmCfg {
    DWORD enabled = 0, opacity = 100, tint = NO_TINT, tint2 = NO_TINT, corner = NO_TINT;
    DWORD scale = 0, height = 0, shadow = 1, border = 1, search = 1, rec = 1;
};

static DWORD RegDw(const wchar_t* name, DWORD def) {
    DWORD v = 0, sz = sizeof(v);
    if (RegGetValueW(HKEY_CURRENT_USER, REG_KEY, name, RRF_RT_REG_DWORD, nullptr, &v, &sz) == ERROR_SUCCESS)
        return v;
    return def;
}

static Cfg ReadCfg() {
    Cfg c;
    c.enabled = RegDw(L"TbEnabled", 0);
    c.opacity = std::min<DWORD>(100, RegDw(L"TbOpacity", 100));
    c.tint = RegDw(L"TbTint", NO_TINT);
    c.tint2 = RegDw(L"TbTint2", NO_TINT);
    c.stroke = RegDw(L"TbStroke", 1);
    return c;
}

static SmCfg ReadSmCfg() {
    SmCfg c;
    c.enabled = RegDw(L"SmEnabled", 0);
    c.opacity = std::min<DWORD>(100, RegDw(L"SmOpacity", 100));
    c.tint = RegDw(L"SmTint", NO_TINT);
    c.tint2 = RegDw(L"SmTint2", NO_TINT);
    c.corner = RegDw(L"SmCorner", NO_TINT);
    c.scale = RegDw(L"SmScale", 0);
    c.height = RegDw(L"SmHeight", 0);
    c.shadow = RegDw(L"SmShadow", 1);
    c.border = RegDw(L"SmBorder", 1);
    c.search = RegDw(L"SmSearch", 1);
    c.rec = RegDw(L"SmRec", 1);
    return c;
}

static winrt::Windows::UI::Color Col(DWORD rgb) {
    return {255, (uint8_t)((rgb >> 16) & 0xFF), (uint8_t)((rgb >> 8) & 0xFF), (uint8_t)(rgb & 0xFF)};
}

// Pincel sólido o degradado (de tint a tint2).
static wuxm::Brush MakeBrush(DWORD tint, DWORD tint2, bool horizontal, uint8_t alpha = 255) {
    if (tint2 == NO_TINT) {
        auto col = Col(tint);
        col.A = alpha;
        return wuxm::SolidColorBrush(col);
    }
    wuxm::LinearGradientBrush b;
    b.StartPoint({0, 0});
    b.EndPoint(horizontal ? winrt::Windows::Foundation::Point{1, 0} : winrt::Windows::Foundation::Point{1, 1});
    wuxm::GradientStop s1, s2;
    auto c1 = Col(tint), c2 = Col(tint2);
    c1.A = c2.A = alpha;
    s1.Color(c1);
    s1.Offset(0);
    s2.Color(c2);
    s2.Offset(1);
    b.GradientStops().Append(s1);
    b.GradientStops().Append(s2);
    return b;
}

static std::recursive_mutex g_lock;

// ------------------------------------------------------------------ barra de tareas
struct Tracked {
    winrt::weak_ref<wux::Shapes::Rectangle> rect;
    bool stroke = false;
    DWORD tid = 0;
    double origOpacity = 1.0;
    wuxm::Brush origFill{nullptr};
    wuxm::Brush ourFill{nullptr};
    unsigned long long ourKey = 0;
};

static std::vector<Tracked> g_items;
static Cfg g_cfg;

static void ApplyOne(Tracked& t, const Cfg& c) {
    auto r = t.rect.get();
    if (!r) return;
    if (!c.enabled) {
        t.ourFill = nullptr;
        if (!t.stroke && t.origFill && r.Fill() != t.origFill) r.Fill(t.origFill);
        if (r.Opacity() != t.origOpacity) r.Opacity(t.origOpacity);
        return;
    }
    if (t.stroke) {
        double want = c.stroke ? t.origOpacity : 0.0;
        if (r.Opacity() != want) r.Opacity(want);
        return;
    }
    if (c.tint != NO_TINT) {
        unsigned long long key = ((unsigned long long)c.tint << 32) | c.tint2;
        if (!t.ourFill || t.ourKey != key) {
            t.ourFill = MakeBrush(c.tint, c.tint2, true);
            t.ourKey = key;
        }
        if (r.Fill() != t.ourFill) r.Fill(t.ourFill);
    } else {
        t.ourFill = nullptr;
        if (t.origFill && r.Fill() != t.origFill) r.Fill(t.origFill);
    }
    double want = c.opacity / 100.0;
    if (r.Opacity() != want) r.Opacity(want);
}

// Windows puede reponer el valor original: se vuelve a imponer el nuestro.
static void Reassert(wux::DependencyObject const& sender) {
    std::lock_guard<std::recursive_mutex> l(g_lock);
    for (auto& t : g_items) {
        auto r = t.rect.get();
        if (r && r == sender) {
            try { ApplyOne(t, g_cfg); } catch (...) {}
            return;
        }
    }
}

// ------------------------------------------------------------------ menú Inicio
enum Role { R_BG, R_BG_GEN, R_OVERLAY, R_FILL, R_SHADOW, R_FRAME, R_SEARCH, R_REC, R_REC_WRAP };

struct Saved {
    wux::DependencyProperty dp{nullptr};
    WInspectable val{nullptr};
};

struct SmItem {
    winrt::weak_ref<wux::FrameworkElement> el;
    Role role = R_BG;
    DWORD tid = 0;
    std::vector<Saved> saved;
    wuxm::Brush ours{nullptr};
    unsigned long long ourKey = 0;
    bool mainFrame = false;      // StartSizingFrame: recibe la escala
    double origH = 0;            // alto original (el menú solo puede achicarse)
    wuxm::ScaleTransform scale{nullptr};
};

static std::vector<SmItem> g_sm;
static SmCfg g_smCfg;

static void Remember(SmItem& it, wux::DependencyObject const& t, wux::DependencyProperty const& dp) {
    for (auto& s : it.saved)
        if (s.dp == dp) return;
    it.saved.push_back({dp, t.ReadLocalValue(dp)});
}

static void Restore(SmItem& it, wux::DependencyObject const& t, wux::DependencyProperty const& dp) {
    for (auto it2 = it.saved.begin(); it2 != it.saved.end(); ++it2) {
        if (it2->dp != dp) continue;
        if (it2->val == wux::DependencyProperty::UnsetValue()) t.ClearValue(dp);
        else t.SetValue(dp, it2->val);
        it.saved.erase(it2);
        return;
    }
}

static void SetOpacity(SmItem& it, wux::UIElement const& e, double v) {
    if (std::fabs(e.Opacity() - v) < 0.001) return;
    Remember(it, e, wux::UIElement::OpacityProperty());
    e.Opacity(v);
}

static void SetVisible(SmItem& it, wux::UIElement const& e, bool vis) {
    auto want = vis ? wux::Visibility::Visible : wux::Visibility::Collapsed;
    if (e.Visibility() == want) return;
    Remember(it, e, wux::UIElement::VisibilityProperty());
    e.Visibility(want);
}

static void SetCorner(SmItem& it, wuxc::Border const& b, double r) {
    auto cur = b.CornerRadius();
    if (cur.TopLeft == r && cur.TopRight == r && cur.BottomLeft == r && cur.BottomRight == r) return;
    Remember(it, b, wuxc::Border::CornerRadiusProperty());
    b.CornerRadius({r, r, r, r});
}

static void ApplySm(SmItem& it, const SmCfg& c) {
    auto e = it.el.get();
    if (!e) return;
    wux::DependencyObject target = e;
    if (it.role == R_REC_WRAP) {
        target = wuxm::VisualTreeHelper::GetParent(e);
        if (!target) return;
    }
    auto ue = target.try_as<wux::UIElement>();
    auto border = target.try_as<wuxc::Border>();
    if (!c.enabled) {
        auto props = it.saved;
        for (auto& s : props) Restore(it, target, s.dp);
        it.ours = nullptr;
        return;
    }
    bool bgChange = c.tint != NO_TINT || c.opacity < 100;
    switch (it.role) {
    case R_BG:
        if (!border) break;
        if (c.tint != NO_TINT) {
            unsigned long long key = ((unsigned long long)c.tint << 32) | c.tint2;
            if (!it.ours || it.ourKey != key) {
                it.ours = MakeBrush(c.tint, c.tint2, false);
                it.ourKey = key;
            }
            if (border.Background() != it.ours) {
                Remember(it, border, wuxc::Border::BackgroundProperty());
                border.Background(it.ours);
            }
        } else {
            it.ours = nullptr;
            Restore(it, border, wuxc::Border::BackgroundProperty());
        }
        if (c.opacity < 100) SetOpacity(it, border, c.opacity / 100.0);
        else Restore(it, border, wux::UIElement::OpacityProperty());
        if (c.corner != NO_TINT) SetCorner(it, border, (double)c.corner);
        else Restore(it, border, wuxc::Border::CornerRadiusProperty());
        if (!c.border) {
            if (border.BorderThickness() != wux::Thickness{0, 0, 0, 0}) {
                Remember(it, border, wuxc::Border::BorderThicknessProperty());
                border.BorderThickness({0, 0, 0, 0});
            }
        } else {
            Restore(it, border, wuxc::Border::BorderThicknessProperty());
        }
        break;
    case R_BG_GEN: {
        // Otras superficies (carpeta abierta, Todas las apps...): solo el pincel,
        // nunca la opacidad, para no ocultar su contenido.
        wuxm::Brush cur{nullptr};
        auto panel = target.try_as<wuxc::Panel>();
        if (border) cur = border.Background();
        else if (panel) cur = panel.Background();
        else break;
        auto dp = border ? wuxc::Border::BackgroundProperty() : wuxc::Panel::BackgroundProperty();
        if (!bgChange) {
            it.ours = nullptr;
            Restore(it, target, dp);
            break;
        }
        DWORD tint = c.tint != NO_TINT ? c.tint : 0x202020;
        uint8_t alpha = (uint8_t)((c.opacity * 255 + 50) / 100);
        unsigned long long key = ((unsigned long long)tint << 32) ^ c.tint2 ^ ((unsigned long long)alpha << 56);
        if (!it.ours || it.ourKey != key) {
            it.ours = MakeBrush(tint, c.tint2, false, alpha);
            it.ourKey = key;
        }
        if (cur != it.ours) {
            Remember(it, target, dp);
            target.SetValue(dp, it.ours);
        }
        break;
    }
    case R_OVERLAY:
    case R_FILL:
        if (ue) {
            if (bgChange) SetOpacity(it, ue, 0.0);
            else Restore(it, ue, wux::UIElement::OpacityProperty());
        }
        if (border) {
            if (c.corner != NO_TINT) SetCorner(it, border, (double)c.corner);
            else Restore(it, border, wuxc::Border::CornerRadiusProperty());
        }
        break;
    case R_SHADOW:
        if (ue) {
            if (!c.shadow) SetOpacity(it, ue, 0.0);
            else Restore(it, ue, wux::UIElement::OpacityProperty());
        }
        if (border) {
            if (c.corner != NO_TINT) SetCorner(it, border, (double)c.corner);
            else Restore(it, border, wuxc::Border::CornerRadiusProperty());
        }
        break;
    case R_FRAME: {
        auto fe = target.as<wux::FrameworkElement>();
        if (it.origH == 0 && fe.ActualHeight() > 0 && it.saved.empty()) it.origH = fe.ActualHeight();
        // La ventana del menú tiene el alto original: más alto se recortaría.
        double h = c.height ? (double)c.height : 0;
        if (it.origH > 0 && h > it.origH) h = it.origH;
        if (h > 0) {
            if (fe.Height() != h) {
                Remember(it, fe, wux::FrameworkElement::HeightProperty());
                fe.Height(h);
            }
        } else {
            Restore(it, fe, wux::FrameworkElement::HeightProperty());
        }
        if (it.mainFrame) {
            // Tamaño: se comprime todo el menú (escala uniforme) anclado abajo al centro.
            double k = (c.scale > 0 && c.scale < 100) ? c.scale / 100.0 : 1.0;
            if (k < 1.0) {
                if (!it.scale) it.scale = wuxm::ScaleTransform();
                if (fe.RenderTransform() != it.scale) {
                    Remember(it, fe, wux::UIElement::RenderTransformProperty());
                    Remember(it, fe, wux::UIElement::RenderTransformOriginProperty());
                    fe.RenderTransformOrigin({0.5f, 1.0f});
                    fe.RenderTransform(it.scale);
                }
                if (it.scale.ScaleX() != k) {
                    it.scale.ScaleX(k);
                    it.scale.ScaleY(k);
                }
            } else {
                Restore(it, fe, wux::UIElement::RenderTransformProperty());
                Restore(it, fe, wux::UIElement::RenderTransformOriginProperty());
            }
        }
        break;
    }
    case R_SEARCH:
        if (ue) {
            if (!c.search) SetVisible(it, ue, false);
            else Restore(it, ue, wux::UIElement::VisibilityProperty());
        }
        break;
    case R_REC:
    case R_REC_WRAP:
        if (ue) {
            if (!c.rec) SetVisible(it, ue, false);
            else Restore(it, ue, wux::UIElement::VisibilityProperty());
        }
        break;
    }
}

static void ReassertSm(wux::DependencyObject const& sender) {
    std::lock_guard<std::recursive_mutex> l(g_lock);
    for (auto& it : g_sm) {
        auto e = it.el.get();
        if (e && e == sender) {
            try { ApplySm(it, g_smCfg); } catch (...) {}
            return;
        }
    }
}

static bool SmRole(std::wstring_view type, std::wstring_view name, Role& role) {
    struct M { const wchar_t* type; const wchar_t* name; Role role; };
    static const M map[] = {
        {L"Windows.UI.Xaml.Controls.Border", L"AcrylicBorder", R_BG},
        {L"Windows.UI.Xaml.Controls.Border", L"AcrylicOverlay", R_OVERLAY},
        {L"Windows.UI.Xaml.Controls.Border", L"BackgroundColorOverlay", R_FILL},
        {L"Windows.UI.Xaml.Controls.Border", L"FallbackFullBleedBackground", R_FILL},
        {L"Windows.UI.Xaml.Controls.Border", L"DropShadow", R_SHADOW},
        {L"StartDocked.StartSizingFrame", L"", R_FRAME},
        {L"StartDocked.StartSizingFramePanel", L"", R_FRAME},
        {L"StartDocked.LauncherFrame", L"", R_FRAME},
        {L"StartDocked.SearchBoxToggleButton", L"StartMenuSearchBox", R_SEARCH},
        {L"Windows.UI.Xaml.Controls.Grid", L"TopLevelSuggestionsListHeader", R_REC},
        {L"Windows.UI.Xaml.Controls.Grid", L"TopLevelSuggestionsContainer", R_REC_WRAP},
        {L"Windows.UI.Xaml.Controls.Grid", L"NoTopLevelSuggestionsText", R_REC},
        {L"Windows.UI.Xaml.Controls.Grid", L"ShowMoreSuggestions", R_REC},
    };
    for (auto& m : map) {
        if (type == m.type && name == m.name) {
            role = m.role;
            return true;
        }
    }
    return false;
}

// ------------------------------------------------------------------ ejecución en el hilo de interfaz
static UINT g_runMsg = 0;
static const WPARAM RUN_TAG = 0x57535442;
struct RunCtx { void (*fn)(void*); void* p; };

static LRESULT CALLBACK RunHook(int code, WPARAM w, LPARAM l) {
    if (code == HC_ACTION) {
        auto cwp = reinterpret_cast<CWPSTRUCT*>(l);
        if (cwp->message == g_runMsg && cwp->wParam == RUN_TAG) {
            auto ctx = reinterpret_cast<RunCtx*>(cwp->lParam);
            ctx->fn(ctx->p);
        }
    }
    return CallNextHookEx(nullptr, code, w, l);
}

static BOOL CALLBACK FirstWnd(HWND h, LPARAM lp) {
    *reinterpret_cast<HWND*>(lp) = h;
    return FALSE;
}

static void RunOnThread(DWORD tid, void (*fn)(void*), void* p) {
    if (tid == GetCurrentThreadId()) { fn(p); return; }
    HWND h = nullptr;
    EnumThreadWindows(tid, FirstWnd, reinterpret_cast<LPARAM>(&h));
    if (!h) return;
    HHOOK hook = SetWindowsHookExW(WH_CALLWNDPROC, RunHook, nullptr, tid);
    if (!hook) return;
    RunCtx ctx{fn, p};
    SendMessageW(h, g_runMsg, RUN_TAG, reinterpret_cast<LPARAM>(&ctx));
    UnhookWindowsHookEx(hook);
}

struct ApplyParam { DWORD tid; };

static void ApplyThreadItems(void* pp) {
    DWORD tid = static_cast<ApplyParam*>(pp)->tid;
    std::lock_guard<std::recursive_mutex> l(g_lock);
    for (auto& t : g_items)
        if (t.tid == tid) { try { ApplyOne(t, g_cfg); } catch (...) {} }
    // R_REC_WRAP depende del padre: se aplica después del resto
    for (int pass = 0; pass < 2; ++pass)
        for (auto& it : g_sm)
            if (it.tid == tid && ((it.role == R_REC_WRAP) == (pass == 1))) { try { ApplySm(it, g_smCfg); } catch (...) {} }
}

static void ApplyAll() {
    std::vector<DWORD> tids;
    {
        std::lock_guard<std::recursive_mutex> l(g_lock);
        g_cfg = ReadCfg();
        g_smCfg = ReadSmCfg();
        for (auto& t : g_items)
            if (std::find(tids.begin(), tids.end(), t.tid) == tids.end()) tids.push_back(t.tid);
        for (auto& t : g_sm)
            if (std::find(tids.begin(), tids.end(), t.tid) == tids.end()) tids.push_back(t.tid);
    }
    for (DWORD tid : tids) {
        ApplyParam p{tid};
        RunOnThread(tid, ApplyThreadItems, &p);
    }
}

static DWORD WINAPI RegWatchThread(LPVOID) {
    HKEY k = nullptr;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, REG_KEY, 0, KEY_NOTIFY | KEY_READ, &k) != ERROR_SUCCESS) return 0;
    HANDLE ev = CreateEventW(nullptr, FALSE, FALSE, nullptr);
    while (ev) {
        if (RegNotifyChangeKeyValue(k, FALSE, REG_NOTIFY_CHANGE_LAST_SET | REG_NOTIFY_CHANGE_NAME, ev, TRUE) != ERROR_SUCCESS)
            break;
        WaitForSingleObject(ev, INFINITE);
        Sleep(80);
        ApplyAll();
        DWORD dummy = 0;
        if (RegQueryInfoKeyW(k, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, &dummy, nullptr, nullptr, nullptr, nullptr) != ERROR_SUCCESS)
            break;  // clave borrada (restauración)
    }
    if (ev) CloseHandle(ev);
    RegCloseKey(k);
    return 0;
}

// ------------------------------------------------------------------ observador del árbol XAML
struct Watcher : winrt::implements<Watcher, IVisualTreeServiceCallback2, winrt::non_agile> {
    winrt::com_ptr<IXamlDiagnostics> diag;

    explicit Watcher(winrt::com_ptr<IUnknown> const& site) : diag(site.as<IXamlDiagnostics>()) {}

    void Start() {
        AddRef();
        HANDLE th = CreateThread(nullptr, 0, [](LPVOID p) -> DWORD {
            auto self = static_cast<Watcher*>(p);
            try {
                self->diag.as<IVisualTreeService3>()->AdviseVisualTreeChange(self);
            } catch (...) {}
            self->Release();
            return 0;
        }, this, 0, nullptr);
        if (th) CloseHandle(th); else Release();
    }

    static bool InTaskbar(wux::DependencyObject const& el) {
        wux::DependencyObject p = el;
        for (int i = 0; i < 10; ++i) {
            p = wuxm::VisualTreeHelper::GetParent(p);
            if (!p) return i == 0;  // todavía sin padre: el Explorador solo tiene XAML de la barra
            if (std::wstring_view(winrt::get_class_name(p)).starts_with(L"Taskbar.")) return true;
        }
        return false;
    }

    winrt::com_ptr<::IInspectable> Inspect(InstanceHandle h) {
        winrt::com_ptr<::IInspectable> insp;
        if (FAILED(diag->GetIInspectableFromHandle(h, insp.put()))) return nullptr;
        return insp;
    }

    void AddStart(VisualElement const& element, std::wstring_view type, std::wstring_view name) {
        Role role = R_BG;
        bool known = SmRole(type, name, role);
        bool maybeBg = !known && (type == L"Windows.UI.Xaml.Controls.Border" || type == L"Windows.UI.Xaml.Controls.Grid");
        if (!known && !maybeBg) return;
        auto insp = Inspect(element.Handle);
        if (!insp) return;
        auto fe = insp.try_as<wux::FrameworkElement>();
        if (!fe) return;
        if (maybeBg) {
            wuxm::Brush bg{nullptr};
            if (auto b = fe.try_as<wuxc::Border>()) bg = b.Background();
            else if (auto pnl = fe.try_as<wuxc::Panel>()) bg = pnl.Background();
            if (!bg || !bg.try_as<wuxm::AcrylicBrush>()) return;
            role = R_BG_GEN;
        }
        std::lock_guard<std::recursive_mutex> l(g_lock);
        g_sm.erase(std::remove_if(g_sm.begin(), g_sm.end(), [](SmItem const& t) { return !t.el.get(); }), g_sm.end());
        for (auto& t : g_sm)
            if (t.el.get() == fe) return;
        SmItem it;
        it.el = winrt::make_weak(fe);
        it.role = role;
        it.mainFrame = type == L"StartDocked.StartSizingFrame";
        it.tid = GetCurrentThreadId();
        g_sm.push_back(it);
        ApplySm(g_sm.back(), g_smCfg);
        if (role == R_REC_WRAP) return;
        auto cb = [](wux::DependencyObject const& s, wux::DependencyProperty const&) { ReassertSm(s); };
        fe.RegisterPropertyChangedCallback(wux::UIElement::OpacityProperty(), cb);
        fe.RegisterPropertyChangedCallback(wux::UIElement::VisibilityProperty(), cb);
        if (role == R_FRAME) {
            fe.RegisterPropertyChangedCallback(wux::FrameworkElement::HeightProperty(), cb);
            fe.RegisterPropertyChangedCallback(wux::UIElement::RenderTransformProperty(), cb);
        }
        if (role == R_BG_GEN && fe.try_as<wuxc::Panel>())
            fe.RegisterPropertyChangedCallback(wuxc::Panel::BackgroundProperty(), cb);
        if (fe.try_as<wuxc::Border>()) {
            fe.RegisterPropertyChangedCallback(wuxc::Border::BackgroundProperty(), cb);
            fe.RegisterPropertyChangedCallback(wuxc::Border::CornerRadiusProperty(), cb);
            fe.RegisterPropertyChangedCallback(wuxc::Border::BorderThicknessProperty(), cb);
        }
    }

    void AddTaskbar(VisualElement const& element, std::wstring_view type, std::wstring_view name) {
        if (type != L"Windows.UI.Xaml.Shapes.Rectangle") return;
        bool stroke = name == L"BackgroundStroke";
        if (!stroke && name != L"BackgroundFill") return;
        auto insp = Inspect(element.Handle);
        if (!insp) return;
        auto rect = insp.try_as<wux::Shapes::Rectangle>();
        if (!rect || !InTaskbar(rect)) return;

        std::lock_guard<std::recursive_mutex> l(g_lock);
        for (auto& t : g_items)
            if (t.rect.get() == rect) return;
        g_items.erase(std::remove_if(g_items.begin(), g_items.end(),
                                     [](Tracked const& t) { return !t.rect.get(); }),
                      g_items.end());
        Tracked t;
        t.rect = winrt::make_weak(rect);
        t.stroke = stroke;
        t.tid = GetCurrentThreadId();
        t.origOpacity = rect.Opacity();
        if (!stroke) t.origFill = rect.Fill();
        g_items.push_back(t);
        ApplyOne(g_items.back(), g_cfg);

        auto cb = [](wux::DependencyObject const& s, wux::DependencyProperty const&) { Reassert(s); };
        rect.RegisterPropertyChangedCallback(wux::UIElement::OpacityProperty(), cb);
        if (!stroke) rect.RegisterPropertyChangedCallback(wux::Shapes::Shape::FillProperty(), cb);
    }

    HRESULT STDMETHODCALLTYPE OnVisualTreeChange(ParentChildRelation, VisualElement element,
                                                 VisualMutationType mutationType) override {
        try {
            if (mutationType != Add || !element.Type) return S_OK;
            std::wstring_view type(element.Type, SysStringLen(element.Type));
            std::wstring_view name;
            if (element.Name) name = std::wstring_view(element.Name, SysStringLen(element.Name));
            if (g_inStart) AddStart(element, type, name);
            else AddTaskbar(element, type, name);
        } catch (...) {}
        return S_OK;
    }

    HRESULT STDMETHODCALLTYPE OnElementStateChanged(InstanceHandle, VisualElementState, LPCWSTR) override {
        return S_OK;
    }
};

static winrt::com_ptr<Watcher> g_watcher;

struct Tap : winrt::implements<Tap, IObjectWithSite, winrt::non_agile> {
    winrt::com_ptr<IUnknown> site;

    HRESULT STDMETHODCALLTYPE SetSite(IUnknown* s) override {
        site.copy_from(s);
        if (!s || g_watcher) return S_OK;
        // Una sola instancia por proceso.
        wchar_t name[64];
        swprintf_s(name, L"Local\\WinStylerTap_%lu", GetCurrentProcessId());
        HANDLE m = CreateMutexW(nullptr, FALSE, name);
        if (m && GetLastError() == ERROR_ALREADY_EXISTS) return S_OK;  // el mutex queda abierto a propósito
        HMODULE self = nullptr;
        GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
                           reinterpret_cast<LPCWSTR>(&CLSID_WsTap), &self);
        wchar_t exe[MAX_PATH] = L"";
        GetModuleFileNameW(nullptr, exe, MAX_PATH);
        g_inStart = std::wstring_view(exe).find(L"StartMenuExperienceHost") != std::wstring_view::npos;
        try {
            {
                std::lock_guard<std::recursive_mutex> l(g_lock);
                g_cfg = ReadCfg();
                g_smCfg = ReadSmCfg();
            }
            g_watcher = winrt::make_self<Watcher>(site);
            g_watcher->Start();
            HANDLE th = CreateThread(nullptr, 0, RegWatchThread, nullptr, 0, nullptr);
            if (th) CloseHandle(th);
        } catch (...) {}
        return S_OK;
    }

    HRESULT STDMETHODCALLTYPE GetSite(REFIID riid, void** ppv) override {
        if (!ppv) return E_POINTER;
        *ppv = nullptr;
        return site ? site->QueryInterface(riid, ppv) : E_FAIL;
    }
};

struct Factory : winrt::implements<Factory, IClassFactory> {
    HRESULT STDMETHODCALLTYPE CreateInstance(IUnknown* outer, REFIID riid, void** ppv) override {
        if (!ppv) return E_POINTER;
        *ppv = nullptr;
        if (outer) return CLASS_E_NOAGGREGATION;
        try { return winrt::make_self<Tap>()->QueryInterface(riid, ppv); }
        catch (...) { return winrt::to_hresult(); }
    }
    HRESULT STDMETHODCALLTYPE LockServer(BOOL) override { return S_OK; }
};

STDAPI DllGetClassObject(REFCLSID clsid, REFIID riid, LPVOID* ppv) {
    if (!ppv) return E_POINTER;
    *ppv = nullptr;
    if (clsid != CLSID_WsTap) return CLASS_E_CLASSNOTAVAILABLE;
    try { return winrt::make_self<Factory>()->QueryInterface(riid, ppv); }
    catch (...) { return winrt::to_hresult(); }
}

STDAPI DllCanUnloadNow() { return S_FALSE; }

// ------------------------------------------------------------------ proceso residente
static DWORD OsBuild() {
    RTL_OSVERSIONINFOW vi{sizeof(vi)};
    using Fn = LONG(WINAPI*)(PRTL_OSVERSIONINFOW);
    auto fn = reinterpret_cast<Fn>(GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "RtlGetVersion"));
    if (fn && fn(&vi) == 0) return vi.dwBuildNumber;
    return 0;
}

static bool g_win11 = true;

static HRESULT Inject(DWORD pid) {
    using Ixde = HRESULT(WINAPI*)(LPCWSTR, DWORD, LPCWSTR, LPCWSTR, CLSID, LPCWSTR);
    static Ixde ixde = nullptr;
    if (!ixde) {
        HMODULE wuxDll = LoadLibraryExW(L"Windows.UI.Xaml.dll", nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
        if (!wuxDll) return HRESULT_FROM_WIN32(GetLastError());
        ixde = reinterpret_cast<Ixde>(GetProcAddress(wuxDll, "InitializeXamlDiagnosticsEx"));
        if (!ixde) return E_NOINTERFACE;
    }
    wchar_t path[MAX_PATH];
    GetModuleFileNameW(g_module, path, MAX_PATH);
    HRESULT hr = ixde(L"VisualDiagConnection1", pid, nullptr, path, CLSID_WsTap, nullptr);
    if (hr == E_INVALIDARG) hr = ixde(L"VisualDiagConnection1", pid, L"", path, CLSID_WsTap, nullptr);
    return hr;
}

// El menú Inicio corre en un AppContainer: necesita permiso de lectura sobre la DLL,
// su carpeta y la clave de configuración.
static void GrantAppPackages(const wchar_t* obj, SE_OBJECT_TYPE type, DWORD access) {
    PSID sid = nullptr;
    if (!ConvertStringSidToSidW(L"S-1-15-2-1", &sid)) return;
    PACL oldAcl = nullptr, newAcl = nullptr;
    PSECURITY_DESCRIPTOR sd = nullptr;
    if (GetNamedSecurityInfoW(obj, type, DACL_SECURITY_INFORMATION, nullptr, nullptr, &oldAcl, nullptr, &sd) == ERROR_SUCCESS) {
        EXPLICIT_ACCESSW ea{};
        ea.grfAccessPermissions = access;
        ea.grfAccessMode = GRANT_ACCESS;
        ea.grfInheritance = NO_INHERITANCE;
        ea.Trustee.TrusteeForm = TRUSTEE_IS_SID;
        ea.Trustee.TrusteeType = TRUSTEE_IS_WELL_KNOWN_GROUP;
        ea.Trustee.ptstrName = static_cast<LPWSTR>(sid);
        if (SetEntriesInAclW(1, &ea, oldAcl, &newAcl) == ERROR_SUCCESS) {
            SetNamedSecurityInfoW(const_cast<LPWSTR>(obj), type, DACL_SECURITY_INFORMATION, nullptr, nullptr, newAcl, nullptr);
            LocalFree(newAcl);
        }
        LocalFree(sd);
    }
    LocalFree(sid);
}

static void GrantAll() {
    wchar_t path[MAX_PATH];
    GetModuleFileNameW(g_module, path, MAX_PATH);
    GrantAppPackages(path, SE_FILE_OBJECT, GENERIC_READ | GENERIC_EXECUTE);
    wchar_t dir[MAX_PATH];
    wcscpy_s(dir, path);
    if (wchar_t* s = wcsrchr(dir, L'\\')) *s = 0;
    GrantAppPackages(dir, SE_FILE_OBJECT, GENERIC_READ | GENERIC_EXECUTE);
    GrantAppPackages(L"CURRENT_USER\\Software\\WinStyler", SE_REGISTRY_KEY, KEY_READ);
}

struct Target {
    DWORD injected = 0;
    volatile LONG busy = 0;
    DWORD pid = 0;
};
static Target g_tbTarget, g_smTarget;

static DWORD WINAPI InjectThread(LPVOID p) {
    auto t = static_cast<Target*>(p);
    // Si el proceso está suspendido (menú cerrado) la llamada espera a que se reanude.
    if (SUCCEEDED(Inject(t->pid))) t->injected = t->pid;
    InterlockedExchange(&t->busy, 0);
    return 0;
}

static void Ensure(Target& t, DWORD pid) {
    if (!pid || pid == t.injected) return;
    if (InterlockedCompareExchange(&t.busy, 1, 0) != 0) return;
    t.pid = pid;
    HANDLE th = CreateThread(nullptr, 0, InjectThread, &t, 0, nullptr);
    if (th) CloseHandle(th); else InterlockedExchange(&t.busy, 0);
}

static DWORD FindProcess(const wchar_t* exe) {
    DWORD session = 0, found = 0;
    ProcessIdToSessionId(GetCurrentProcessId(), &session);
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) return 0;
    PROCESSENTRY32W pe{sizeof(pe)};
    for (BOOL ok = Process32FirstW(snap, &pe); ok; ok = Process32NextW(snap, &pe)) {
        DWORD s = 0;
        if (_wcsicmp(pe.szExeFile, exe) == 0 && ProcessIdToSessionId(pe.th32ProcessID, &s) && s == session) {
            found = pe.th32ProcessID;
            break;
        }
    }
    CloseHandle(snap);
    return found;
}

struct AccentPolicy { int state; int flags; DWORD color; int anim; };
struct WinCompAttrData { int attr; PVOID data; SIZE_T size; };
using SwcaFn = BOOL(WINAPI*)(HWND, WinCompAttrData*);

static BOOL CALLBACK Win10Apply(HWND h, LPARAM lp) {
    wchar_t cls[64];
    if (!GetClassNameW(h, cls, 64)) return TRUE;
    if (wcscmp(cls, L"Shell_TrayWnd") && wcscmp(cls, L"Shell_SecondaryTrayWnd")) return TRUE;
    auto ap = reinterpret_cast<AccentPolicy*>(lp);
    static SwcaFn swca = reinterpret_cast<SwcaFn>(GetProcAddress(GetModuleHandleW(L"user32.dll"), "SetWindowCompositionAttribute"));
    if (swca) {
        WinCompAttrData d{19, ap, sizeof(*ap)};
        swca(h, &d);
    }
    return TRUE;
}

static void Win10Tick(const Cfg& c, bool off) {
    AccentPolicy ap{0, 0, 0, 0};
    if (!off && c.enabled) {
        DWORD a = (c.opacity * 255 + 50) / 100;
        DWORD rgb = c.tint == NO_TINT ? 0 : c.tint;
        DWORD abgr = (a << 24) | ((rgb & 0xFF) << 16) | (rgb & 0xFF00) | ((rgb >> 16) & 0xFF);
        ap = AccentPolicy{2, 2, abgr, 0};
    }
    EnumWindows(Win10Apply, reinterpret_cast<LPARAM>(&ap));
}

// Pide a todos los programas que vuelvan a poner su ícono en la bandeja (Steam, Discord...).
// Es el mismo aviso que manda Windows cuando arranca la barra; no cierra ni cambia nada.
static void RefreshTrayIcons() {
    static const UINT msg = RegisterWindowMessageW(L"TaskbarCreated");
    if (msg) PostMessageW(HWND_BROADCAST, msg, 0, 0);
}

static DWORD g_trayNotified = 0;

static LRESULT CALLBACK KeepProc(HWND h, UINT m, WPARAM w, LPARAM l) {
    if (m == WM_TIMER && w == 2) {
        KillTimer(h, 2);
        RefreshTrayIcons();
        return 0;
    }
    if (m == WM_TIMER) {
        Cfg c = ReadCfg();
        bool sm = ReadSmCfg().enabled != 0;
        if (!c.enabled && !sm) {
            if (!g_win11) Win10Tick(c, true);
            PostQuitMessage(0);
            return 0;
        }
        if (!g_win11) {
            Win10Tick(c, false);
            return 0;
        }
        if (w == 1) {
            if (c.enabled) {
                HWND tray = FindWindowW(L"Shell_TrayWnd", nullptr);
                DWORD pid = 0;
                if (tray) GetWindowThreadProcessId(tray, &pid);
                Ensure(g_tbTarget, pid);
                // Barra nueva (inicio de sesión, reinicio o cierre inesperado del Explorador):
                // los íconos que se registraron mientras arrancaba se pierden; se recuperan.
                if (g_tbTarget.injected && g_tbTarget.injected != g_trayNotified) {
                    g_trayNotified = g_tbTarget.injected;
                    SetTimer(h, 2, 4000, nullptr);
                }
            }
            if (sm) Ensure(g_smTarget, FindProcess(L"StartMenuExperienceHost.exe"));
        }
        return 0;
    }
    return DefWindowProcW(h, m, w, l);
}

extern "C" void CALLBACK Keep(HWND, HINSTANCE, LPSTR, int) {
    HANDLE mtx = CreateMutexW(nullptr, TRUE, L"Local\\WinStylerTBKeeper");
    if (!mtx || GetLastError() == ERROR_ALREADY_EXISTS) return;
    HANDLE stop = CreateEventW(nullptr, TRUE, FALSE, L"Local\\WinStylerTBStop");
    if (stop) ResetEvent(stop);
    g_win11 = OsBuild() >= 22000;
    if (g_win11) GrantAll();

    WNDCLASSW wc{};
    wc.lpfnWndProc = KeepProc;
    wc.hInstance = g_module;
    wc.lpszClassName = L"WinStylerTBKeeper";
    RegisterClassW(&wc);
    HWND h = CreateWindowExW(WS_EX_TOOLWINDOW, wc.lpszClassName, L"", WS_POPUP, 0, 0, 0, 0, nullptr, nullptr, g_module, nullptr);
    SetTimer(h, 1, g_win11 ? 2000 : 40, nullptr);
    PostMessageW(h, WM_TIMER, 1, 0);

    bool run = true;
    while (run) {
        DWORD r = MsgWaitForMultipleObjects(stop ? 1 : 0, &stop, FALSE, INFINITE, QS_ALLINPUT);
        if (stop && r == WAIT_OBJECT_0) {
            if (!g_win11) Win10Tick(ReadCfg(), true);
            break;
        }
        MSG msg;
        while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) {
            if (msg.message == WM_QUIT) { run = false; break; }
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }
    if (h) DestroyWindow(h);
    if (stop) CloseHandle(stop);
    ReleaseMutex(mtx);
    CloseHandle(mtx);
    // Los hilos de inyección pueden seguir esperando un proceso suspendido.
    ExitProcess(0);
}

BOOL APIENTRY DllMain(HMODULE mod, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_module = mod;
        g_runMsg = RegisterWindowMessageW(L"WinStyler_RunOnThread");
        DisableThreadLibraryCalls(mod);
    }
    return TRUE;
}
