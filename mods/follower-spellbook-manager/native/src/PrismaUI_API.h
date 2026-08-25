/* Prisma UI public API. Kept verbatim in ABI shape so this plugin can request Prisma UI v1. */
#pragma once

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
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
        virtual PrismaView CreateView(const char*, OnDomReadyCallback = nullptr) noexcept = 0;
        virtual void Invoke(PrismaView, const char*, JSCallback = nullptr) noexcept = 0;
        virtual void InteropCall(PrismaView, const char*, const char*) noexcept = 0;
        virtual void RegisterJSListener(PrismaView, const char*, JSListenerCallback) noexcept = 0;
        virtual bool HasFocus(PrismaView) noexcept = 0;
        virtual bool Focus(PrismaView, bool = false, bool = false) noexcept = 0;
        virtual void Unfocus(PrismaView) noexcept = 0;
        virtual void Show(PrismaView) noexcept = 0;
        virtual void Hide(PrismaView) noexcept = 0;
        virtual bool IsHidden(PrismaView) noexcept = 0;
        virtual int GetScrollingPixelSize(PrismaView) noexcept = 0;
        virtual void SetScrollingPixelSize(PrismaView, int) noexcept = 0;
        virtual bool IsValid(PrismaView) noexcept = 0;
        virtual void Destroy(PrismaView) noexcept = 0;
        virtual void SetOrder(PrismaView, int) noexcept = 0;
        virtual int GetOrder(PrismaView) noexcept = 0;
        virtual void CreateInspectorView(PrismaView) noexcept = 0;
        virtual void SetInspectorVisibility(PrismaView, bool) noexcept = 0;
        virtual bool IsInspectorVisible(PrismaView) noexcept = 0;
        virtual void SetInspectorBounds(PrismaView, float, float, unsigned int, unsigned int) noexcept = 0;
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
