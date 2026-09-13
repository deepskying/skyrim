#include "spell_details.h"
#include <cmath>
namespace companion
{
const char *SpellSchool(RE::SpellItem *spell)
{
    if (!spell)
        return "其他";
    switch (spell->GetAssociatedSkill())
    {
    case RE::ActorValue::kAlteration:
        return "变化系";
    case RE::ActorValue::kConjuration:
        return "召唤系";
    case RE::ActorValue::kDestruction:
        return "毁灭系";
    case RE::ActorValue::kIllusion:
        return "幻术系";
    case RE::ActorValue::kRestoration:
        return "恢复系";
    default:
        return "其他";
    }
}
std::string SpellDescription(RE::SpellItem *spell)
{
    std::string result;
    if (!spell)
        return result;
    for (auto *effect : spell->effects)
    {
        if (!effect || !effect->baseEffect)
            continue;
        const auto *raw = effect->baseEffect->magicItemDescription.c_str();
        std::string text = raw ? raw : "";
        const auto magnitude = std::isfinite(effect->effectItem.magnitude) ? effect->effectItem.magnitude : 0.0f;
        const auto mag = std::format("{:g}", magnitude);
        const auto duration = std::to_string(effect->effectItem.duration),
                   area = std::to_string(effect->effectItem.area);
        const auto replace = [&](const std::string &key, const std::string &value) {
            std::size_t pos = 0;
            while ((pos = text.find(key, pos)) != std::string::npos)
            {
                text.replace(pos, key.size(), value);
                pos += value.size();
            }
        };
        for (const auto *key : {"<mag>", "<MAG>"})
            replace(key, mag);
        for (const auto *key : {"<dur>", "<DUR>"})
            replace(key, duration);
        for (const auto *key : {"<area>", "<AREA>"})
            replace(key, area);
        if (text.empty())
        {
            const auto *name = effect->baseEffect->GetFullName();
            text = name ? name : "未命名效果";
            if (magnitude != 0)
                text += " · 强度 " + mag;
            if (effect->effectItem.duration)
                text += " · 持续 " + duration + " 秒";
            if (effect->effectItem.area)
                text += " · 范围 " + area + " 英尺";
        }
        if (!text.empty())
        {
            if (!result.empty())
                result += '\n';
            result += text;
        }
        if (result.size() > 8192)
        {
            result.resize(8192);
            break;
        }
    }
    return result;
}
} // namespace companion
