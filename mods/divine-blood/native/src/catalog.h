#pragma once
#include <array>
namespace divine_blood {
struct Recipe {const char* key;const char* name;const char* gain;unsigned form;std::array<int,3> actorValues;};
inline constexpr std::array<Recipe,16> recipes{{
    Recipe{"health", "玛拉之血", "生命上限 +1", 0x800, {24,-1,-1}},
    Recipe{"magicka", "朱莉安诺斯之血", "魔力上限 +1", 0x802, {25,-1,-1}},
    Recipe{"stamina", "海尔辛之血", "体力上限 +1", 0x803, {26,-1,-1}},
    Recipe{"carry_weight", "泽尼萨尔之血", "负重上限 +1", 0xD74, {32,-1,-1}},
    Recipe{"health_rec", "斯丹达尔之血", "生命恢复 +0.01", 0xD75, {27,155,-1}},
    Recipe{"magicka_rec", "玛格努斯之血", "魔力恢复 +0.01", 0xD77, {28,156,-1}},
    Recipe{"stamina_rec", "塔洛斯之血", "体力恢复 +0.01", 0xD79, {29,157,-1}},
    Recipe{"shout_rec", "阿卡托什之血", "龙吼冷却倍率 −0.0001", 0xD7B, {86,28,156}},
    Recipe{"magic_resist", "阿祖拉之血", "魔法抗性 +0.01", 0xD7D, {44,-1,-1}},
    Recipe{"fire_resist", "梅瑞狄亚之血", "火焰抗性 +0.01", 0xD80, {41,-1,-1}},
    Recipe{"frost_resist", "诺克图娜之血", "寒霜抗性 +0.01", 0xD82, {43,-1,-1}},
    Recipe{"electric_resist", "波耶希亚之血", "闪电抗性 +0.01", 0xD84, {42,-1,-1}},
    Recipe{"disease_resist", "魄伊特之血", "疾病抗性 +0.01", 0xD86, {45,-1,-1}},
    Recipe{"poison_resist", "纳米拉之血", "毒素抗性 +0.01", 0xD88, {40,-1,-1}},
    Recipe{"damage_resist", "大衮之血", "护甲值 +0.01", 0xD8A, {39,9,-1}},
    Recipe{"speed_mult", "凯娜瑞斯之血", "移动速度 +0.01", 0xD8C, {30,26,-1}},
}};
}
