#include "input_handler.h"

InputHandler* InputHandler::GetSingleton()
{
    static InputHandler singleton;
    return std::addressof(singleton);
}

void InputHandler::RegisterSink()
{
    if (const auto inputManager = RE::BSInputDeviceManager::GetSingleton()) {
        inputManager->AddEventSink(this);
    }
}

void InputHandler::SetToggleCallback(std::function<void()> a_callback)
{
    _onToggle = std::move(a_callback);
}

void InputHandler::SetEscapeCallback(std::function<bool()> a_callback)
{
    _onEscape = std::move(a_callback);
}

void InputHandler::SetHotkey(HotkeyConfig a_hotkey)
{
    _hotkey = a_hotkey;
}

void InputHandler::UpdateModifierState(std::uint32_t a_keyCode, bool a_isPressed)
{
    switch (a_keyCode) {
    case 0x2A: _leftShift = a_isPressed; break;
    case 0x36: _rightShift = a_isPressed; break;
    case 0x1D: _leftCtrl = a_isPressed; break;
    case 0x9D: _rightCtrl = a_isPressed; break;
    case 0x38: _leftAlt = a_isPressed; break;
    case 0xB8: _rightAlt = a_isPressed; break;
    default: break;
    }
}

bool InputHandler::ModifiersMatch() const
{
    const bool shiftDown = _leftShift || _rightShift;
    const bool ctrlDown = _leftCtrl || _rightCtrl;
    const bool altDown = _leftAlt || _rightAlt;
    return (!_hotkey.requireShift || shiftDown) &&
           (!_hotkey.requireCtrl || ctrlDown) &&
           (!_hotkey.requireAlt || altDown);
}

RE::BSEventNotifyControl InputHandler::ProcessEvent(
    RE::InputEvent* const* a_events,
    RE::BSTEventSource<RE::InputEvent*>*)
{
    if (!a_events) return RE::BSEventNotifyControl::kContinue;

    for (auto event = *a_events; event; event = event->next) {
        const auto button = event->AsButtonEvent();
        if (!button || button->GetDevice() != RE::INPUT_DEVICE::kKeyboard) continue;

        const auto keyCode = button->GetIDCode();
        UpdateModifierState(keyCode, button->IsPressed());
        if (!button->IsDown()) continue;

        if (keyCode == _hotkey.keyCode && _onToggle && ModifiersMatch()) {
            _onToggle();
            return RE::BSEventNotifyControl::kStop;
        }
        if (keyCode == 0x01 && _onEscape && _onEscape()) {
            return RE::BSEventNotifyControl::kStop;
        }
    }
    return RE::BSEventNotifyControl::kContinue;
}
