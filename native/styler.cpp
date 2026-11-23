// styler.cpp - motor genérico de estilos XAML (ver styler.h).
//
// Formato de styles.wss (lo genera WinStyler, UTF-8, una entrada por línea):
//   @explorer | @start                      proceso al que aplican las reglas siguientes
//   T<TAB>Tipo#Nombre[Prop=Valor]@Grupo > ...  objetivo (cadena de padres directos)
//   S<TAB>Propiedad<TAB>Estado<TAB>v|x<TAB>Valor  v = valor de texto, x = valor XAML
// El estado (vacío = siempre) es un estado visual del grupo marcado con @ en el objetivo.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#undef GetCurrentTime
#include <winrt/base.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.UI.Xaml.h>
#include <winrt/Windows.UI.Xaml.Automation.h>
#include <winrt/Windows.UI.Xaml.Controls.h>
#include <winrt/Windows.UI.Xaml.Controls.Primitives.h>
#include <winrt/Windows.UI.Xaml.Markup.h>
#include <winrt/Windows.UI.Xaml.Media.h>
#include <winrt/Windows.UI.Xaml.Shapes.h>
#include <list>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <vector>
#include <cstdio>
#include "styler.h"

namespace wux = winrt::Windows::UI::Xaml;
namespace wuxc = winrt::Windows::UI::Xaml::Controls;
using WInspectable = winrt::Windows::Foundation::IInspectable;

