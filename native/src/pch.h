#pragma once

#pragma warning(push)
#include <RE/Skyrim.h>
#include <REL/Relocation.h>
#include <SKSE/SKSE.h>
#include <nlohmann/json.hpp>
#pragma warning(pop)

#include <algorithm>
#include <functional>
#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace logger = SKSE::log;

#define DLLEXPORT __declspec(dllexport)
