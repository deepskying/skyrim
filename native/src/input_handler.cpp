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

void InputHandler::SetF10Callback(std::function<void()> a_callback)
{
    _onF10 = std::move(a_callback);
}

void InputHandler::SetEscapeCallback(std::function<void()> a_callback)
{
    _onEscape = std::move(a_callback);
}

RE::BSEventNotifyControl InputHandler::ProcessEvent(
    RE::InputEvent* const* a_events,
    RE::BSTEventSource<RE::InputEvent*>*)
{
    if (!a_events) return RE::BSEventNotifyControl::kContinue;

    for (auto event = *a_events; event; event = event->next) {
        const auto button = event->AsButtonEvent();
        if (!button || button->GetDevice() != RE::INPUT_DEVICE::kKeyboard || !button->IsDown()) continue;
        if (button->GetIDCode() == 0x44 && _onF10) {
            _onF10();
            break;
        }
        if (button->GetIDCode() == 0x01 && _onEscape) {
            _onEscape();
            break;
        }
    }
    return RE::BSEventNotifyControl::kContinue;
}
