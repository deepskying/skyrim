#pragma once

#include <memory>

namespace companion::activity {
// CreateMessage (SE 51420) consumes null-terminated varargs and a function
// pointer, despite the bundled CommonLib declaration. Use owned message data
// instead, so neither button strings nor an object callback cross that ABI.
inline bool QueuePrompt(const char* text, RE::BSTSmartPointer<RE::IMessageBoxCallback> callback)
{
    auto* queue = RE::UIMessageQueue::GetSingleton();
    auto* strings = RE::InterfaceStrings::GetSingleton();
    if (!queue || !strings) return false;
    std::unique_ptr<RE::MessageBoxData> message(static_cast<RE::MessageBoxData*>(
        queue->CreateUIMessageData(strings->messageBoxData)));
    if (!message) return false;
    message->bodyText = text;
    message->buttonText.clear();
    message->buttonText.emplace_back("好的");
    message->buttonText.emplace_back("稍后再说");
    message->type = 4;
    message->cancelOptionIndex = 1;
    message->callback = std::move(callback);
    message->menuDepth = 10;
    message->optionIndexOffset = 0;
    message->useHtml = false;
    message->verticalButtons = false;
    message->isCancellable = true;

    // SE 1.5.97 +08AB5C0 returns whether the engine accepted ownership.
    // CommonLib's QueueMessage wrapper drops this result; retain it so a
    // rejected message and its callback are freed instead of leaked.
    using QueueMessage = bool (*)(RE::MessageBoxData*);
    static REL::Relocation<QueueMessage> enqueue{ RELOCATION_ID(51422, 52271) };
    if (!enqueue(message.get())) return false;
    message.release();
    return true;
}
}
