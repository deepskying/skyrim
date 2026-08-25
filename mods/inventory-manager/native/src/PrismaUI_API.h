/*
 * PrismaUI public API v1. This header is distributed by PrismaUI specifically
 * for use in SKSE plugins.
 */
#pragma once

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <Windows.h>
#include <cstdint>

using PrismaView = std::uint64_t;

namespace PRISMA_UI_API
{
    enum class InterfaceVersion : std::uint8_t { V1, V2 };
    using OnDomReadyCallback = void (*)(PrismaView);
    using JSCallback = void (*)(const char*);
    using JSListenerCallback = void (*)(const char*);

    class IVPrismaUI1
    {
    protected:
        ~IVPrismaUI1() = default;
    public:
        virtual PrismaView CreateView(const char* a_htmlPath, OnDomReadyCallback a_callback = nullptr) noexcept = 0;
        virtual void Invoke(PrismaView a_view, const char* a_script, JSCallback a_callback = nullptr) noexcept = 0;
        virtual void InteropCall(PrismaView a_view, const char* a_functionName, const char* a_argument) noexcept = 0;
        virtual void RegisterJSListener(PrismaView a_view, const char* a_functionName, JSListenerCallback a_callback) noexcept = 0;
        virtual bool HasFocus(PrismaView a_view) noexcept = 0;
        virtual bool Focus(PrismaView a_view, bool a_pauseGame = false, bool a_disableFocusMenu = false) noexcept = 0;
        virtual void Unfocus(PrismaView a_view) noexcept = 0;
        virtual void Show(PrismaView a_view) noexcept = 0;
        virtual void Hide(PrismaView a_view) noexcept = 0;
        virtual bool IsHidden(PrismaView a_view) noexcept = 0;
        virtual int GetScrollingPixelSize(PrismaView a_view) noexcept = 0;
        virtual void SetScrollingPixelSize(PrismaView a_view, int a_pixelSize) noexcept = 0;
        virtual bool IsValid(PrismaView a_view) noexcept = 0;
        virtual void Destroy(PrismaView a_view) noexcept = 0;
        virtual void SetOrder(PrismaView a_view, int a_order) noexcept = 0;
        virtual int GetOrder(PrismaView a_view) noexcept = 0;
        virtual void CreateInspectorView(PrismaView a_view) noexcept = 0;
        virtual void SetInspectorVisibility(PrismaView a_view, bool a_visible) noexcept = 0;
        virtual bool IsInspectorVisible(PrismaView a_view) noexcept = 0;
        virtual void SetInspectorBounds(PrismaView a_view, float a_x, float a_y, unsigned int a_width, unsigned int a_height) noexcept = 0;
        virtual bool HasAnyActiveFocus() noexcept = 0;
    };

    using RequestPluginAPIFunc = void* (*)(InterfaceVersion);

    [[nodiscard]] inline IVPrismaUI1* RequestPluginAPI()
    {
        const auto module = GetModuleHandleA("PrismaUI.dll");
        if (!module) return nullptr;
        const auto request = reinterpret_cast<RequestPluginAPIFunc>(GetProcAddress(module, "RequestPluginAPI"));
        return request ? static_cast<IVPrismaUI1*>(request(InterfaceVersion::V1)) : nullptr;
    }
}
