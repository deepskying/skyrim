#pragma once

#include <Windows.h>

#include <functional>

struct HotkeyConfig
{
    std::uint32_t keyCode = 0x20; // D
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
    void SetPageToggleCallback(std::function<bool()> a_callback) { pageToggleCallback_ = std::move(a_callback); }
    void SetFavoriteCallback(std::function<bool()> a_callback) { favoriteCallback_ = std::move(a_callback); }
    void SetCaptureCallback(std::function<bool(std::uint32_t, bool, bool, bool)> a_callback) { captureCallback_ = std::move(a_callback); }

    void RegisterSink()
    {
        if (registered_) return;
        if (auto* input = RE::BSInputDeviceManager::GetSingleton()) {
            input->AddEventSink(this);
            registered_ = true;
        }
    }

    RE::BSEventNotifyControl ProcessEvent(
        RE::InputEvent* const* a_events,
        RE::BSTEventSource<RE::InputEvent*>*) override
    {
        if (!a_events) return RE::BSEventNotifyControl::kContinue;
        for (auto* event = *a_events; event; event = event->next) {
            if (event->GetEventType() != RE::INPUT_EVENT_TYPE::kButton) continue;
            const auto* button = event->AsButtonEvent();
            if (!button || !button->IsDown()) continue;
            const auto key = button->GetIDCode();
            if (captureCallback_ && !IsModifierKey(key) && captureCallback_(key, IsModifierDown(VK_SHIFT), IsModifierDown(VK_CONTROL), IsModifierDown(VK_MENU))) continue;
            if (key == 0x01 && escapeCallback_ && escapeCallback_()) continue;
            if ((key == 0x38 || key == 0xB8) && pageToggleCallback_ && pageToggleCallback_()) continue;
            if (key == 0x21 && favoriteCallback_ && favoriteCallback_()) continue;
            if (key == hotkey_.keyCode && ModifiersMatch() && toggleCallback_) toggleCallback_();
        }
        return RE::BSEventNotifyControl::kContinue;
    }

private:
    [[nodiscard]] static bool IsModifierKey(std::uint32_t a_key)
    {
        return a_key == 0x2A || a_key == 0x36 || a_key == 0x1D || a_key == 0x9D || a_key == 0x38 || a_key == 0xB8;
    }

    [[nodiscard]] static bool IsModifierDown(int a_key)
    {
        return (GetAsyncKeyState(a_key) & 0x8000) != 0;
    }

    [[nodiscard]] bool ModifiersMatch() const
    {
        return IsModifierDown(VK_SHIFT) == hotkey_.requireShift &&
               IsModifierDown(VK_CONTROL) == hotkey_.requireCtrl &&
               IsModifierDown(VK_MENU) == hotkey_.requireAlt;
    }

    HotkeyConfig hotkey_{};
    std::function<void()> toggleCallback_;
    std::function<bool()> escapeCallback_;
    std::function<bool()> pageToggleCallback_;
    std::function<bool()> favoriteCallback_;
    std::function<bool(std::uint32_t, bool, bool, bool)> captureCallback_;
    bool registered_ = false;
};
