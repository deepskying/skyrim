#include "MeridianUIAPI/ViewDllLoader.h"
#include "input_rules.h"
#include "manager.h"
#include "snapshot.h"
#include <atomic>
#include <spdlog/sinks/basic_file_sink.h>

namespace
{
namespace View = Meridian::UI::View;
View::IViewAPI *views = nullptr;
View::ViewHandle panel = View::INVALID_VIEW_HANDLE;
std::atomic_bool refreshQueued = false;

void Close()
{
    if (!views || !panel)
        return;
    views->Unfocus(panel);
    views->Hide(panel);
    views->ExecuteJavaScript(
        panel, "window.__companionSnapshot=undefined;window.dispatchEvent(new Event('companion:reset'));");
}

void SendSnapshot()
{
    if (!views || !panel || !views->IsReady(panel) || !views->HasFocus(panel))
        return;
    try
    {
        const auto snapshot = companion::CollectSnapshot();
        for (const auto &actor : snapshot.at("followers"))
            if (actor.at("group") == "party" && !actor.at("managed").get<bool>())
                logger::info("Unmanaged teammate {} canEnroll={} reason={}", actor.at("id").get<std::string>(),
                             actor.at("canRecruit").get<bool>(), actor.at("reason").get<std::string>());
        const auto script =
            "window.__companionSnapshot=" + snapshot.dump(-1, ' ', true, nlohmann::json::error_handler_t::replace) +
            ";window.dispatchEvent(new Event('companion:snapshot'));";
        if (!views->ExecuteJavaScript(panel, script.c_str()))
            logger::warn("Snapshot delivery failed.");
    }
    catch (const std::exception &error)
    {
        logger::error("Snapshot failed: {}", error.what());
        views->ExecuteJavaScript(
            panel, "window.dispatchEvent(new CustomEvent('companion:error',{detail:'读取游戏数据失败，请查看 "
                   "CompanionManager.log'}));");
    }
}

void RequestRefresh()
{
    if (refreshQueued.exchange(true))
        return;
    if (const auto tasks = SKSE::GetTaskInterface())
    {
        tasks->AddTask([] {
            refreshQueued = false;
            SendSnapshot();
        });
    }
    else
        refreshQueued = false;
}

void OnRequest(const char *payload)
{
    // The CEF buffer belongs to the callback. Only copied, bounded commands cross to Skyrim.
    if (!payload || strnlen_s(payload, 8193) > 8192)
        return;
    try
    {
        const auto request = nlohmann::json::parse(payload);
        const auto action = request.at("type").get<std::string>();
        if (action == "refresh")
            RequestRefresh();
        else if (action == "close")
        {
            if (const auto tasks = SKSE::GetTaskInterface())
                tasks->AddTask(Close);
        }
        else if (action == "command")
        {
            const auto requestId = request.at("requestId").get<std::string>();
            if (requestId.empty() || requestId.size() > 64)
                return;
            if (const auto tasks = SKSE::GetTaskInterface())
                tasks->AddTask([request, requestId] {
                    if (!views || !panel || !views->HasFocus(panel))
                        return;
                    companion::ExecuteCommand(request, [requestId](bool ok, std::string message) {
                        const auto response =
                            nlohmann::json{{"requestId", requestId}, {"ok", ok}, {"message", message}};
                        const auto script = "window.dispatchEvent(new CustomEvent('companion:result',{detail:" +
                                            response.dump(-1, ' ', true) + "}));";
                        if (views && panel)
                            views->ExecuteJavaScript(panel, script.c_str());
                        SendSnapshot();
                    });
                });
        }
        else
            logger::warn("Rejected unsupported UI command: {}", action);
    }
    catch (const std::exception &)
    {
        logger::warn("Rejected malformed UI command.");
    }
}

bool CanOpen()
{
    const auto ui = RE::UI::GetSingleton();
    const auto player = RE::PlayerCharacter::GetSingleton();
    const auto main = RE::Main::GetSingleton();
    return main && main->gameActive && ui && player && player->GetParentCell() && !player->IsDead() &&
           !ui->GameIsPaused() && !ui->IsMenuOpen(RE::MainMenu::MENU_NAME) &&
           !ui->IsMenuOpen(RE::LoadingMenu::MENU_NAME) && !ui->IsMenuOpen(RE::Console::MENU_NAME) &&
           !ui->IsMenuOpen(RE::DialogueMenu::MENU_NAME) && !ui->IsMenuOpen(RE::RaceSexMenu::MENU_NAME);
}

bool Open()
{
    if (!views || !panel || !CanOpen() || views->HasAnyFocus())
        return false;
    if (!views->IsReady(panel))
    {
        logger::info("Panel is not ready yet.");
        return false;
    }
    if (!views->Show(panel))
        return false;
    const auto focus = views->TryFocus(panel, View::FocusMode::Unpaused);
    if (focus != View::FocusResult::Granted && focus != View::FocusResult::AlreadyFocused)
    {
        views->Hide(panel);
        return false;
    }
    RequestRefresh();
    return true;
}

class Input final : public RE::BSTEventSink<RE::InputEvent *>
{
  public:
    RE::BSEventNotifyControl ProcessEvent(RE::InputEvent *const *events,
                                          RE::BSTEventSource<RE::InputEvent *> *) override
    {
        if (!events || !views || !panel || views->HasAnyFocus())
            return RE::BSEventNotifyControl::kContinue;
        const auto devices = RE::BSInputDeviceManager::GetSingleton();
        const auto keyboard = devices ? devices->GetKeyboard() : nullptr;
        if (!keyboard)
            return RE::BSEventNotifyControl::kContinue;
        // Read the current engine snapshot, so focus changes cannot leave cached modifiers stuck.
        // Calling this CommonLib revision's out-of-line IsPressed pulls in incomplete device vtables.
        const auto pressed = [keyboard](std::uint32_t key) { return (keyboard->curState[key] & 0x80) != 0; };
        for (auto *event = *events; event; event = event->next)
        {
            const auto button = event->AsButtonEvent();
            if (!button || button->GetDevice() != RE::INPUT_DEVICE::kKeyboard)
                continue;
            if (companion::IsOpeningChord(button->GetIDCode(), button->IsDown(), pressed(0x2A) || pressed(0x36),
                                          pressed(0x1D) || pressed(0x9D), pressed(0x38) || pressed(0xB8), CanOpen(),
                                          false) &&
                Open())
            {
                return RE::BSEventNotifyControl::kStop;
            }
        }
        return RE::BSEventNotifyControl::kContinue;
    }
} input;

void OnMessage(SKSE::MessagingInterface::Message *message)
{
    switch (message->type)
    {
    case SKSE::MessagingInterface::kInputLoaded: {
        Meridian::UI::Settings settings{};
        views = View::Query(&settings, "CompanionManager");
        if (!views)
            logger::error("Meridian.View/1 unavailable. Install and enable Meridian UI; plugin remains inactive.");
        break;
    }
    case SKSE::MessagingInterface::kDataLoaded: {
        companion::InitializeManager();
        if (!views)
            break;
        View::ViewCreateInfo info{};
        info.ownerName = "companion-manager";
        info.viewName = "main";
        info.startUrl = "mod://companion-manager/index.html";
        info.initiallyVisible = false;
        info.frameRate = 60;
        info.onDOMReady = [](View::ViewHandle) { RequestRefresh(); };
        panel = views->CreateView(&info);
        if (!panel || !views->RegisterListener(panel, "companionRequest", OnRequest))
        {
            logger::error("Failed to create panel/bridge.");
            if (panel)
                views->DestroyView(panel);
            panel = View::INVALID_VIEW_HANDLE;
            break;
        }
        if (const auto devices = RE::BSInputDeviceManager::GetSingleton())
            devices->AddEventSink(&input);
        logger::info("Companion Manager {} view ready; Shift+F.", SKSE::PluginDeclaration::GetSingleton()->GetVersion().string("."));
        break;
    }
    case SKSE::MessagingInterface::kPreLoadGame:
        companion::SetGameReady(false);
        Close();
        break;
    case SKSE::MessagingInterface::kNewGame:
    case SKSE::MessagingInterface::kPostLoadGame:
        if (const auto tasks = SKSE::GetTaskInterface())
            tasks->AddTask([] { companion::SetGameReady(true); });
        Close();
        if (views && panel)
            views->ExecuteJavaScript(
                panel, "window.__companionSnapshot=undefined;window.dispatchEvent(new Event('companion:reset')); ");
        break;
    default:
        break;
    }
}
} // namespace