namespace {

struct Seg {
    std::wstring type, name, group;
    bool hasGroup = false;
    std::vector<std::pair<std::wstring, std::wstring>> filters;
};

struct StyleSetter {
    std::wstring prop, state, value;
    bool xaml = false;
};

struct Rule {
    std::vector<Seg> segs;
    std::vector<StyleSetter> setters;
    int groupSeg = -1;
};

using RuleSet = std::vector<Rule>;

HMODULE g_mod = nullptr;
bool g_start = false;
std::mutex g_fileLock;
std::shared_ptr<const RuleSet> g_rules = std::make_shared<RuleSet>();
FILETIME g_loadedTime{};
bool g_inSet = false;
bool g_dump = false;  // inspector: HKCU\Software\WinStyler\DumpTree = 1

// Inspector de elementos: anota cada elemento con sus padres en %TEMP%\winstyler_tree.txt
// (en el menú Inicio, la carpeta temporal de su paquete). Sirve para escribir mods.
void DumpElement(wux::FrameworkElement const& fe) {
    static std::mutex m;
    std::wstring line;
    wux::DependencyObject cur = fe;
    for (int i = 0; i < 8 && cur; ++i) {
        auto f = cur.try_as<wux::FrameworkElement>();
        if (!f) break;
        if (i) line += L" < ";
        line += winrt::get_class_name(f);
        std::wstring n(f.Name());
        if (!n.empty()) line += L"#" + n;
        cur = wux::Media::VisualTreeHelper::GetParent(cur);
    }
    line += L"\n";
    wchar_t path[MAX_PATH];
    GetTempPathW(MAX_PATH, path);
    wcscat_s(path, L"winstyler_tree.txt");
    std::lock_guard<std::mutex> l(m);
    if (FILE* f = _wfsopen(path, L"a, ccs=UTF-8", 0x40)) {
        fputws(line.c_str(), f);
        fclose(f);
    }
}

struct Prop {
    std::wstring name;
    wux::DependencyProperty dp{nullptr};
    WInspectable orig{nullptr};
    WInspectable cur{nullptr};
    int64_t cbToken = 0;
    bool saved = false;
    DWORD burstStart = 0;  // freno: si otro código pelea por la propiedad, se deja de insistir
    int burst = 0;
};

struct Applied {
    winrt::weak_ref<wux::FrameworkElement> el;
    const Rule* rule = nullptr;
    winrt::weak_ref<wux::VisualStateGroup> group;
    winrt::event_token token{};
    std::vector<Prop> props;
};

struct ThreadState {
    std::shared_ptr<const RuleSet> rules;
    std::vector<winrt::weak_ref<wux::FrameworkElement>> all;
    std::list<Applied> applied;
    size_t adds = 0;
};

std::mutex g_threadsLock;
std::map<DWORD, std::unique_ptr<ThreadState>> g_threads;

ThreadState& Me() {
    std::lock_guard<std::mutex> l(g_threadsLock);
    auto& p = g_threads[GetCurrentThreadId()];
    if (!p) p = std::make_unique<ThreadState>();
    return *p;
}

// ------------------------------------------------------------------ lectura del archivo
std::wstring StylesPath() {
    wchar_t path[MAX_PATH];
    GetModuleFileNameW(g_mod, path, MAX_PATH);
    if (wchar_t* s = wcsrchr(path, L'\\')) wcscpy_s(s + 1, MAX_PATH - (s + 1 - path), L"styles.wss");
    return path;
}

bool FileTime(FILETIME& ft) {
    WIN32_FILE_ATTRIBUTE_DATA d;
    if (!GetFileAttributesExW(StylesPath().c_str(), GetFileExInfoStandard, &d)) return false;
    ft = d.ftLastWriteTime;
    return true;
}

std::vector<std::wstring> Split(const std::wstring& s, wchar_t sep) {
    std::vector<std::wstring> out;
    size_t a = 0;
    for (;;) {
        size_t b = s.find(sep, a);
        out.push_back(s.substr(a, b == std::wstring::npos ? std::wstring::npos : b - a));
        if (b == std::wstring::npos) break;
        a = b + 1;
    }
    return out;
}

std::wstring Trim(const std::wstring& s) {
    size_t a = s.find_first_not_of(L" \t\r\n"), b = s.find_last_not_of(L" \t\r\n");
    return a == std::wstring::npos ? L"" : s.substr(a, b - a + 1);
}

Seg ParseSeg(std::wstring t) {
    Seg s;
    t = Trim(t);
    size_t at = std::wstring::npos;
    int depth = 0;
    for (size_t i = 0; i < t.size(); ++i) {
        if (t[i] == L'[') ++depth;
        else if (t[i] == L']') --depth;
        else if (t[i] == L'@' && depth == 0) { at = i; break; }
    }
    if (at != std::wstring::npos) {
        s.hasGroup = true;
        s.group = t.substr(at + 1);
        t = t.substr(0, at);
    }
    size_t lb;
    while ((lb = t.find(L'[')) != std::wstring::npos) {
        size_t rb = t.find(L']', lb);
        if (rb == std::wstring::npos) break;
        std::wstring f = t.substr(lb + 1, rb - lb - 1);
        size_t eq = f.find(L'=');
        if (eq != std::wstring::npos) s.filters.push_back({Trim(f.substr(0, eq)), Trim(f.substr(eq + 1))});
        t.erase(lb, rb - lb + 1);
    }
    size_t hash = t.find(L'#');
    if (hash != std::wstring::npos) {
        s.name = t.substr(hash + 1);
        t = t.substr(0, hash);
    }
    s.type = (t == L"*") ? L"" : t;
    return s;
}

std::shared_ptr<const RuleSet> LoadRules() {
    auto rules = std::make_shared<RuleSet>();
    HANDLE f = CreateFileW(StylesPath().c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                           nullptr, OPEN_EXISTING, 0, nullptr);
    if (f == INVALID_HANDLE_VALUE) return rules;
    std::string bytes;
    char buf[8192];
    DWORD n = 0;
    while (ReadFile(f, buf, sizeof(buf), &n, nullptr) && n) bytes.append(buf, n);
    CloseHandle(f);
    if (bytes.size() >= 3 && (unsigned char)bytes[0] == 0xEF) bytes.erase(0, 3);
    int wl = MultiByteToWideChar(CP_UTF8, 0, bytes.data(), (int)bytes.size(), nullptr, 0);
    std::wstring text(wl, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, bytes.data(), (int)bytes.size(), text.data(), wl);

    bool mine = false;
    const wchar_t* wanted = g_start ? L"@start" : L"@explorer";
    for (auto& raw : Split(text, L'\n')) {
        std::wstring line = raw;
        if (!line.empty() && line.back() == L'\r') line.pop_back();
        if (line.empty() || line[0] == L'#') continue;
        if (line[0] == L'@') { mine = Trim(line) == wanted; continue; }
        if (!mine) continue;
        auto parts = Split(line, L'\t');
        if (parts[0] == L"T" && parts.size() >= 2) {
            Rule r;
            for (auto& seg : Split(parts[1], L'>')) r.segs.push_back(ParseSeg(seg));
            for (int i = 0; i < (int)r.segs.size(); ++i)
                if (r.segs[i].hasGroup) r.groupSeg = i;  // el último grupo nombrado manda
            rules->push_back(std::move(r));
        } else if (parts[0] == L"S" && parts.size() >= 5 && !rules->empty()) {
            StyleSetter st;
            st.prop = parts[1];
            st.state = parts[2];
            st.xaml = parts[3] == L"x";
            // el valor puede contener tabulaciones: se une el resto
            st.value = parts[4];
            for (size_t i = 5; i < parts.size(); ++i) st.value += L"\t" + parts[i];
            rules->back().setters.push_back(std::move(st));
        }
    }
    return rules;
}

std::shared_ptr<const RuleSet> CurrentRules() {
    std::lock_guard<std::mutex> l(g_fileLock);
    FILETIME ft{};
    bool exists = FileTime(ft);
    if (!exists) ft = FILETIME{};
    if (CompareFileTime(&ft, &g_loadedTime) != 0) {
        g_rules = exists ? LoadRules() : std::make_shared<RuleSet>();
        g_loadedTime = ft;
    }
    return g_rules;
}

// ------------------------------------------------------------------ coincidencias
bool TypeMatches(wux::FrameworkElement const& fe, const std::wstring& type) {
    if (type.empty()) return true;
    std::wstring cls(winrt::get_class_name(fe));
    if (cls == type) return true;
    return cls.size() > type.size() && cls.compare(cls.size() - type.size(), type.size(), type) == 0 &&
           cls[cls.size() - type.size() - 1] == L'.';
}

bool FilterMatches(wux::FrameworkElement const& fe, const std::wstring& prop, const std::wstring& value) {
    try {
        if (prop == L"Name") return std::wstring(fe.Name()) == value;
        if (prop == L"AutomationProperties.AutomationId")
            return std::wstring(wux::Automation::AutomationProperties::GetAutomationId(fe)) == value;
        if (prop == L"AutomationProperties.Name")
            return std::wstring(wux::Automation::AutomationProperties::GetName(fe)) == value;
        if (prop == L"Text")
            if (auto tb = fe.try_as<wuxc::TextBlock>()) return std::wstring(tb.Text()) == value;
    } catch (...) {}
    return false;
}

bool SegMatches(wux::FrameworkElement const& fe, const Seg& s) {
    if (!TypeMatches(fe, s.type)) return false;
    if (!s.name.empty() && std::wstring(fe.Name()) != s.name) return false;
    for (auto& f : s.filters)
        if (!FilterMatches(fe, f.first, f.second)) return false;
    return true;
}

bool RuleMatches(wux::FrameworkElement const& fe, const Rule& r, wux::FrameworkElement& groupEl) {
    if (r.segs.empty()) return false;
    wux::DependencyObject cur = fe;
    for (int i = (int)r.segs.size() - 1; i >= 0; --i) {
        auto curFe = cur ? cur.try_as<wux::FrameworkElement>() : nullptr;
        if (!curFe || !SegMatches(curFe, r.segs[i])) return false;
        if (i == r.groupSeg) groupEl = curFe;
        if (i > 0) cur = wux::Media::VisualTreeHelper::GetParent(cur);
    }
    return true;
}

// ------------------------------------------------------------------ valores
std::wstring Esc(const std::wstring& s) {
    std::wstring o;
    for (wchar_t c : s) {
        switch (c) {
        case L'&': o += L"&amp;"; break;
        case L'<': o += L"&lt;"; break;
        case L'>': o += L"&gt;"; break;
        case L'"': o += L"&quot;"; break;
        default: o += c;
        }
    }
    return o;
}

// Tipos XAML conocidos de los que puede derivar el elemento, del más concreto al más general.
std::vector<const wchar_t*> TargetTypes(wux::FrameworkElement const& fe) {
    std::vector<const wchar_t*> t;
    if (fe.try_as<wux::Shapes::Rectangle>()) t.push_back(L"Rectangle");
    if (fe.try_as<wux::Shapes::Ellipse>()) t.push_back(L"Ellipse");
    if (fe.try_as<wux::Shapes::Path>()) t.push_back(L"Path");
    if (fe.try_as<wuxc::Border>()) t.push_back(L"Border");
    if (fe.try_as<wuxc::TextBlock>()) t.push_back(L"TextBlock");
    if (fe.try_as<wuxc::Grid>()) t.push_back(L"Grid");
    if (fe.try_as<wuxc::StackPanel>()) t.push_back(L"StackPanel");
    if (fe.try_as<wuxc::Canvas>()) t.push_back(L"Canvas");
    if (fe.try_as<wuxc::ContentPresenter>()) t.push_back(L"ContentPresenter");
    if (fe.try_as<wuxc::Image>()) t.push_back(L"Image");
    if (fe.try_as<wuxc::FontIcon>()) t.push_back(L"FontIcon");
    if (fe.try_as<wuxc::Primitives::ToggleButton>()) t.push_back(L"ToggleButton");
    if (fe.try_as<wuxc::Button>()) t.push_back(L"Button");
    if (fe.try_as<wuxc::ContentControl>()) t.push_back(L"ContentControl");
    if (fe.try_as<wuxc::ItemsControl>()) t.push_back(L"ItemsControl");
    if (fe.try_as<wuxc::Control>()) t.push_back(L"Control");
    t.push_back(L"FrameworkElement");
    return t;
}

bool MakeValue(wux::FrameworkElement const& fe, const StyleSetter& st, wux::DependencyProperty& dp, WInspectable& val) {
    static const std::wstring head =
        L"<Style xmlns=\"http://schemas.microsoft.com/winfx/2006/xaml/presentation\" "
        L"xmlns:x=\"http://schemas.microsoft.com/winfx/2006/xaml\" ";
    // Primero el tipo real del elemento (p. ej. Microsoft.UI.Xaml.Controls.ItemsRepeater con
    // xmlns "using:"), después los tipos XAML estándar de los que deriva.
    std::vector<std::wstring> types;
    std::wstring cls(winrt::get_class_name(fe));
    size_t dot = cls.rfind(L'.');
    if (dot != std::wstring::npos && cls.rfind(L"Windows.UI.Xaml.", 0) != 0)
        types.push_back(L"xmlns:t=\"using:" + cls.substr(0, dot) + L"\" TargetType=\"t:" + cls.substr(dot + 1));
    for (auto tt : TargetTypes(fe)) types.push_back(std::wstring(L"TargetType=\"") + tt);
    for (auto& tt : types) {
        std::wstring x = head + tt + L"\"><Setter Property=\"" + Esc(st.prop) + L"\"";
        if (st.xaml) x += L"><Setter.Value>" + st.value + L"</Setter.Value></Setter></Style>";
        else x += L" Value=\"" + Esc(st.value) + L"\"/></Style>";
        try {
            auto style = wux::Markup::XamlReader::Load(x).as<wux::Style>();
            auto setter = style.Setters().GetAt(0).as<wux::Setter>();
            dp = setter.Property();
            val = setter.Value();
            if (dp) return true;
        } catch (...) {}
    }
    return false;
}

// ------------------------------------------------------------------ aplicar / restaurar
void Restore(wux::FrameworkElement const& fe, Prop& p) {
    if (!p.saved) return;
    p.cur = nullptr;
    try {
        if (p.cbToken) fe.UnregisterPropertyChangedCallback(p.dp, p.cbToken);
        p.cbToken = 0;
        g_inSet = true;
        if (p.orig == wux::DependencyProperty::UnsetValue()) fe.ClearValue(p.dp);
        else fe.SetValue(p.dp, p.orig);
    } catch (...) {}
    g_inSet = false;
    p.saved = false;
}

void OnChanged(wux::DependencyObject const& sender, wux::DependencyProperty const& dp) {
    if (g_inSet) return;
    auto& me = Me();
    for (auto& a : me.applied) {
        auto el = a.el.get();
        if (!el || el != sender) continue;
        for (auto& p : a.props) {
            if (p.dp == dp && p.cur) {
                DWORD now = GetTickCount();
                if (now - p.burstStart > 1000) { p.burstStart = now; p.burst = 0; }
                if (++p.burst > 20) continue;
                g_inSet = true;
                try { el.SetValue(dp, p.cur); } catch (...) {}
                g_inSet = false;
            }
        }
    }
}

void Evaluate(Applied& a, const std::wstring& state) {
    auto el = a.el.get();
    if (!el) return;
    // propiedades distintas de la regla
    for (auto& st : a.rule->setters) {
        bool known = false;
        for (auto& p : a.props) known |= p.name == st.prop;
        if (!known) a.props.push_back(Prop{st.prop});
    }
    for (auto& p : a.props) {
        const StyleSetter* pick = nullptr;
        for (auto& st : a.rule->setters)
            if (st.prop == p.name && !st.state.empty() && st.state == state) pick = &st;
        if (!pick)
            for (auto& st : a.rule->setters)
                if (st.prop == p.name && st.state.empty()) pick = &st;
        if (!pick) { Restore(el, p); continue; }
        wux::DependencyProperty dp{nullptr};
        WInspectable val{nullptr};
        if (!MakeValue(el, *pick, dp, val)) continue;
        try {
            if (!p.saved) {
                p.dp = dp;
                p.orig = el.ReadLocalValue(dp);
                p.saved = true;
                p.cbToken = el.RegisterPropertyChangedCallback(dp, OnChanged);
            }
            p.cur = val;
            g_inSet = true;
            el.SetValue(dp, val);
        } catch (...) {}
        g_inSet = false;
    }
}

void Attach(ThreadState& me, wux::FrameworkElement const& fe) {
    for (auto& rule : *me.rules) {
        wux::FrameworkElement groupEl{nullptr};
        if (!RuleMatches(fe, rule, groupEl)) continue;
        me.applied.emplace_back();
        Applied* a = &me.applied.back();
        a->el = winrt::make_weak(fe);
        a->rule = &rule;
        std::wstring state;
        if (groupEl) {
            try {
                for (auto g : wux::VisualStateManager::GetVisualStateGroups(groupEl)) {
                    if (std::wstring(g.Name()) != rule.segs[rule.groupSeg].group) continue;
                    a->group = winrt::make_weak(g);
                    if (auto cs = g.CurrentState()) state = cs.Name();
                    a->token = g.CurrentStateChanged([a](WInspectable const&, wux::VisualStateChangedEventArgs const& e) {
                        std::wstring s;
                        if (auto ns = e.NewState()) s = ns.Name();
                        Evaluate(*a, s);
                    });
                    break;
                }
            } catch (...) {}
        }
        Evaluate(*a, state);
    }
}

void Detach(ThreadState& me) {
    for (auto& a : me.applied) {
        if (auto g = a.group.get()) {
            try { g.CurrentStateChanged(a.token); } catch (...) {}
        }
        if (auto el = a.el.get())
            for (auto& p : a.props) Restore(el, p);
    }
    me.applied.clear();
}

}  // namespace

