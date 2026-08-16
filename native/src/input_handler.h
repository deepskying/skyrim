#pragma once

class InputHandler final : public RE::BSTEventSink<RE::InputEvent*>
{
public:
    static InputHandler* GetSingleton();
    void RegisterSink();
    void SetF10Callback(std::function<void()> a_callback);
    void SetEscapeCallback(std::function<void()> a_callback);

private:
    RE::BSEventNotifyControl ProcessEvent(
        RE::InputEvent* const* a_events,
        RE::BSTEventSource<RE::InputEvent*>*) override;

    std::function<void()> _onF10;
    std::function<void()> _onEscape;
};