void companion::RefreshManagerView()
{
    RequestRefresh();
}
void companion::CloseManagerView(){Close();}
bool companion::ManagerViewOpen() { return views && views->HasAnyFocus(); }
void companion::OpenPartnerWardrobe(RE::FormID actor,std::string mode)
{
    if(Open()) {
        SendSnapshot();
        const auto detail=json{{"actorId",std::format("{:08X}",actor)},{"mode",mode},{"session",SessionToken()}}.dump();
        const auto js=std::format("window.dispatchEvent(new CustomEvent('companion:wardrobe',{{detail:{}}}));",detail);
        views->ExecuteJavaScript(panel,js.c_str());
    }
}

extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Load(const SKSE::LoadInterface *skse)
{
    REL::Module::reset();
    SKSE::Init(skse);
    companion::RegisterSerialization();
    if(auto* papyrus=SKSE::GetPapyrusInterface()) papyrus->Register(companion::RegisterPapyrus);
    else return false;
    if (auto directory = SKSE::log::log_directory())
    {
        *directory /= "CompanionManager.log";
        auto sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>(directory->string(), true);
        auto log = std::make_shared<spdlog::logger>("CompanionManager", std::move(sink));
        spdlog::set_default_logger(std::move(log));
        spdlog::set_level(spdlog::level::info);
        spdlog::flush_on(spdlog::level::info);
    }
    const auto messaging = SKSE::GetMessagingInterface();
    return messaging && messaging->RegisterListener("SKSE", OnMessage);
}
