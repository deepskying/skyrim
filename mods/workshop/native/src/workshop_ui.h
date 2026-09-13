#pragma once
#include "../../../durability-manager/native/src/PrismaUI_API.h"
#include "MeridianUIAPI/ViewDllLoader.h"

namespace unified_workshop
{
// Both modules share one backend and handle. Standalone builds retain Prisma.
class WorkshopUI
{
public:
    Meridian::UI::Settings settings{};
    Meridian::UI::View::IViewAPI* views = nullptr;
    PRISMA_UI_API::IVPrismaUI1* prisma = nullptr;
    bool initialized = false;
    bool Init() {
        if (!initialized) {
            initialized = true;
            views = Meridian::UI::View::Query(&settings, "EquipmentWorkshop");
            prisma = PRISMA_UI_API::RequestPluginAPI();
        }
        return views || prisma;
    }
    PrismaView CreateView(const char* path) {
        if (!views) return prisma->CreateView(path);
        Meridian::UI::View::ViewCreateInfo info{};
        info.ownerName = "equipmentworkshop";
        info.viewName = "workshop";
        info.startUrl = "mod://equipmentworkshop/index.html";
        return views->CreateView(&info);
    }
    void Invoke(PrismaView view, const char* script) {
        if (views) views->ExecuteJavaScript(view, script); else prisma->Invoke(view, script);
    }
    void RegisterJSListener(PrismaView view, const char* name, PRISMA_UI_API::JSListenerCallback callback) {
        if (views) views->RegisterListener(view, name, callback); else prisma->RegisterJSListener(view, name, callback);
    }
    bool HasFocus(PrismaView view) { return views ? views->HasFocus(view) : prisma->HasFocus(view); }
    bool HasAnyActiveFocus() {
        return (views && views->HasAnyFocus()) || (prisma && prisma->HasAnyActiveFocus());
    }
    bool Focus(PrismaView view, bool pause) {
        if (!views) return prisma->Focus(view, pause);
        if (prisma && prisma->HasAnyActiveFocus()) return false;
        const auto result = views->TryFocus(view, pause ? Meridian::UI::View::FocusMode::PauseGame : Meridian::UI::View::FocusMode::Unpaused);
        return result == Meridian::UI::View::FocusResult::Granted || result == Meridian::UI::View::FocusResult::AlreadyFocused;
    }
    void Unfocus(PrismaView view) { if (views) views->Unfocus(view); else prisma->Unfocus(view); }
    void Show(PrismaView view) { if (views) views->Show(view); else prisma->Show(view); }
    void Hide(PrismaView view) { if (views) views->Hide(view); else prisma->Hide(view); }
};
inline WorkshopUI* GetWorkshopUI() {
    static WorkshopUI ui;
    return ui.Init() ? &ui : nullptr;
}
}
