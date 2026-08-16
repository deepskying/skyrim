#pragma once

struct HotkeyConfig
{
    std::uint32_t keyCode = 0x1F;  // S
    bool requireShift = true;
    bool requireCtrl = false;
    bool requireAlt = false;
};

class InputHandler final : public RE::BSTEventSink<RE::InputEvent*>
{
public:
    static InputHandler* GetSingleton();
    void RegisterSink();
    void SetToggleCallback(std::function<void()> a_callback);
    void SetEscapeCallback(std::function<bool()> a_callback);
    void SetHotkey(HotkeyConfig a_hotkey);

private:
    RE::BSEventNotifyControl ProcessEvent(
        RE::InputEvent* const* a_events,
        RE::BSTEventSource<RE::InputEvent*>*) override;

    void UpdateModifierState(std::uint32_t a_keyCode, bool a_isPressed);
    [[nodiscard]] bool ModifiersMatch() const;

    std::function<void()> _onToggle;
    std::function<bool()> _onEscape;
    HotkeyConfig _hotkey;
    bool _leftShift = false;
    bool _rightShift = false;
    bool _leftCtrl = false;
    bool _rightCtrl = false;
    bool _leftAlt = false;
    bool _rightAlt = false;
};
