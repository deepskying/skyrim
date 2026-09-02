#pragma once

#include <Windows.h>

#include <functional>

struct HotkeyConfig
{
    std::uint32_t keyCode = 0x21; // F
    bool requireShift = true;
    bool requireCtrl = false;
    bool requireAlt = false;
};

class InputHandler final : public RE::BSTEventSink<RE::InputEvent*>
{
public:
    static InputHandler* GetSingleton()
    {
        static InputHandler singleton;
        return std::addressof(singleton);
    }

    void SetHotkey(const HotkeyConfig& a_hotkey) { hotkey_ = a_hotkey; }
    void SetToggleCallback(std::function<void()> a_callback) { toggleCallback_ = std::move(a_callback); }
    void SetEscapeCallback(std::function<bool()> a_callback) { escapeCallback_ = std::move(a_callback); }
    void SetCaptureCallback(std::function<bool(std::uint32_t, bool, bool, bool)> a_callback) { captureCallback_ = std::move(a_callback); }

    void RegisterSink()
    {
        if (registered_) return;
        if (auto* input = RE::BSInputDeviceManager::GetSingleton()) {
            input->AddEventSink(this);
            registered_ = true;
        }
    }

    RE::BSEventNotifyControl ProcessEvent(RE::InputEvent* const* a_events, RE::BSTEventSource<RE::InputEvent*>*) override
    {
        if (!a_events) return RE::BSEventNotifyControl::kContinue;
        for (auto* event = *a_events; event; event = event->next) {
            if (event->GetEventType() != RE::INPUT_EVENT_TYPE::kButton) continue;
            const auto* button = event->AsButtonEvent();
            if (!button || !button->IsDown()) continue;
            const auto key = button->GetIDCode();
            if (captureCallback_ && !IsModifierKey(key) && captureCallback_(key, Down(VK_SHIFT), Down(VK_CONTROL), Down(VK_MENU))) continue;
            if (key == 0x01 && escapeCallback_ && escapeCallback_()) continue;
            if (key == hotkey_.keyCode && MatchesModifiers(hotkey_) && toggleCallback_) toggleCallback_();
        }
        return RE::BSEventNotifyControl::kContinue;
    }

private:
    static bool Down(const int a_key) { return (GetAsyncKeyState(a_key) & 0x8000) != 0; }
    static bool IsModifierKey(const std::uint32_t a_key) { return a_key == 0x2A || a_key == 0x36 || a_key == 0x1D || a_key == 0x9D || a_key == 0x38 || a_key == 0xB8; }
    static bool MatchesModifiers(const HotkeyConfig& a_hotkey)
    {
        return Down(VK_SHIFT) == a_hotkey.requireShift && Down(VK_CONTROL) == a_hotkey.requireCtrl && Down(VK_MENU) == a_hotkey.requireAlt;
    }

    HotkeyConfig hotkey_{};
    std::function<void()> toggleCallback_;
    std::function<bool()> escapeCallback_;
    std::function<bool(std::uint32_t, bool, bool, bool)> captureCallback_;
    bool registered_ = false;
};
