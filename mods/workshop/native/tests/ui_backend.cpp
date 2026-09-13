#ifdef NDEBUG
#undef NDEBUG
#endif
#include "workshop_ui.h"
#include <cassert>
#include <string>

namespace V = Meridian::UI::View;
struct FakeViews : V::IViewAPI {
    V::FocusResult focusResult = V::FocusResult::NotReady;
    bool focused = false, visible = false;
    int created = 0, focusCalls = 0;
    std::string url, script, listener;
    V::ViewHandle CreateView(const V::ViewCreateInfo* info) override { ++created; url = info->startUrl; assert(!info->initiallyVisible); return 42; }
    void DestroyView(V::ViewHandle) override {}
    bool IsValid(V::ViewHandle v) const override { return v == 42; }
    bool IsReady(V::ViewHandle) const override { return true; }
    bool RegisterListener(V::ViewHandle v, const char* name, V::ListenerCallback) override { assert(v == 42); listener = name; return true; }
    bool ExecuteJavaScript(V::ViewHandle v, const char* value) override { assert(v == 42); script = value; return true; }
    bool Show(V::ViewHandle) override { visible = true; return true; }
    bool Hide(V::ViewHandle) override { visible = false; return true; }
    V::FocusResult TryFocus(V::ViewHandle, V::FocusMode mode) override { ++focusCalls; assert(mode == V::FocusMode::PauseGame); return focusResult; }
    void Unfocus(V::ViewHandle) override { focused = false; }
    bool HasFocus(V::ViewHandle) const override { return focused; }
    bool HasAnyFocus() const override { return focused; }
};
struct FakePrisma : PRISMA_UI_API::IVPrismaUI1 {
    bool focused = false;
    int created = 0;
    std::string path, script;
    PrismaView CreateView(const char* p, PRISMA_UI_API::OnDomReadyCallback) noexcept override { ++created; path = p; return 9; }
    void Invoke(PrismaView v, const char* p, PRISMA_UI_API::JSCallback) noexcept override { assert(v == 9); script = p; }
    void InteropCall(PrismaView, const char*, const char*) noexcept override {}
    void RegisterJSListener(PrismaView, const char*, PRISMA_UI_API::JSListenerCallback) noexcept override {}
    bool HasFocus(PrismaView) noexcept override { return focused; }
    bool Focus(PrismaView, bool, bool) noexcept override { focused = true; return true; }
    void Unfocus(PrismaView) noexcept override { focused = false; }
    void Show(PrismaView) noexcept override {}
    void Hide(PrismaView) noexcept override {}
    bool IsHidden(PrismaView) noexcept override { return false; }
    int GetScrollingPixelSize(PrismaView) noexcept override { return 0; }
    void SetScrollingPixelSize(PrismaView, int) noexcept override {}
    bool IsValid(PrismaView) noexcept override { return true; }
    void Destroy(PrismaView) noexcept override {}
    void SetOrder(PrismaView, int) noexcept override {}
    int GetOrder(PrismaView) noexcept override { return 0; }
    void CreateInspectorView(PrismaView) noexcept override {}
    void SetInspectorVisibility(PrismaView, bool) noexcept override {}
    bool IsInspectorVisible(PrismaView) noexcept override { return false; }
    void SetInspectorBounds(PrismaView, float, float, unsigned int, unsigned int) noexcept override {}
    bool HasAnyActiveFocus() noexcept override { return focused; }
};
int main() {
    FakeViews views; FakePrisma prisma;
    unified_workshop::WorkshopUI ui; ui.views = &views; ui.prisma = &prisma;
    const auto handle = ui.CreateView("DurabilityManager/index.html");
    assert(handle == 42 && views.created == 1 && prisma.created == 0);
    assert(views.url == "mod://equipmentworkshop/index.html");
    ui.RegisterJSListener(handle, "durabilityManagerAction", nullptr);
    ui.Invoke(handle, "window.DurabilityManager.receiveState({});");
    assert(views.listener == "durabilityManagerAction" && !views.script.empty() && prisma.script.empty());
    assert(!ui.Focus(handle, true)); // Not ready must never be treated as acquired focus.
    views.focusResult = V::FocusResult::Busy; assert(!ui.Focus(handle, true));
    views.focusResult = V::FocusResult::Granted; assert(ui.Focus(handle, true));
    views.focusResult = V::FocusResult::AlreadyFocused; assert(ui.Focus(handle, true));
    prisma.focused = true; const auto calls = views.focusCalls;
    assert(ui.HasAnyActiveFocus() && !ui.Focus(handle, true) && views.focusCalls == calls);
    prisma.focused = false; views.focused = true;
    ui.Show(handle); assert(views.visible && ui.HasFocus(handle));
    ui.Unfocus(handle); ui.Hide(handle); assert(!ui.HasAnyActiveFocus() && !views.visible);
    ui.views = nullptr;
    assert(ui.CreateView("DurabilityManager/index.html") == 9 && prisma.created == 1);
    assert(prisma.path == "DurabilityManager/index.html");
    ui.Invoke(9, "fallback"); assert(prisma.script == "fallback");
    assert(ui.Focus(9, true) && ui.HasFocus(9)); ui.Unfocus(9); assert(!ui.HasAnyActiveFocus());
}