void Styler_Init(HMODULE module, bool inStart) {
    g_mod = module;
    g_start = inStart;
    DWORD v = 0, sz = sizeof(v);
    g_dump = RegGetValueW(HKEY_CURRENT_USER, L"Software\\WinStyler", L"DumpTree", RRF_RT_REG_DWORD, nullptr, &v, &sz) == ERROR_SUCCESS && v;
}

void Styler_OnAdd(wux::FrameworkElement const& el) {
    auto& me = Me();
    if (g_dump) {
        try { DumpElement(el); } catch (...) {}
    }
    if (!me.rules) me.rules = CurrentRules();
    me.all.push_back(winrt::make_weak(el));
    if (++me.adds % 512 == 0)  // se descartan los elementos ya destruidos
        me.all.erase(std::remove_if(me.all.begin(), me.all.end(), [](auto& w) { return !w.get(); }), me.all.end());
    if (!me.rules->empty()) {
        try { Attach(me, el); } catch (...) {}
    }
}

void Styler_ReloadThread() {
    auto& me = Me();
    auto rules = CurrentRules();
    if (rules == me.rules) return;
    Detach(me);
    me.rules = rules;
    if (rules->empty()) return;
    for (auto& w : me.all)
        if (auto el = w.get()) {
            try { Attach(me, el); } catch (...) {}
        }
}

void Styler_Threads(std::vector<DWORD>& out) {
    std::lock_guard<std::mutex> l(g_threadsLock);
    for (auto& t : g_threads)
        if (std::find(out.begin(), out.end(), t.first) == out.end()) out.push_back(t.first);
}

void Styler_Invalidate() {
    std::lock_guard<std::mutex> l(g_fileLock);
    g_loadedTime = FILETIME{1, 1};  // fuerza la relectura en el próximo acceso
}
