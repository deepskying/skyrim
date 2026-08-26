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
    void SetPageToggleHotkey(const HotkeyConfig& a_hotkey) { pageToggleHotkey_ = a_hotkey; }
    void SetSearchHotkey(const HotkeyConfig& a_hotkey) { searchHotkey_ = a_hotkey; }
    void SetToggleCallback(std::function<void()> a_callback) { toggleCallback_ = std::move(a_callback); }
    void SetEscapeCallback(std::function<bool()> a_callback) { escapeCallback_ = std::move(a_callback); }
    void SetPageToggleCallback(std::function<bool()> a_callback) { pageToggleCallback_ = std::move(a_callback); }
    void SetFavoriteCallback(std::function<bool()> a_callback) { favoriteCallback_ = std::move(a_callback); }
    void SetSearchCallback(std::function<bool()> a_callback) { searchCallback_ = std::move(a_callback); }
    void SetNavigationCallback(std::function<bool(std::uint32_t)> a_callback) { navigationCallback_ = std::move(a_callback); }
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
            if (captureCallback_ && (!IsModifierKey(key) || IsAltKey(key)) && captureCallback_(key, IsModifierDown(VK_SHIFT), IsModifierDown(VK_CONTROL), IsModifierDown(VK_MENU) || IsAltKey(key))) continue;
            if (key == 0x01 && escapeCallback_ && escapeCallback_()) continue;
            if (key == 0x21 && favoriteCallback_ && favoriteCallback_()) continue;
            if (KeysMatch(key, hotkey_) && ModifiersMatch(hotkey_, key) && toggleCallback_) {
                toggleCallback_();
                continue;
            }
            if (KeysMatch(key, pageToggleHotkey_) && ModifiersMatch(pageToggleHotkey_, key) && pageToggleCallback_ && pageToggleCallback_()) continue;
            if (KeysMatch(key, searchHotkey_) && ModifiersMatch(searchHotkey_, key) && searchCallback_ && searchCallback_()) continue;
            if (IsNavigationKey(key) && navigationCallback_ && navigationCallback_(key)) continue;
        }
        return RE::BSEventNotifyControl::kContinue;
    }

private:
    [[nodiscard]] static bool IsModifierKey(std::uint32_t a_key)
    {
        return a_key == 0x2A || a_key == 0x36 || a_key == 0x1D || a_key == 0x9D || a_key == 0x38 || a_key == 0xB8;
    }

    [[nodiscard]] static bool IsAltKey(std::uint32_t a_key)
    {
        return a_key == 0x38 || a_key == 0xB8;
    }

    [[nodiscard]] static bool KeysMatch(std::uint32_t a_key, const HotkeyConfig& a_hotkey)
    {
        return a_key == a_hotkey.keyCode || (a_hotkey.keyCode == 0x38 && a_key == 0xB8);
    }

    [[nodiscard]] static bool IsNavigationKey(std::uint32_t a_key)
    {
        return a_key == 0x11 || a_key == 0x1E || a_key == 0x1F || a_key == 0x20 ||
               a_key == 0xC8 || a_key == 0xCB || a_key == 0xCD || a_key == 0xD0;
    }

    [[nodiscard]] static bool IsModifierDown(int a_key)
    {
        return (GetAsyncKeyState(a_key) & 0x8000) != 0;
    }

    [[nodiscard]] static bool ModifiersMatch(const HotkeyConfig& a_hotkey, std::uint32_t a_key)
    {
        return IsModifierDown(VK_SHIFT) == a_hotkey.requireShift &&
               IsModifierDown(VK_CONTROL) == a_hotkey.requireCtrl &&
               (IsModifierDown(VK_MENU) || IsAltKey(a_key)) == a_hotkey.requireAlt;
    }

    HotkeyConfig hotkey_{};
    HotkeyConfig pageToggleHotkey_{ 0x38, false, false, true };
    HotkeyConfig searchHotkey_{ 0x35, false, false, false };
    std::function<void()> toggleCallback_;
    std::function<bool()> escapeCallback_;
    std::function<bool()> pageToggleCallback_;
    std::function<bool()> favoriteCallback_;
    std::function<bool()> searchCallback_;
    std::function<bool(std::uint32_t)> navigationCallback_;
    std::function<bool(std::uint32_t, bool, bool, bool)> captureCallback_;
    bool registered_ = false;
};
