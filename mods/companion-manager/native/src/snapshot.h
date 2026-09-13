#pragma once
#include <nlohmann/json.hpp>

namespace companion
{
// Must only be called from the Skyrim task/game thread. Never retains Actor pointers.
nlohmann::json CollectSnapshot();
} // namespace companion
